# SignalForge DSP

A readable, dependency-free DSP teaching toolkit with RMS, O(n) moving average,
and discrete Fourier-transform magnitudes.

```python
from signalforge import dft_magnitudes, moving_average

smooth = moving_average([1, 2, 3, 4], window=2)
spectrum = dft_magnitudes([1, 0, -1, 0])
```

Run `python -m unittest -v`. The direct DFT is intentionally optimized for
clarity rather than large data sets; production-scale analysis should use FFT.
