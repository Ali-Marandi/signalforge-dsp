"""Local-first research risk metrics for SignalForge.

The functions in this module calculate inspectable risk *estimates* from a
one-dimensional decimal return series. They do not calculate regulatory
capital, connect to market data, submit orders, provide investment advice, or
predict prices. Callers should persist source-data provenance, configuration,
package version, and output hashes in their own RunManifest.
"""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral, Real
from typing import Literal, Sequence

import numpy as np
from scipy.stats import norm

from .diagnostics import DiagnosticValidationError


RiskMethod = Literal["historical", "normal_parametric", "normal_monte_carlo"]


@dataclass(frozen=True, slots=True)
class RiskConfig:
    """Configuration for one-interval local risk diagnostics.

    Returns must be supplied in decimal units: ``0.01`` represents +1%.
    The current module measures a single observation interval only; it does not
    scale results to multi-day horizons or apply regulatory liquidity horizons.
    """

    confidence_level: float = 0.975
    min_observations: int = 100
    simulation_count: int = 10_000
    random_seed: int = 42

    def __post_init__(self) -> None:
        if isinstance(self.confidence_level, bool) or not isinstance(self.confidence_level, Real):
            raise DiagnosticValidationError("confidence_level must be a finite value strictly between 0.50 and 1.0.")
        if not np.isfinite(self.confidence_level) or not 0.50 < self.confidence_level < 1.0:
            raise DiagnosticValidationError("confidence_level must be a finite value strictly between 0.50 and 1.0.")
        if isinstance(self.min_observations, bool) or not isinstance(self.min_observations, Integral):
            raise DiagnosticValidationError("min_observations must be an integer of at least 30.")
        if self.min_observations < 30:
            raise DiagnosticValidationError("min_observations must be at least 30 for a risk diagnostic.")
        if isinstance(self.simulation_count, bool) or not isinstance(self.simulation_count, Integral):
            raise DiagnosticValidationError("simulation_count must be an integer between 1,000 and 1,000,000.")
        if not 1_000 <= self.simulation_count <= 1_000_000:
            raise DiagnosticValidationError("simulation_count must be between 1,000 and 1,000,000.")
        if isinstance(self.random_seed, bool) or not isinstance(self.random_seed, Integral):
            raise DiagnosticValidationError("random_seed must be an integer.")


@dataclass(frozen=True, slots=True)
class RiskEstimate:
    """An inspectable univariate loss-tail estimate in the same unit as inputs."""

    method: RiskMethod
    confidence_level: float
    value_at_risk: float
    expected_shortfall: float
    observations_used: int
    simulation_count: int | None
    random_seed: int | None
    return_mean: float
    return_std: float
    quantile_method: str
    warning_messages: tuple[str, ...]


def _as_finite_returns(values: Sequence[float], *, minimum: int) -> np.ndarray:
    try:
        returns = np.asarray(values, dtype=float)
    except (TypeError, ValueError) as error:
        raise DiagnosticValidationError("returns must be a one-dimensional numeric sequence.") from error
    if returns.ndim != 1:
        raise DiagnosticValidationError("returns must be a one-dimensional sequence.")
    if returns.size < minimum:
        raise DiagnosticValidationError(
            f"Risk diagnostic requires at least {minimum} observations; got {returns.size}."
        )
    if not np.isfinite(returns).all():
        raise DiagnosticValidationError("returns must contain only finite values.")
    return returns


def _warnings_for(returns: np.ndarray, *, tail_count: int, normality_assumed: bool) -> tuple[str, ...]:
    warnings: list[str] = []
    if returns.size < 250:
        warnings.append("Sample has fewer than 250 observations; tail estimates may be unstable.")
    if tail_count < 10:
        warnings.append("Fewer than 10 observations fall in the estimated historical loss tail.")
    if normality_assumed:
        warnings.append("Normal distribution assumption selected; compare with historical loss tails before use.")
    warnings.append("Research estimate only; not a regulatory capital calculation, forecast, or recommendation.")
    return tuple(warnings)


