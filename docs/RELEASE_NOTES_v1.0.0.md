# SignalForge Studio v1.0.0 — Proposed Release Notes

**Status:** Proposed; not published
**Distribution:** Windows 10/11 x64 portable executable
**Release tag:** `v1.0.0`

SignalForge Studio v1.0.0 introduces a polished local desktop application around the SignalForge DSP toolkit. This release is designed for teaching, exploratory analysis, and repeatable demonstrations of sampled one-dimensional signals.

## Highlights

| Area | What is new |
|---|---|
| Desktop experience | A high-DPI dark desktop workspace with a clear Signal Lab control surface, time-domain waveform, frequency-domain magnitude spectrum, and live metrics rail. |
| Signal creation | Sine, square, chirp, impulse, and noise generators with configurable sample rate, duration, amplitude, frequency, and noise mix. |
| Import and export | UTF-8 `.csv`/`.txt` numeric signal import; visible time-domain CSV export; readable JSON analysis-summary export. |
| DSP capabilities | RMS, mean, peak, normalized radix-2 FFT magnitudes, dominant frequency, Nyquist value, and optional O(n) moving-average smoothing. |
| Library evolution | The existing direct DFT and moving-average APIs remain compatible; finite-value validation and FFT/frequency-bin helpers extend the core. |
| Delivery pipeline | GitHub Actions runs the full test suite, builds a Windows x64 EXE on a Windows runner, supplies a SHA-256 checksum, stores a build artifact, and publishes only when a version tag is deliberately pushed. |

## Validation completed

The complete 10-test regression suite passes, including core numerical behavior, direct-DFT/FFT agreement, data import/export, aliasing validation, and an offscreen Qt desktop smoke test. A local PyInstaller `onedir` package was also built and launched in offscreen mode without errors. The final Windows `onefile` executable will be built by the version-tag workflow on a Windows runner.

## Known limitations

This release accepts one-dimensional numeric data only. It does not provide live audio capture, multi-channel import, hardware drivers, code signing, cloud synchronization, medical certification, or safety-critical validation. A Windows security reputation prompt may occur until a future signed build is introduced.

## Assets expected on the public release

| File | Purpose |
|---|---|
| `SignalForge-Studio-v1.0.0-win64.exe` | Portable Windows x64 desktop executable. |
| `SignalForge-Studio-v1.0.0-win64.exe.sha256` | Integrity checksum for the executable. |
| `THIRD_PARTY_NOTICES.md` | Third-party dependency and license notice. |

## Verification guidance

After downloading the executable and checksum on Windows PowerShell, verify integrity with:

```powershell
(Get-FileHash .\SignalForge-Studio-v1.0.0-win64.exe -Algorithm SHA256).Hash.ToLower()
Get-Content .\SignalForge-Studio-v1.0.0-win64.exe.sha256
```

The two SHA-256 values must match exactly before the executable is launched.
