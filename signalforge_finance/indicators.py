*** Begin Patch
*** Update File: signalforge_finance/indicators.py
@@
 def macd(values: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9):
     s = pd.Series(values)
     ema_fast = s.ewm(span=fast, adjust=False).mean()
     ema_slow = s.ewm(span=slow, adjust=False).mean()
     macd_line = ema_fast - ema_slow
     signal_line = macd_line.ewm(span=signal, adjust=False).mean()
     histogram = macd_line - signal_line
     return list(macd_line.to_numpy()), list(signal_line.to_numpy()), list(histogram.to_numpy())
+
+
+def macd_components(values: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9):
+    """Return MACD line, signal line and histogram as pandas Series for plotting/slicing.
+
+    This helper keeps index alignment information when callers need Series.
+    """
+    s = pd.Series(values)
+    ema_fast = s.ewm(span=fast, adjust=False).mean()
+    ema_slow = s.ewm(span=slow, adjust=False).mean()
+    macd_line = ema_fast - ema_slow
+    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
+    histogram = macd_line - signal_line
+    return macd_line, signal_line, histogram
*** End Patch
