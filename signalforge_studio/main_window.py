*** Begin Patch
*** Update File: signalforge_studio/main_window.py
@@
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
-        self.wave_plot.set_series(waveform)
+        # Compute and overlay indicators if requested
+        try:
+            samples_for_indicators = list(analysis.displayed_samples)
+            if self.sma_check.isChecked():
+                sma_vals = sma(samples_for_indicators, int(self.sma_window_spin.value()))
+                waveform.append(PlotSeries(processed_time, tuple(sma_vals), f"SMA({self.sma_window_spin.value()})", QColor("#ffd166")))
+            if self.ema_check.isChecked():
+                ema_vals = ema(samples_for_indicators, int(self.ema_window_spin.value()))
+                waveform.append(PlotSeries(processed_time, tuple(ema_vals), f"EMA({self.ema_window_spin.value()})", QColor("#90be6d")))
+        except Exception:
+            # Indicator computation should not crash the UI; show error in status instead
+            self._status_label.setText("Indicator calculation failed for current settings.")
+
+        self.wave_plot.set_series(waveform)
*** End Patch
