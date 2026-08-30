*** Begin Patch
*** Update File: signalforge_studio/main_window.py
@@
         analysis = self._analysis
         rate = analysis.source.sample_rate
         raw_time = tuple(index / rate for index in range(len(analysis.source.samples)))
         processed_time = tuple(index / rate for index in range(len(analysis.displayed_samples)))
         waveform: list[PlotSeries] = []
@@
-        # Compute and overlay indicators if requested
+        # Compute and overlay indicators if requested
         try:
             samples_for_indicators = list(analysis.displayed_samples)
             if self.sma_check.isChecked():
                 sma_vals = sma(samples_for_indicators, int(self.sma_window_spin.value()))
                 waveform.append(PlotSeries(processed_time, tuple(sma_vals), f"SMA({self.sma_window_spin.value()})", QColor("#ffd166")))
             if self.ema_check.isChecked():
                 ema_vals = ema(samples_for_indicators, int(self.ema_window_spin.value()))
                 waveform.append(PlotSeries(processed_time, tuple(ema_vals), f"EMA({self.ema_window_spin.value()})", QColor("#90be6d")))
+            # MACD and RSI may produce additional subplots
+            macd_series = None
+            if hasattr(self, 'macd_check') and self.macd_check.isChecked():
+                macd_line, signal_line, histogram = macd_components(samples_for_indicators, int(self.macd_fast_spin.value()), int(self.macd_slow_spin.value()), int(self.macd_signal_spin.value()))
+                # store for separate subplot rendering
+                macd_series = (macd_line.to_numpy().tolist(), signal_line.to_numpy().tolist(), histogram.to_numpy().tolist())
+            rsi_series = None
+            if hasattr(self, 'rsi_check') and self.rsi_check.isChecked():
+                rsi_vals = rsi(samples_for_indicators, int(self.rsi_window_spin.value()))
+                rsi_series = list(rsi_vals)
         except Exception:
             # Indicator computation should not crash the UI; show error in status instead
             self._status_label.setText("Indicator calculation failed for current settings.")
 
         self.wave_plot.set_series(waveform)
+        # Render RSI / MACD subplots if present
+        if rsi_series is not None:
+            # For now reuse spectrum_plot for RSI rendering (temporary UI choice)
+            self.spectrum_plot.set_series([PlotSeries(processed_time, tuple(rsi_series), "RSI", QColor("#ff7f50"))])
+        elif macd_series is not None:
+            macd_line, signal_line, histogram = macd_series
+            # overlay macd line and signal line on spectrum_plot as a temporary subplot
+            self.spectrum_plot.set_series([
+                PlotSeries(processed_time, tuple(macd_line), "MACD", QColor("#a66cff")),
+                PlotSeries(processed_time, tuple(signal_line), "Signal", QColor("#54e3d7")),
+            ])
*** End Patch