def _loss_tail_summary(losses: np.ndarray, confidence_level: float) -> tuple[float, float, int]:
    """Return VaR/ES using an observed-loss quantile for deterministic tail membership."""
    value_at_risk = float(np.quantile(losses, confidence_level, method="higher"))
    tail = losses[losses >= value_at_risk]
    if tail.size == 0:  # Defensive: ``method='higher'`` guarantees an observed value.
        raise DiagnosticValidationError("No loss-tail observations were available for Expected Shortfall.")
    return value_at_risk, float(np.mean(tail)), int(tail.size)


def _make_estimate(
    *,
    method: RiskMethod,
    returns: np.ndarray,
    losses: np.ndarray,
    config: RiskConfig,
    normality_assumed: bool,
    simulation_count: int | None,
    random_seed: int | None,
) -> RiskEstimate:
    value_at_risk, expected_shortfall, _ = _loss_tail_summary(losses, config.confidence_level)
    _, _, source_tail_count = _loss_tail_summary(-returns, config.confidence_level)
    return RiskEstimate(
        method=method,
        confidence_level=float(config.confidence_level),
        value_at_risk=value_at_risk,
        expected_shortfall=expected_shortfall,
        observations_used=int(returns.size),
        simulation_count=simulation_count,
        random_seed=random_seed,
        return_mean=float(np.mean(returns)),
        return_std=float(np.std(returns, ddof=1)),
        quantile_method="higher_observed_loss",
        warning_messages=_warnings_for(
            returns,
            tail_count=source_tail_count,
            normality_assumed=normality_assumed,
        ),
    )


class LocalRiskEngine:
    """Computes local research risk metrics without file, network, or broker I/O."""

    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()

    def historical(self, returns: Sequence[float]) -> RiskEstimate:
        """Estimate VaR and ES directly from the observed return-loss distribution."""
        series = _as_finite_returns(returns, minimum=self.config.min_observations)
        return _make_estimate(
            method="historical",
            returns=series,
            losses=-series,
            config=self.config,
            normality_assumed=False,
            simulation_count=None,
            random_seed=None,
        )

    def normal_parametric(self, returns: Sequence[float]) -> RiskEstimate:
        """Estimate normal-loss VaR and ES from local sample mean and sample deviation."""
        series = _as_finite_returns(returns, minimum=self.config.min_observations)
        standard_deviation = float(np.std(series, ddof=1))
        if standard_deviation <= np.finfo(float).eps:
            raise DiagnosticValidationError("Normal parametric risk requires a non-zero return standard deviation.")

        mean_loss = -float(np.mean(series))
        z_score = float(norm.ppf(self.config.confidence_level))
        value_at_risk = mean_loss + standard_deviation * z_score
        expected_shortfall = mean_loss + standard_deviation * float(norm.pdf(z_score)) / (
            1.0 - self.config.confidence_level
        )
        # Use the observed historical tail only to communicate the relevant thin-sample warning.
        _, _, tail_count = _loss_tail_summary(-series, self.config.confidence_level)
        return RiskEstimate(
            method="normal_parametric",
            confidence_level=float(self.config.confidence_level),
            value_at_risk=float(value_at_risk),
            expected_shortfall=float(expected_shortfall),
            observations_used=int(series.size),
            simulation_count=None,
            random_seed=None,
            return_mean=float(np.mean(series)),
            return_std=standard_deviation,
            quantile_method="normal_closed_form",
            warning_messages=_warnings_for(series, tail_count=tail_count, normality_assumed=True),
        )

    def normal_monte_carlo(self, returns: Sequence[float]) -> RiskEstimate:
        """Produce a seeded normal scenario tail summary from local source returns.

        The simulation is a reproducible sensitivity scenario, not a forecast or
        a replacement for a stress-testing, regulatory, or investment process.
        """
        series = _as_finite_returns(returns, minimum=self.config.min_observations)
        standard_deviation = float(np.std(series, ddof=1))
        if standard_deviation <= np.finfo(float).eps:
            raise DiagnosticValidationError("Normal Monte Carlo risk requires a non-zero return standard deviation.")

        generator = np.random.default_rng(self.config.random_seed)
        simulated_returns = generator.normal(
            loc=float(np.mean(series)),
            scale=standard_deviation,
            size=self.config.simulation_count,
        )
        return _make_estimate(
            method="normal_monte_carlo",
            returns=series,
            losses=-simulated_returns,
            config=self.config,
            normality_assumed=True,
            simulation_count=self.config.simulation_count,
            random_seed=self.config.random_seed,
        )
