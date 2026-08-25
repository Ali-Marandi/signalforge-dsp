"""Render the desktop shell offscreen for a lightweight visual smoke check."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from signalforge_studio.app import create_application
from signalforge_studio.main_window import SignalForgeWindow


if __name__ == "__main__":
    application = create_application([])
    window = SignalForgeWindow()
    window.show()
    application.processEvents()
    target = Path("artifacts/ui-preview.png")
    target.parent.mkdir(exist_ok=True)
    window.grab().save(str(target), "PNG")
    window.close()
