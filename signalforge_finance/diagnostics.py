"""Local-first quantitative diagnostics for SignalForge.

This module deliberately produces research diagnostics only. It does not connect to
brokers, submit orders, make personalized recommendations, or calculate regulatory
capital. Each caller is expected to persist its own RunManifest with the source-data
hash, transform hash, package versions, parameters and validation messages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

import numpy as np
from arch import arch_model
from scipy.linalg import subspace_angles
from sklearn.decomposition import PCA
from sklearn.preprocessing import RobustScaler, StandardScaler


class DiagnosticValidationError(ValueError):
    """Raised when a quantitative diagnostic would be misleading or non-reproducible."""


@dataclass(frozen=True, slots=True)
class GarchConfig:
    """Explicit configuration for a univariate GARCH volatility forecast."""

    p: int = 1
    o: int = 0
    q: int = 1
    distribution: Literal["normal", "student_t"] = "student_t"
    mean_model: Literal["zero", "constant"] = "constant"
    horizon: int = 1
    min_observations: int = 500
    return_scale: float = 100.0

    def __post_init__(self) -> None:
        if self.p not in (1, 2) or self.q not in (1, 2) or self.o not in (0, 1):
            raise DiagnosticValidationError("v1 supports p/q in {1, 2} and o in {0, 1}.")
        if self.horizon < 1 or self.horizon > 20:
            raise DiagnosticValidationError("GARCH horizon must be between 1 and 20 observations.")
        if self.min_observations < 100:
            raise DiagnosticValidationError("min_observations must be at least 100.")
        if not np.isfinite(self.return_scale) or self.return_scale <= 0:
            raise DiagnosticValidationError("return_scale must be a positive finite number.")


@dataclass(frozen=True, slots=True)
class GarchForecast:
    """A fitted model plus conditional and forward volatility diagnostics."""

    conditional_volatility: tuple[float, ...]
    forecast_volatility: tuple[float, ...]
    parameter_estimates: tuple[tuple[str, float], ...]
    log_likelihood: float
    aic: float
    bic: float
    convergence_flag: int
    persistence: float | None
    observations_used: int
    warning_messages: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RollingGarchPoint:
    """One no-look-ahead forecast point produced from a history ending before timestamp."""

    timestamp: str
    forecast_volatility: float
    realized_return: float
    refit_index: int


@dataclass(frozen=True, slots=True)
class PcaConfig:
    """Explicit configuration for cross-sectional PCA and regime diagnostics."""

    n_components: int | float = 0.80
    scaler: Literal["zscore", "robust"] = "zscore"
    solver: Literal["full", "randomized"] = "full"
    random_seed: int = 42
    min_assets: int = 3
    min_observations: int = 100
    regime_z_threshold: float = 2.5
    principal_angle_threshold_degrees: float = 25.0

    def __post_init__(self) -> None:
        if isinstance(self.n_components, int):
            if self.n_components < 1:
                raise DiagnosticValidationError("n_components must be >= 1.")
        elif not 0.0 < self.n_components <= 1.0:
            raise DiagnosticValidationError("n_components as a ratio must be in (0, 1].")
        if isinstance(self.n_components, float) and self.solver != "full":
            raise DiagnosticValidationError("n_components as a ratio requires solver='full'.")
        if self.min_assets < 3 or self.min_observations < 20:
            raise DiagnosticValidationError("PCA needs at least 3 assets and 20 observations.")
        if self.regime_z_threshold <= 0 or self.principal_angle_threshold_degrees <= 0:
            raise DiagnosticValidationError("Regime thresholds must be positive.")


@dataclass(frozen=True, slots=True)
class PcaFit:
    """Inspectible fit artifact for a PCA window."""

    feature_names: tuple[str, ...]
    components: tuple[tuple[float, ...], ...]
    explained_variance_ratio: tuple[float, ...]
    component_scores: tuple[tuple[float, ...], ...]
    scaler_center: tuple[float, ...]
    scaler_scale: tuple[float, ...]
    reconstruction_rmse: float
    observations_used: int


@dataclass(frozen=True, slots=True)
class PcaRegimePoint:
    """One no-look-ahead regime diagnostic based on a prior rolling training window."""

    timestamp: str
    pc_z_scores: tuple[float, ...]
    max_abs_pc_z_score: float
    max_principal_angle_degrees: float | None
    regime_shift: bool
    reasons: tuple[str, ...]


def _as_finite_vector(values: Sequence[float], *, name: str) -> np.ndarray:
    vector = np.asarray(values, dtype=float)
    if vector.ndim != 1:
        raise DiagnosticValidationError(f"{name} must be a one-dimensional sequence.")
    if vector.size == 0 or not np.isfinite(vector).all():
        raise DiagnosticValidationError(f"{name} must contain one or more finite values.")
    return vector


def _as_finite_matrix(values: Sequence[Sequence[float]], *, name: str) -> np.ndarray:
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2:
        raise DiagnosticValidationError(f"{name} must be a two-dimensional matrix.")
    if matrix.shape[0] == 0 or matrix.shape[1] == 0 or not np.isfinite(matrix).all():
        raise DiagnosticValidationError(f"{name} must be non-empty and contain only finite values.")
    return matrix


def _align_component_signs(components: np.ndarray) -> np.ndarray:
    """Apply a deterministic display convention without changing PCA geometry.

    PCA component signs are mathematically arbitrary. This function selects the
    sign such that the largest absolute loading on every component is non-negative.
    The convention is stable for identical inputs and must be recorded in the run
    manifest as a presentation transform.
    """

    aligned = np.asarray(components, dtype=float).copy()
    for row_index, row in enumerate(aligned):
        anchor_index = int(np.argmax(np.abs(row)))
        if row[anchor_index] < 0:
            aligned[row_index] *= -1.0
    return aligned


class GarchVolatilityEngine:
    """Fits an inspectible local GARCH model and returns a bounded forecast artifact."""

    def __init__(self, config: GarchConfig | None = None) -> None:
        self.config = config or GarchConfig()

    def fit_forecast(self, returns: Sequence[float]) -> GarchForecast:
        series = _as_finite_vector(returns, name="returns")
        if series.size < self.config.min_observations:
            raise DiagnosticValidationError(
                f"GARCH requires at least {self.config.min_observations} observations; got {series.size}."
            )
        if np.std(series) == 0:
            raise DiagnosticValidationError("GARCH cannot be fitted to a zero-variance return series.")

        scaled = series * self.config.return_scale
        mean = "Zero" if self.config.mean_model == "zero" else "Constant"
        distribution = "normal" if self.config.distribution == "normal" else "StudentsT"
        model = arch_model(
            scaled,
            mean=mean,
            vol="GARCH",
            p=self.config.p,
            o=self.config.o,
            q=self.config.q,
            dist=distribution,
            rescale=False,
        )
        fitted = model.fit(disp="off", show_warning=False)
        convergence_flag = int(getattr(fitted, "convergence_flag", 0))
        if convergence_flag != 0:
            raise DiagnosticValidationError(
                f"GARCH optimizer did not converge (flag={convergence_flag}); no forecast is emitted."
            )

        forecast = fitted.forecast(horizon=self.config.horizon, reindex=False)
        variance = np.asarray(forecast.variance.iloc[-1], dtype=float)
        if not np.isfinite(variance).all() or np.any(variance < 0):
            raise DiagnosticValidationError("GARCH returned an invalid forward variance forecast.")

        parameters = tuple((str(name), float(value)) for name, value in fitted.params.items())
        parameter_map = dict(parameters)
        persistence: float | None = None
        if "alpha[1]" in parameter_map and "beta[1]" in parameter_map:
            persistence = parameter_map["alpha[1]"] + parameter_map["beta[1]"]

        warnings: list[str] = []
        if persistence is not None and persistence >= 0.99:
            warnings.append("GARCH persistence is >= 0.99; long-horizon interpretation needs caution.")
        if self.config.distribution == "normal":
            warnings.append("Normal innovations selected; compare against Student-t before tail-risk interpretation.")

        return GarchForecast(
            conditional_volatility=tuple(np.asarray(fitted.conditional_volatility, dtype=float) / self.config.return_scale),
            forecast_volatility=tuple(np.sqrt(variance) / self.config.return_scale),
            parameter_estimates=parameters,
            log_likelihood=float(fitted.loglikelihood),
            aic=float(fitted.aic),
            bic=float(fitted.bic),
            convergence_flag=convergence_flag,
            persistence=persistence,
            observations_used=int(series.size),
            warning_messages=tuple(warnings),
        )


class RollingGarchVolatilityForecaster:
    """Generates rolling no-look-ahead forecasts with bounded refit cost."""

    def __init__(
        self,
        engine: GarchVolatilityEngine,
        *,
        estimation_window: int = 500,
        refit_interval: int = 5,
    ) -> None:
        if estimation_window < engine.config.min_observations:
            raise DiagnosticValidationError("estimation_window must meet the configured GARCH minimum.")
        if refit_interval < 1 or refit_interval > engine.config.horizon:
            raise DiagnosticValidationError("refit_interval must be between 1 and configured forecast horizon.")
        self.engine = engine
        self.estimation_window = estimation_window
        self.refit_interval = refit_interval

    def forecast(
        self,
        returns: Sequence[float],
        timestamps: Sequence[str],
    ) -> tuple[RollingGarchPoint, ...]:
        series = _as_finite_vector(returns, name="returns")
        if len(timestamps) != series.size:
            raise DiagnosticValidationError("timestamps must be one-to-one with returns.")
        if series.size <= self.estimation_window:
            raise DiagnosticValidationError("returns must be longer than the estimation window.")

        points: list[RollingGarchPoint] = []
        for anchor in range(self.estimation_window, series.size, self.refit_interval):
            history = series[anchor - self.estimation_window : anchor]
            remaining = series.size - anchor
            requested_horizon = min(self.refit_interval, remaining)
            engine = GarchVolatilityEngine(
                GarchConfig(
                    p=self.engine.config.p,
                    o=self.engine.config.o,
                    q=self.engine.config.q,
                    distribution=self.engine.config.distribution,
                    mean_model=self.engine.config.mean_model,
                    horizon=requested_horizon,
                    min_observations=self.engine.config.min_observations,
                    return_scale=self.engine.config.return_scale,
                )
            )
            fitted = engine.fit_forecast(history)
            for horizon_index, volatility in enumerate(fitted.forecast_volatility):
                observation_index = anchor + horizon_index
                points.append(
                    RollingGarchPoint(
                        timestamp=str(timestamps[observation_index]),
                        forecast_volatility=float(volatility),
                        realized_return=float(series[observation_index]),
                        refit_index=anchor,
                    )
                )
        return tuple(points)


class PcaRegimeEngine:
    """Local PCA fitting and no-look-ahead regime-shift diagnostics."""

    def __init__(self, config: PcaConfig | None = None) -> None:
        self.config = config or PcaConfig()

    def _new_scaler(self) -> StandardScaler | RobustScaler:
        return StandardScaler() if self.config.scaler == "zscore" else RobustScaler()

    def _fit(self, matrix: np.ndarray, feature_names: Sequence[str]) -> tuple[PCA, StandardScaler | RobustScaler, np.ndarray]:
        if matrix.shape[0] < self.config.min_observations:
            raise DiagnosticValidationError(
                f"PCA requires at least {self.config.min_observations} observations; got {matrix.shape[0]}."
            )
        if matrix.shape[1] < self.config.min_assets:
            raise DiagnosticValidationError(
                f"PCA requires at least {self.config.min_assets} assets; got {matrix.shape[1]}."
            )
        if len(feature_names) != matrix.shape[1] or len(set(feature_names)) != len(feature_names):
            raise DiagnosticValidationError("feature_names must be unique and match the matrix column count.")
        if isinstance(self.config.n_components, int) and self.config.n_components > min(matrix.shape):
            raise DiagnosticValidationError(
                "n_components cannot exceed the smaller of observation and asset counts."
            )

        scaler = self._new_scaler()
        transformed = scaler.fit_transform(matrix)
        model = PCA(
            n_components=self.config.n_components,
            svd_solver=self.config.solver,
            random_state=self.config.random_seed if self.config.solver == "randomized" else None,
        )
        scores = model.fit_transform(transformed)
        return model, scaler, scores

    def fit(self, matrix: Sequence[Sequence[float]], feature_names: Sequence[str]) -> PcaFit:
        raw = _as_finite_matrix(matrix, name="matrix")
        model, scaler, scores = self._fit(raw, feature_names)
        aligned_components = _align_component_signs(model.components_)
        reconstructed = model.inverse_transform(scores)
        reconstruction = scaler.inverse_transform(reconstructed)
        rmse = float(np.sqrt(np.mean((raw - reconstruction) ** 2)))
        scale = getattr(scaler, "scale_", np.ones(raw.shape[1]))
        center = getattr(scaler, "mean_", getattr(scaler, "center_", np.zeros(raw.shape[1])))
        return PcaFit(
            feature_names=tuple(str(name) for name in feature_names),
            components=tuple(tuple(float(value) for value in row) for row in aligned_components),
            explained_variance_ratio=tuple(float(value) for value in model.explained_variance_ratio_),
            component_scores=tuple(tuple(float(value) for value in row) for row in scores),
            scaler_center=tuple(float(value) for value in center),
            scaler_scale=tuple(float(value) for value in scale),
            reconstruction_rmse=rmse,
            observations_used=int(raw.shape[0]),
        )

    def detect_regimes(
        self,
        matrix: Sequence[Sequence[float]],
        timestamps: Sequence[str],
        feature_names: Sequence[str],
        *,
        rolling_window: int = 126,
    ) -> tuple[PcaRegimePoint, ...]:
        raw = _as_finite_matrix(matrix, name="matrix")
        if len(timestamps) != raw.shape[0]:
            raise DiagnosticValidationError("timestamps must match the matrix row count.")
        if rolling_window < self.config.min_observations:
            raise DiagnosticValidationError("rolling_window must meet the configured PCA minimum.")
        if raw.shape[0] <= rolling_window:
            raise DiagnosticValidationError("matrix must contain observations after the rolling window.")

        previous_components: np.ndarray | None = None
        points: list[PcaRegimePoint] = []
        for observation_index in range(rolling_window, raw.shape[0]):
            # Training data ends strictly before the evaluated observation: no look-ahead.
            history = raw[observation_index - rolling_window : observation_index]
            model, scaler, historical_scores = self._fit(history, feature_names)
            current_scaled = scaler.transform(raw[observation_index : observation_index + 1])
            current_score = model.transform(current_scaled)[0]
            score_mean = np.mean(historical_scores, axis=0)
            score_std = np.std(historical_scores, axis=0, ddof=1)
            score_std = np.where(score_std <= np.finfo(float).eps, 1.0, score_std)
            z_scores = (current_score - score_mean) / score_std

            current_components = _align_component_signs(model.components_)
            angle: float | None = None
            if previous_components is not None:
                shared_dimension = min(previous_components.shape[0], current_components.shape[0])
                angles = np.degrees(subspace_angles(previous_components[:shared_dimension].T, current_components[:shared_dimension].T))
                angle = float(np.max(angles))

            max_abs_z = float(np.max(np.abs(z_scores)))
            reasons: list[str] = []
            if max_abs_z >= self.config.regime_z_threshold:
                reasons.append("factor score exceeds configured z-score threshold")
            if angle is not None and angle >= self.config.principal_angle_threshold_degrees:
                reasons.append("principal-component subspace angle exceeds configured threshold")
            points.append(
                PcaRegimePoint(
                    timestamp=str(timestamps[observation_index]),
                    pc_z_scores=tuple(float(value) for value in z_scores),
                    max_abs_pc_z_score=max_abs_z,
                    max_principal_angle_degrees=angle,
                    regime_shift=bool(reasons),
                    reasons=tuple(reasons),
                )
            )
            previous_components = current_components
        return tuple(points)
