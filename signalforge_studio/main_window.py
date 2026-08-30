from signalforge_finance.indicators import sma, ema, rsi, macd
*** Begin Patch
*** Update File: signalforge_studio/main_window.py
@@
-from .models import ExportBundle, SignalData
-from .services import analyse_signal, export_csv, export_summary, generate_signal, import_signal
-from signalforge_finance.importer import import_market_csv_df, import_market_csv
-from .widgets import MetricsPanel, PlotSeries, SignalPlot, CandlePlot
+from .models import ExportBundle, SignalData
+from .services import analyse_signal, export_csv, export_summary, generate_signal, import_signal
+from signalforge_finance.importer import import_market_csv_df, import_market_csv
+from signalforge_finance.indicators import sma, ema, rsi, macd
+from .widgets import MetricsPanel, PlotSeries, SignalPlot, CandlePlot
@@
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
+
+        # Indicators
+        indicators = QGroupBox("Indicators")
+        indicators_form = QFormLayout(indicators)
+        self.sma_check = QCheckBox("Show SMA")
+        self.sma_check.toggled.connect(lambda _: self._refresh_analysis())
+        self.sma_window_spin = QSpinBox()
+        self.sma_window_spin.setRange(1, 65_536)
+        self.sma_window_spin.setValue(8)
+        self.sma_window_spin.valueChanged.connect(lambda _: self._refresh_analysis())
+
+        self.ema_check = QCheckBox("Show EMA")
+        self.ema_check.toggled.connect(lambda _: self._refresh_analysis())
+        self.ema_window_spin = QSpinBox()
+        self.ema_window_spin.setRange(1, 65_536)
+        self.ema_window_spin.setValue(8)
+        self.ema_window_spin.valueChanged.connect(lambda _: self._refresh_analysis())
+
+        self.rsi_check = QCheckBox("Compute RSI")
+        self.rsi_check.toggled.connect(lambda _: self._refresh_analysis())
+        self.rsi_window_spin = QSpinBox()
+        self.rsi_window_spin.setRange(2, 65_536)
+        self.rsi_window_spin.setValue(14)
+        self.rsi_window_spin.valueChanged.connect(lambda _: self._refresh_analysis())
+
+        indicators_form.addRow(self.sma_check, self.sma_window_spin)
+        indicators_form.addRow(self.ema_check, self.ema_window_spin)
+        indicators_form.addRow(self.rsi_check, self.rsi_window_spin)
+        layout.addWidget(indicators)
*** End Patch
