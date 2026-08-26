"""Main window and interaction controller for SignalForge Studio."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .models import ExportBundle, SignalData
from .risk_window import RiskResearchDialog
from .services import analyse_signal, export_csv, export_summary, generate_signal, import_signal
from .widgets import MetricsPanel, PlotSeries, SignalPlot


ACCENT = QColor("#1bd6c7")
SECONDARY_ACCENT = QColor("#9a86ff")
RAW_COLOR = QColor("#6f86a6")


class SignalForgeWindow(QMainWindow):
    """A production-oriented shell for approachable DSP analysis."""

    def __init__(self) -> None:
        super().__init__()
        self._signal: SignalData | None = None
        self._analysis = None
        self._risk_dialog: RiskResearchDialog | None = None
        self.setWindowTitle(f"SignalForge Studio {__version__}")
        self.setMinimumSize(1120, 720)
        self.resize(1500, 900)
        self.setAccessibleName("SignalForge Studio")
        self._build_actions()
        self._build_ui()
        self._generate_signal()

    def _build_actions(self) -> None:
        self._import_action = QAction("Import signal…", self, shortcut=QKeySequence.StandardKey.Open)
        self._import_action.triggered.connect(self._import_signal)
        self._export_action = QAction("Export time data…", self, shortcut=QKeySequence.StandardKey.Save)
        self._export_action.triggered.connect(self._export_csv)
        self._summary_action = QAction("Export analysis summary…", self)
        self._summary_action.triggered.connect(self._export_summary)
        self._reset_action = QAction("Reset workspace", self, shortcut=QKeySequence("Ctrl+R"))
        self._reset_action.triggered.connect(self._reset_workspace)
        self._exit_action = QAction("Exit", self, shortcut=QKeySequence.StandardKey.Quit)
        self._exit_action.triggered.connect(self.close)
        self._about_action = QAction("About SignalForge Studio", self)
        self._about_action.triggered.connect(self._show_about)
        self._risk_research_action = QAction("Local Risk Research…", self)
        self._risk_research_action.triggered.connect(self._open_risk_research)

        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(self._import_action)
        file_menu.addAction(self._export_action)
        file_menu.addAction(self._summary_action)
        file_menu.addSeparator()
        file_menu.addAction(self._reset_action)
        file_menu.addSeparator()
        file_menu.addAction(self._exit_action)
        analysis_menu = self.menuBar().addMenu("Analysis")
        analysis_menu.addAction(self._risk_research_action)
        help_menu = self.menuBar().addMenu("Help")
        help_menu.addAction(self._about_action)

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 12, 18, 18)
        root_layout.setSpacing(14)
        root_layout.addWidget(self._build_header())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_controls())
        splitter.addWidget(self._build_workspace())
        splitter.addWidget(self._build_metrics())
        splitter.setSizes([310, 940, 250])
        root_layout.addWidget(splitter, 1)
        self.setCentralWidget(root)

        status = QStatusBar()
        status.setSizeGripEnabled(False)
        self.setStatusBar(status)
        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("statusLabel")
        status.addWidget(self._status_label, 1)
        self._status_detail = QLabel("Local analysis · no data leaves your device")
        self._status_detail.setObjectName("mutedLabel")
        status.addPermanentWidget(self._status_detail)

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("appHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)
        mark = QLabel("SF")
        mark.setObjectName("brandMark")
        mark.setFixedSize(40, 40)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(mark)
        title_block = QVBoxLayout()
        title_block.setSpacing(0)
        title = QLabel("SignalForge Studio")
        title.setObjectName("appTitle")
        subtitle = QLabel("A focused workspace for signal exploration")
        subtitle.setObjectName("mutedLabel")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        layout.addLayout(title_block)
        layout.addStretch(1)
        self._header_source = QLabel("SINE GENERATOR")
        self._header_source.setObjectName("sourceBadge")
        layout.addWidget(self._header_source)
        return header

    def _build_controls(self) -> QScrollArea:
        shell = QScrollArea()
        shell.setWidgetResizable(True)
        shell.setFrameShape(QFrame.Shape.NoFrame)
        shell.setObjectName("controlScroll")
        content = QWidget()
        content.setObjectName("controlPane")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 14, 0)
        layout.setSpacing(14)

        heading = QLabel("Signal Lab")
        heading.setObjectName("panelHeading")
        layout.addWidget(heading)
        description = QLabel("Create a synthetic signal or import a single numeric data column.")
        description.setObjectName("mutedLabel")
        description.setWordWrap(True)
        layout.addWidget(description)

        source_group = QGroupBox("Source")
        source_form = QFormLayout(source_group)
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Sine", "Square", "Chirp", "Noise", "Impulse"])
        self.source_combo.currentTextChanged.connect(self._source_changed)
        source_form.addRow("Type", self.source_combo)
        layout.addWidget(source_group)

        parameters = QGroupBox("Parameters")
        parameter_form = QFormLayout(parameters)
        self.frequency_spin = self._double_spin(0.0, 96_000.0, 440.0, 1.0, 2)
        self.frequency_spin.setSuffix(" Hz")
        self.amplitude_spin = self._double_spin(0.0, 1000.0, 1.0, 0.1, 3)
        self.sample_rate_spin = QSpinBox()
        self.sample_rate_spin.setRange(32, 192_000)
        self.sample_rate_spin.setValue(8_192)
        self.sample_rate_spin.setSingleStep(256)
        self.sample_rate_spin.setSuffix(" Hz")
        self.duration_spin = self._double_spin(0.01, 16.0, 0.5, 0.05, 3)
        self.duration_spin.setSuffix(" s")
        self.noise_spin = self._double_spin(0.0, 1.0, 0.03, 0.01, 2)
        parameter_form.addRow("Frequency", self.frequency_spin)
        parameter_form.addRow("Amplitude", self.amplitude_spin)
        parameter_form.addRow("Sample rate", self.sample_rate_spin)
        parameter_form.addRow("Duration", self.duration_spin)
        parameter_form.addRow("Noise mix", self.noise_spin)
        layout.addWidget(parameters)

        processing = QGroupBox("Processing")
        processing_form = QFormLayout(processing)
        self.smoothing_check = QCheckBox("Apply moving average")
        self.smoothing_check.toggled.connect(self._smoothing_toggled)
        self.smoothing_window_spin = QSpinBox()
        self.smoothing_window_spin.setRange(2, 16_384)
        self.smoothing_window_spin.setValue(8)
        self.smoothing_window_spin.setEnabled(False)
        self.smoothing_window_spin.setSuffix(" samples")
        self.smoothing_window_spin.valueChanged.connect(lambda _: self._refresh_analysis())
        processing_form.addRow(self.smoothing_check)
        processing_form.addRow("Window", self.smoothing_window_spin)
        layout.addWidget(processing)

        self.generate_button = QPushButton("Generate & analyze")
        self.generate_button.setObjectName("primaryButton")
        self.generate_button.setDefault(True)
        self.generate_button.clicked.connect(self._generate_signal)
        layout.addWidget(self.generate_button)

        import_button = QPushButton("Import data file…")
        import_button.clicked.connect(self._import_signal)
        layout.addWidget(import_button)
        export_button = QPushButton("Export visible data…")
        export_button.clicked.connect(self._export_csv)
        layout.addWidget(export_button)
        layout.addStretch(1)
        notes = QLabel("Tip: the frequency must remain below the Nyquist frequency (half the sample rate).")
        notes.setObjectName("helpNote")
        notes.setWordWrap(True)
        layout.addWidget(notes)
        shell.setWidget(content)
        return shell

    @staticmethod
    def _double_spin(minimum: float, maximum: float, value: float, step: float, decimals: int) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSingleStep(step)
        spin.setDecimals(decimals)
        spin.setKeyboardTracking(False)
        return spin

    def _build_workspace(self) -> QWidget:
        workspace = QWidget()
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        self.wave_plot = SignalPlot("Waveform", "seconds", "amplitude")
        self.spectrum_plot = SignalPlot("Magnitude spectrum", "Hz", "magnitude")
        visual_splitter = QSplitter(Qt.Orientation.Vertical)
        visual_splitter.setChildrenCollapsible(False)
        visual_splitter.addWidget(self.wave_plot)
        visual_splitter.addWidget(self.spectrum_plot)
        visual_splitter.setSizes([450, 360])
        layout.addWidget(visual_splitter)
        return workspace

    def _build_metrics(self) -> MetricsPanel:
        self.metrics_panel = MetricsPanel()
        self.metrics_panel.setMinimumWidth(220)
        return self.metrics_panel

    def _open_risk_research(self) -> None:
        if self._risk_dialog is None:
            self._risk_dialog = RiskResearchDialog(application_version=__version__, parent=self)
        self._risk_dialog.show()
        self._risk_dialog.raise_()
        self._risk_dialog.activateWindow()

    def _source_changed(self, source: str) -> None:
        analytical = source not in {"Noise", "Impulse"}
        self.frequency_spin.setEnabled(analytical)
        self.noise_spin.setEnabled(source != "Noise")
        if source == "Impulse":
            self.noise_spin.setValue(0.0)

    def _smoothing_toggled(self, enabled: bool) -> None:
        self.smoothing_window_spin.setEnabled(enabled)
        self._refresh_analysis()

    def _generate_signal(self) -> None:
        try:
            self._signal = generate_signal(
                self.source_combo.currentText(),
                sample_rate=float(self.sample_rate_spin.value()),
                duration_seconds=float(self.duration_spin.value()),
                amplitude=float(self.amplitude_spin.value()),
                frequency=float(self.frequency_spin.value()),
                noise_amount=float(self.noise_spin.value()),
            )
            self._header_source.setText(f"{self.source_combo.currentText().upper()} GENERATOR")
            self._refresh_analysis(success_message="Generated and analysed a new signal.")
        except ValueError as error:
            self._show_error(str(error))

    def _import_signal(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import signal samples",
            "",
            "Data files (*.csv *.txt);;All files (*)",
        )
        if not path:
            return
        try:
            self._signal = import_signal(path, sample_rate=float(self.sample_rate_spin.value()))
            self._header_source.setText("IMPORTED DATA")
            self._refresh_analysis(success_message=f"Imported {Path(path).name} using the current sample rate.")
        except ValueError as error:
            self._show_error(str(error))

    def _refresh_analysis(self, success_message: str | None = None) -> None:
        if self._signal is None:
            return
        try:
            window = self.smoothing_window_spin.value() if self.smoothing_check.isChecked() else None
            self._analysis = analyse_signal(self._signal, smoothing_window=window)
        except ValueError as error:
            self._show_error(str(error))
            return
        analysis = self._analysis
        rate = analysis.source.sample_rate
        raw_time = tuple(index / rate for index in range(len(analysis.source.samples)))
        processed_time = tuple(index / rate for index in range(len(analysis.displayed_samples)))
        waveform: list[PlotSeries] = []
        if analysis.processed:
            waveform.append(PlotSeries(raw_time, analysis.source.samples, "Original", RAW_COLOR))
            waveform.append(PlotSeries(processed_time, analysis.displayed_samples, "Smoothed", ACCENT))
        else:
            waveform.append(PlotSeries(raw_time, analysis.displayed_samples, "Signal", ACCENT))
        self.wave_plot.set_series(waveform)
        self.spectrum_plot.set_series(
            [PlotSeries(analysis.frequencies, analysis.magnitudes, "Magnitude", SECONDARY_ACCENT)]
        )
        smoothing_note = f" · MA({analysis.smoothing_window})" if analysis.processed else ""
        self.metrics_panel.set_values(
            {
                "rms": self._number(analysis.rms),
                "peak": self._number(analysis.peak),
                "mean": self._number(analysis.mean),
                "dominant": f"{analysis.dominant_frequency:.2f} Hz",
                "duration": f"{analysis.source.duration_seconds:.4f} s",
                "samples": f"{len(analysis.source.samples):,}",
                "fft": f"{analysis.fft_size:,}",
                "nyquist": f"{analysis.nyquist_frequency:.0f} Hz",
            },
            f"{analysis.source.label} · {analysis.source.sample_rate:,.0f} Hz{smoothing_note}",
        )
        self._status_label.setText(
            success_message or f"Analysed {len(analysis.displayed_samples):,} visible samples in local memory."
        )

    @staticmethod
    def _number(value: float) -> str:
        return f"{value:.5g}"

    def _export_csv(self) -> None:
        if not self._analysis:
            self._show_error("Generate or import a signal before exporting.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export visible time data", "signalforge-data.csv", "CSV files (*.csv)")
        if not path:
            return
        try:
            export_csv(ExportBundle(self._analysis, __version__), path)
            self._status_label.setText(f"Exported time-domain data to {Path(path).name}.")
        except OSError as error:
            self._show_error(f"The data file could not be written: {error}")

    def _export_summary(self) -> None:
        if not self._analysis:
            self._show_error("Generate or import a signal before exporting.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export analysis summary", "signalforge-analysis.json", "JSON files (*.json)"
        )
        if not path:
            return
        try:
            export_summary(ExportBundle(self._analysis, __version__), path)
            self._status_label.setText(f"Exported analysis summary to {Path(path).name}.")
        except OSError as error:
            self._show_error(f"The analysis summary could not be written: {error}")

    def _reset_workspace(self) -> None:
        self.source_combo.setCurrentText("Sine")
        self.frequency_spin.setValue(440.0)
        self.amplitude_spin.setValue(1.0)
        self.sample_rate_spin.setValue(8_192)
        self.duration_spin.setValue(0.5)
        self.noise_spin.setValue(0.03)
        self.smoothing_check.setChecked(False)
        self.smoothing_window_spin.setValue(8)
        self._generate_signal()
        self._status_label.setText("Workspace reset to the default sine signal.")

    def _show_error(self, message: str) -> None:
        self._status_label.setText(message)
        QMessageBox.warning(self, "SignalForge Studio", message)

    def _show_about(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("About SignalForge Studio")
        dialog.setMinimumWidth(430)
        layout = QVBoxLayout(dialog)
        title = QLabel(f"SignalForge Studio {__version__}")
        title.setObjectName("appTitle")
        layout.addWidget(title)
        body = QLabel(
            "A local-first desktop workspace for learning and inspecting sampled signals. "
            "It is built on the SignalForge DSP primitives and does not send signal data over the network."
        )
        body.setWordWrap(True)
        layout.addWidget(body)
        legal = QLabel("Distributed under the repository's MIT License. See THIRD_PARTY_NOTICES.md for packaged dependencies.")
        legal.setObjectName("mutedLabel")
        legal.setWordWrap(True)
        layout.addWidget(legal)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()
