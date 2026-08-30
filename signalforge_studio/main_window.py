*** Begin Patch
*** Update File: signalforge_studio/main_window.py
@@
-from .models import ExportBundle, SignalData
-from .services import analyse_signal, export_csv, export_summary, generate_signal, import_signal
-from .widgets import MetricsPanel, PlotSeries, SignalPlot
+from .models import ExportBundle, SignalData
+from .services import analyse_signal, export_csv, export_summary, generate_signal, import_signal
+from signalforge_finance.importer import import_market_csv_df, import_market_csv
+from .widgets import MetricsPanel, PlotSeries, SignalPlot, CandlePlot
@@
         self._import_action = QAction("Import signal…", self, shortcut=QKeySequence.StandardKey.Open)
         self._import_action.triggered.connect(self._import_signal)
+        self._import_market_action = QAction("Import market CSV…", self)
+        self._import_market_action.triggered.connect(self._import_market_csv)
         self._export_action = QAction("Export time data…", self, shortcut=QKeySequence.StandardKey.Save)
@@
         file_menu = self.menuBar().addMenu("File")
         file_menu.addAction(self._import_action)
+        file_menu.addAction(self._import_market_action)
         file_menu.addAction(self._export_action)
         file_menu.addAction(self._summary_action)
@@
-        self.wave_plot = SignalPlot("Waveform", "seconds", "amplitude")
+        self.wave_plot = SignalPlot("Waveform", "seconds", "amplitude")
+        self.candle_plot = CandlePlot("Price (candles)", "time", "price")
         self.spectrum_plot = SignalPlot("Magnitude spectrum", "Hz", "magnitude")
         visual_splitter = QSplitter(Qt.Orientation.Vertical)
         visual_splitter.setChildrenCollapsible(False)
-        visual_splitter.addWidget(self.wave_plot)
+        visual_splitter.addWidget(self.wave_plot)
+        visual_splitter.addWidget(self.candle_plot)
+        self.candle_plot.hide()
         visual_splitter.addWidget(self.spectrum_plot)
         visual_splitter.setSizes([450, 360])
         layout.addWidget(visual_splitter)
         return workspace
*** End Patch
