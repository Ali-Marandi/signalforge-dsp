"""Qt dialog for bounded, local-first risk-research calculations."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from .risk_services import (
    ReturnFilePreview,
    RiskResearchRequest,
    RiskResearchRun,
    calculate_risk,
    export_risk_manifest,
    preview_return_file,
)


METHOD_LABELS = {
    "historical": "Historical VaR / Expected Shortfall",
    "normal_parametric": "Normal parametric VaR / Expected Shortfall",
    "normal_monte_carlo": "Seeded normal Monte Carlo VaR / Expected Shortfall",
}


class RiskResearchDialog(QDialog):
    """An explicit local workflow for univariate historical-return diagnostics."""

    def __init__(self, *, application_version: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._application_version = application_version
        self._preview: ReturnFilePreview | None = None
        self._run: RiskResearchRun | None = None
        self.setWindowTitle("Local Risk Research")
        self.setMinimumWidth(660)
        self.resize(760, 760)
        self.setAccessibleName("Local Risk Research")
        self._build_ui()
        self._update_calculate_state()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Local Risk Research")
        title.setObjectName("appTitle")
        layout.addWidget(title)
        boundary = QLabel(
            "Use a local historical return series only. Results are research estimates—not regulatory capital, "
            "forecasts, recommendations, or trading instructions. No selected data is uploaded by this workflow."
        )
        boundary.setObjectName("helpNote")
        boundary.setWordWrap(True)
        layout.addWidget(boundary)

        layout.addWidget(self._build_source_group())
        layout.addWidget(self._build_configuration_group())
        layout.addWidget(self._build_result_group())

        actions = QHBoxLayout()
        self._calculate_button = QPushButton("Calculate local estimate")
        self._calculate_button.setObjectName("primaryButton")
        self._calculate_button.clicked.connect(self._calculate)
        actions.addWidget(self._calculate_button)
        self._export_button = QPushButton("Export local run manifest…")
        self._export_button.setEnabled(False)
        self._export_button.clicked.connect(self._export_manifest)
        actions.addWidget(self._export_button)
        actions.addStretch(1)
        layout.addLayout(actions)

    def _build_source_group(self) -> QGroupBox:
        group = QGroupBox("Local return series")
        form = QFormLayout(group)
        self._source_label = QLabel("No file selected")
        self._source_label.setObjectName("mutedLabel")
        self._source_label.setWordWrap(True)
        form.addRow("Source", self._source_label)

        import_button = QPushButton("Import local return file…")
        import_button.clicked.connect(self._import_file)
        form.addRow(import_button)

        self._column_combo = QComboBox()
        self._column_combo.setObjectName("riskReturnColumn")
        self._column_combo.setEnabled(False)
        self._column_combo.currentIndexChanged.connect(lambda _: self._invalidate_run())
        form.addRow("Return column", self._column_combo)

        self._unit_combo = QComboBox()
        self._unit_combo.setObjectName("riskReturnUnit")
        self._unit_combo.addItem("Decimal return (0.01 = +1%)", "decimal")
        self._unit_combo.addItem("Percent return (1 = +1%)", "percent")
        self._unit_combo.setEnabled(False)
        self._unit_combo.currentIndexChanged.connect(lambda _: self._invalidate_run())
        form.addRow("Declared unit", self._unit_combo)
        return group

    def _build_configuration_group(self) -> QGroupBox:
        group = QGroupBox("Method and configuration")
        form = QFormLayout(group)

        self._method_combo = QComboBox()
        self._method_combo.setObjectName("riskMethod")
        for method, label in METHOD_LABELS.items():
            self._method_combo.addItem(label, method)
        self._method_combo.currentIndexChanged.connect(self._method_changed)
        form.addRow("Method", self._method_combo)

        self._confidence_spin = QDoubleSpinBox()
        self._confidence_spin.setObjectName("riskConfidence")
        self._confidence_spin.setRange(0.501, 0.999)
        self._confidence_spin.setDecimals(3)
        self._confidence_spin.setSingleStep(0.005)
        self._confidence_spin.setValue(0.975)
        self._confidence_spin.valueChanged.connect(lambda _: self._invalidate_run())
        form.addRow("Confidence level", self._confidence_spin)

        self._minimum_spin = QSpinBox()
        self._minimum_spin.setRange(30, 100_000)
        self._minimum_spin.setValue(100)
        self._minimum_spin.valueChanged.connect(lambda _: self._invalidate_run())
        form.addRow("Minimum observations", self._minimum_spin)

        self._simulation_spin = QSpinBox()
        self._simulation_spin.setObjectName("riskSimulationCount")
        self._simulation_spin.setRange(1_000, 1_000_000)
        self._simulation_spin.setSingleStep(1_000)
        self._simulation_spin.setValue(10_000)
        self._simulation_spin.valueChanged.connect(lambda _: self._invalidate_run())
        form.addRow("Monte Carlo scenarios", self._simulation_spin)

        self._seed_spin = QSpinBox()
        self._seed_spin.setObjectName("riskRandomSeed")
        self._seed_spin.setRange(-2_147_483_648, 2_147_483_647)
        self._seed_spin.setValue(42)
        self._seed_spin.valueChanged.connect(lambda _: self._invalidate_run())
        form.addRow("Random seed", self._seed_spin)

        self._acknowledgement = QCheckBox(
            "I understand this is a local research estimate and not a forecast, recommendation, capital calculation, or order instruction."
        )
        self._acknowledgement.setObjectName("riskResearchAcknowledgement")
        self._acknowledgement.toggled.connect(self._update_calculate_state)
        form.addRow(self._acknowledgement)
        return group

    def _build_result_group(self) -> QGroupBox:
        group = QGroupBox("Result")
        layout = QVBoxLayout(group)
        form = QFormLayout()
        self._result_method = QLabel("—")
        self._result_confidence = QLabel("—")
        self._result_var = QLabel("—")
        self._result_es = QLabel("—")
        self._result_observations = QLabel("—")
        self._result_scenario = QLabel("—")
        for label in (
            self._result_method,
            self._result_confidence,
            self._result_var,
            self._result_es,
            self._result_observations,
            self._result_scenario,
        ):
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow("Method", self._result_method)
        form.addRow("Confidence", self._result_confidence)
        form.addRow("Value at Risk", self._result_var)
        form.addRow("Expected Shortfall", self._result_es)
        form.addRow("Source observations", self._result_observations)
        form.addRow("Scenario details", self._result_scenario)
        layout.addLayout(form)
        warning_title = QLabel("Warnings and limitations")
        warning_title.setObjectName("metricName")
        layout.addWidget(warning_title)
        self._warning_text = QTextEdit()
        self._warning_text.setObjectName("riskWarnings")
        self._warning_text.setReadOnly(True)
        self._warning_text.setMinimumHeight(100)
        self._warning_text.setPlainText("Choose a local return series, acknowledge the research boundary, and calculate explicitly.")
        layout.addWidget(self._warning_text)
        return group

    def _import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import local return series",
            "",
            "Return files (*.csv *.txt);;All files (*)",
        )
        if not path:
            return
        try:
            preview = preview_return_file(path)
        except ValueError as error:
            self._show_error(str(error))
            return
        self._preview = preview
        self._column_combo.blockSignals(True)
        self._column_combo.clear()
        self._column_combo.addItems(preview.headers)
        self._column_combo.blockSignals(False)
        self._column_combo.setEnabled(True)
        self._unit_combo.setEnabled(True)
        self._source_label.setText(
            f"{preview.source_name} · {len(preview.data_rows):,} data rows · local SHA-256 {preview.source_sha256[:12]}…"
        )
        self._invalidate_run()

    def _method_changed(self) -> None:
        is_monte_carlo = self._method_combo.currentData() == "normal_monte_carlo"
        self._simulation_spin.setEnabled(is_monte_carlo)
        self._seed_spin.setEnabled(is_monte_carlo)
        self._invalidate_run()

    def _request(self) -> RiskResearchRequest:
        return RiskResearchRequest(
            method=self._method_combo.currentData(),
            confidence_level=float(self._confidence_spin.value()),
            min_observations=int(self._minimum_spin.value()),
            simulation_count=int(self._simulation_spin.value()),
            random_seed=int(self._seed_spin.value()),
            return_column=self._column_combo.currentText(),
            return_unit=self._unit_combo.currentData(),
        )

    def _calculate(self) -> None:
        if self._preview is None:
            self._show_error("Import and select a local return series before calculating.")
            return
        self._calculate_button.setEnabled(False)
        try:
            run = calculate_risk(
                self._preview,
                self._request(),
                research_use_acknowledged=self._acknowledgement.isChecked(),
            )
        except ValueError as error:
            self._show_error(str(error))
            return
        finally:
            self._update_calculate_state()
        self._run = run
        self._export_button.setEnabled(True)
        estimate = run.estimate
        self._result_method.setText(METHOD_LABELS[estimate.method])
        self._result_confidence.setText(f"{estimate.confidence_level:.1%}")
        self._result_var.setText(self._format_loss(estimate.value_at_risk))
        self._result_es.setText(self._format_loss(estimate.expected_shortfall))
        self._result_observations.setText(f"{estimate.observations_used:,}")
        if estimate.simulation_count is None:
            self._result_scenario.setText("Observed/source distribution only")
        else:
            self._result_scenario.setText(
                f"{estimate.simulation_count:,} scenarios · seed {estimate.random_seed}"
            )
        self._warning_text.setPlainText("\n".join(f"• {warning}" for warning in estimate.warning_messages))

    @staticmethod
    def _format_loss(value: float) -> str:
        return f"{value:.6f} decimal loss ({value:.3%})"

    def _export_manifest(self) -> None:
        if self._run is None:
            self._show_error("Calculate a local risk estimate before exporting a manifest.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export local risk run manifest",
            "signalforge-risk-run.json",
            "JSON files (*.json)",
        )
        if not path:
            return
        try:
            destination = export_risk_manifest(
                self._run,
                Path(path),
                application_version=self._application_version,
            )
        except OSError as error:
            self._show_error(f"The risk manifest could not be written: {error}")
            return
        self._warning_text.append(f"\nManifest exported locally to {destination.name}.")

    def _invalidate_run(self) -> None:
        self._run = None
        self._export_button.setEnabled(False)
        self._update_calculate_state()

    def _update_calculate_state(self) -> None:
        ready = self._preview is not None and self._acknowledgement.isChecked()
        self._calculate_button.setEnabled(ready)

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, "Local Risk Research", message)
