# SignalForge Studio — Product and Delivery Plan

**Version:** 1.0.0 (planned)
**Product:** SignalForge Studio
**Target:** Windows 10/11 x64 portable desktop executable
**Author:** Manus AI

## 1. Product intent

SignalForge Studio transforms the existing educational DSP primitives into a polished desktop workstation for inspecting sampled one-dimensional signals. The first release will remain deliberately focused: it will let users create or import a signal, inspect its waveform and spectrum, apply a moving-average filter, compare the original and processed data, review clear numerical metrics, and export analysis results without sending any data over a network.

The existing dependency-free module stays usable as a small Python library. The desktop application is a new, separate presentation and workflow layer rather than a replacement for the public DSP API. This preserves the repository's educational value while providing a practical Windows product.

## 2. User-facing capabilities

| Area | Release 1 capability | Acceptance condition |
|---|---|---|
| Signal source | Generate sine, square, impulse, noise, and chirp signals; import one numeric channel from `.csv` or `.txt`. | A user can load or generate a signal and sees its sample count immediately. |
| Analysis | RMS, peak, mean, sample duration, direct DFT magnitude spectrum, dominant frequency, and optional moving average. | Metrics change after each valid analysis operation and are mathematically tested. |
| Visual inspection | Responsive waveform and spectrum canvases with axes, gridlines, hover readout, legends, and an accessible dark theme. | A generated or imported signal can be understood without opening a separate plotting tool. |
| Workflow | Safe input validation, non-destructive processing, reset, CSV export, and an analysis summary export. | Invalid data produces a human-readable inline error and cannot corrupt the active workspace. |
| Product polish | Branded application shell, keyboard shortcuts, progress states, consistent typography and spacing, and an About dialog. | No debug console appears in the packaged Windows application; principal controls are keyboard reachable. |
| Delivery | Automated Windows x64 build, test run, and upload of a versioned executable artifact. | A tagged build produces a downloadable `SignalForge-Studio-<version>-win64.exe`. |

## 3. Experience model

The visual hierarchy uses a compact top command bar, a left “Signal Lab” control pane, a central waveform viewport, a lower spectrum viewport, and a persistent metrics rail. Teal and violet accents distinguish the raw and processed signals, while warning states use amber and errors use red. Controls display measurement units explicitly; the application stores no samples outside of the user-selected import/export locations.

The initial analysis workflow is: select a source, set the sample rate, generate or import, optionally enable smoothing, inspect the time-domain and frequency-domain views, then export the selected results. The app does not attempt live microphone capture, arbitrary multichannel files, code signing, cloud synchronization, or medical/industrial certification in version 1.0. Those features require additional threat modelling, hardware validation, and product decisions.

## 4. Technical architecture

```text
signalforge.py                 Pure DSP primitives and validation
signalforge_studio/
  app.py                       Application bootstrap and metadata
  models.py                    Immutable signal and analysis data models
  services.py                  Import, generation, export, and analysis orchestration
  widgets.py                   Custom high-DPI plot widgets and metrics components
  main_window.py               Qt application shell and interaction controller
  resources/                   Application icon and legal notices
main.py                        Executable entry point
requirements.txt               Runtime/build dependencies
.github/workflows/
  tests.yml                    Cross-version unit tests
  windows-release.yml          Windows build artifact on tag/manual dispatch
```

The desktop UI is built with **PySide6**, the official Qt for Python binding, and native Qt widgets. Qt Charts demonstrates the required line-series and anti-aliased rendering primitives, but the product will use custom `QWidget` painting for tightly controlled dual-series plots, hover readouts, and a dependency-light package [1] [2]. The core remains standard-library Python so that its numerical behavior is transparent and unit-testable.

A GitHub-hosted Windows runner builds the Windows executable because PyInstaller's output is specific to the operating system and interpreter used for the build [3]. The build first produces a `onedir` diagnostic bundle, then packages a signed-checksum portable executable artifact. The release workflow starts only from a version tag or deliberate manual dispatch; it does not create public releases merely because a feature branch is pushed. GitHub Actions artifacts preserve build outputs independently of the final release [4].

## 5. Quality and release gates

| Gate | Evidence required before a public release |
|---|---|
| Numerical correctness | Unit tests cover valid and invalid input, DFT/FFT agreement on supported cases, and export formatting. |
| User-interface smoke test | Headless Qt smoke test can instantiate the main window, generate a signal, analyze it, and close cleanly. |
| Static packaging review | The Windows build performs unit tests before packaging and uploads a SHA-256 checksum alongside the executable. |
| Dependency and license hygiene | Requirements are pinned to compatible major versions; `THIRD_PARTY_NOTICES.md` identifies PySide6/Qt and PyInstaller licensing obligations. |
| Release integrity | The release notes name the commit, version, validation scope, known limitations, and executable checksum. |
| Human approval | Pushing commits and creating a public GitHub release are separate, explicit approval points. |

> The portable executable is not code-signed in version 1.0. Windows reputation prompts can therefore occur. A commercial distribution should add a managed code-signing certificate and protected signing workflow before broad commercial distribution.

## 6. Versioning

The planned first desktop release is `v1.0.0`. It uses semantic versioning: backward-compatible enhancements increment the minor version, compatible fixes increment the patch version, and breaking public API or file-format changes increment the major version.

## References

[1]: https://doc.qt.io/qtforpython-6/ "Qt for Python documentation"
[2]: https://doc.qt.io/qtforpython-6/examples/example_charts_linechart.html "Qt for Python Line Chart example"
[3]: https://pyinstaller.org/en/stable/operating-mode.html "PyInstaller operating modes"
[4]: https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts "GitHub Actions workflow artifacts"
