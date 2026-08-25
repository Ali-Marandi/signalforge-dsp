# SignalForge Studio

**SignalForge Studio** is a local-first Windows desktop workspace for generating, importing, exploring, and exporting sampled one-dimensional signals. It pairs an approachable Qt interface with a small, dependency-light Python DSP core, making it useful for teaching, rapid analysis, and repeatable demonstrations.

The application never uploads signal data. A user can generate common waveforms, import a UTF-8 CSV or text signal, apply a non-destructive moving average, inspect a waveform and normalized magnitude spectrum, review practical metrics, and export either the visible samples or an analysis summary.

| Capability | Included in 1.0.0 |
|---|---|
| Signal sources | Sine, square, chirp, impulse, seeded local noise, and imported numeric data. |
| DSP analysis | RMS, mean, peak, radix-2 FFT spectrum, dominant frequency, Nyquist limit, and moving average. |
| Visual workspace | High-DPI dark interface, dual custom plots, metrics rail, hover frequency/time readout, and keyboard-accessible menus. |
| Data exchange | UTF-8 `.csv` / `.txt` import; CSV time-domain export; JSON analysis-summary export. |
| Windows delivery | Automated Windows x64 executable build, SHA-256 checksum, and tagged-release workflow. |

> SignalForge Studio is an analysis and educational tool. It is not certified for medical, safety-critical, metrology, or compliance use.

## Run from source

Use Python 3.10–3.13, create an isolated environment, and install the project requirements.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

The default workspace opens with a 440 Hz sine source. Adjust the source controls, then select **Generate & analyze**. For imported data, use a UTF-8 file with one numeric signal column or a common `time,amplitude` layout; choose the associated sample rate in the UI before importing.

## Test

The complete test suite includes DSP correctness, import/export regression coverage, and a headless desktop smoke test.

```bash
QT_QPA_PLATFORM=offscreen python -m unittest -v
```

On Windows PowerShell, use:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m unittest -v
```

## Build a Windows executable

A Windows executable must be built on Windows because the frozen runtime is platform-specific. The release workflow uses a GitHub-hosted Windows runner to run tests, package `SignalForge-Studio.exe`, calculate a SHA-256 checksum, and store the result as an artifact.

To build locally on Windows after installing requirements:

```powershell
pyinstaller --noconfirm --clean --onefile --windowed `
  --name SignalForge-Studio `
  --version-file packaging/windows_version_info.txt `
  main.py
```

The resulting executable is written to `dist/SignalForge-Studio.exe`. For distribution, retain the matching checksum and the third-party notices.

## Publish a release

Pushing a version tag such as `v1.0.0` invokes the protected `windows-release` workflow. It produces a Windows x64 artifact and creates or updates the matching GitHub Release with the executable and its `.sha256` file. Manual workflow dispatch builds a non-release development artifact only.

Publication requires a deliberate human approval because it changes the public repository and creates a public release. The detailed product scope and release gates are documented in [docs/PRODUCT_PLAN.md](docs/PRODUCT_PLAN.md).

## DSP core API

The original lightweight `signalforge.py` module remains independently usable.

```python
from signalforge import dft_magnitudes, fft_magnitudes, moving_average, rms

samples = [1.0, 0.0, -1.0, 0.0]
smoothed = moving_average(samples, window=2)
level = rms(samples)
spectrum = fft_magnitudes(samples)
```

The direct DFT remains intentionally readable for teaching. The Studio interface uses the included radix-2 FFT for responsive analysis of power-of-two-padded signals.

## Project layout

```text
signalforge.py                 DSP primitives and fast spectrum helpers
signalforge_studio/            Desktop application package
main.py                        Executable entry point
packaging/                     Windows file-version metadata
.github/workflows/             Test and Windows release automation
test_*.py                      Regression and desktop smoke tests
docs/PRODUCT_PLAN.md           Product scope, architecture, and quality gates
```

## License and dependencies

The repository source is available under the [MIT License](LICENSE). The packaged application uses Qt for Python and PyInstaller; review [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) before distributing a Windows executable commercially.
