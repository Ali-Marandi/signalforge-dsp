"""Headless smoke test for the SignalForge Studio Qt interface."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from signalforge_studio.app import create_application
from signalforge_studio.main_window import SignalForgeWindow


class DesktopSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = create_application([])

    def test_default_window_generates_and_analyses_signal(self) -> None:
        window = SignalForgeWindow()
        self.application.processEvents()
        self.assertIsNotNone(window._signal)
        self.assertIsNotNone(window._analysis)
        self.assertGreater(len(window._analysis.magnitudes), 2)
        self.assertIn("analysed", (window.statusBar().currentMessage() or window._status_label.text()).casefold())
        window.close()


if __name__ == "__main__":
    unittest.main()
