# Third-Party Notices

SignalForge Studio is distributed under the repository's MIT License. The Windows executable additionally bundles or uses the third-party components listed below. This document is an operational notice, not a substitute for reviewing the exact license texts included with the final packaged dependencies.

| Component | Purpose | License reference |
|---|---|---|
| [Qt for Python / PySide6](https://doc.qt.io/qtforpython-6/) | Native Qt desktop interface and platform plugins. | Qt for Python is available under LGPLv3, GPLv3, and a commercial license. The distributor must select and comply with the applicable Qt licensing route. [1] |
| [PyInstaller](https://pyinstaller.org/) | Freezes the Python application and its dependencies into the Windows executable. | GPL-2.0-or-later with a bootloader exception; review the upstream project license for exact distribution terms. [2] |
| Python | Runtime included by the packaging process. | Python Software Foundation License Version 2. [3] |

The release workflow is designed to preserve the build input in source control and attach a SHA-256 checksum to each executable. Before commercial distribution, retain the installed package license files, complete the relevant Qt licensing review, and obtain legal review for branding, export controls, product claims, and code-signing policies.

## References

[1]: https://doc.qt.io/qtforpython-6/ "Qt for Python documentation and licensing"
[2]: https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt "PyInstaller license"
[3]: https://docs.python.org/3/license.html "Python license"
