"""Application bootstrap and visual system for SignalForge Studio."""

from __future__ import annotations

import sys

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QFont, QPalette, QColor
from PySide6.QtWidgets import QApplication

from .main_window import SignalForgeWindow


APP_STYLESHEET = """
* {
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog {
    background: #101826;
    color: #e9f0fa;
}
QMenuBar {
    background: #0b1220;
    color: #b8c6da;
    padding: 2px 8px;
}
QMenuBar::item { padding: 6px 10px; border-radius: 5px; }
QMenuBar::item:selected { background: #1a2a40; color: #ffffff; }
QMenu {
    background: #17253a;
    color: #e8eef8;
    border: 1px solid #31435e;
    padding: 6px;
}
QMenu::item { padding: 7px 26px 7px 12px; border-radius: 4px; }
QMenu::item:selected { background: #243a58; }
#appHeader {
    background: #142137;
    border: 1px solid #263a56;
    border-radius: 12px;
}
#brandMark {
    background: #1bd6c7;
    color: #07151c;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 800;
}
#appTitle {
    color: #f5f8fd;
    font-size: 18px;
    font-weight: 700;
}
#panelHeading {
    color: #f0f5fd;
    font-size: 16px;
    font-weight: 700;
}
#mutedLabel, #statusLabel {
    color: #9fb1c8;
}
#sourceBadge {
    color: #1bd6c7;
    border: 1px solid #2b675f;
    background: #112c31;
    border-radius: 10px;
    padding: 6px 9px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
}
#controlPane {
    background: transparent;
}
#controlScroll { background: transparent; border: none; }
QGroupBox {
    color: #dce7f7;
    background: #142137;
    border: 1px solid #273b57;
    border-radius: 10px;
    margin-top: 10px;
    padding: 12px 10px 9px 10px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QLabel { color: #dce6f4; }
QLabel#helpNote {
    color: #8297b3;
    font-size: 11px;
    padding: 6px;
}
QComboBox, QSpinBox, QDoubleSpinBox {
    background: #0d1727;
    color: #eef5ff;
    border: 1px solid #324863;
    border-radius: 6px;
    padding: 6px 8px;
    min-height: 19px;
}
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover { border-color: #4f7895; }
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #1bd6c7; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background: #17253a;
    color: #edf4fc;
    selection-background-color: #254b5a;
    border: 1px solid #314761;
}
QPushButton {
    background: #1a2b43;
    color: #e8f1fc;
    border: 1px solid #395473;
    border-radius: 7px;
    padding: 8px 11px;
    font-weight: 600;
}
QPushButton:hover { background: #253c59; border-color: #58799b; }
QPushButton:pressed { background: #102135; }
QPushButton#primaryButton {
    color: #062023;
    background: #1bd6c7;
    border: 1px solid #4ef3e2;
}
QPushButton#primaryButton:hover { background: #54e3d7; }
QCheckBox { color: #dce7f7; spacing: 7px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #526b88; border-radius: 4px; background: #0c1625; }
QCheckBox::indicator:checked { background: #1bd6c7; border-color: #5cf5e7; }
#metricsPanel {
    background: #142137;
    border: 1px solid #273b57;
    border-radius: 10px;
}
#metricName { color: #91a5bf; }
#metricValue { color: #f2f6fc; font-weight: 700; }
QStatusBar {
    background: #0b1220;
    color: #9fb1c8;
    border-top: 1px solid #202f45;
}
QSplitter::handle { background: #1d2d43; width: 1px; height: 1px; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #31445f; min-height: 30px; border-radius: 5px; }
"""


def create_application(argv: list[str] | None = None) -> QApplication:
    """Create and configure the Qt application before any windows are built."""
    QCoreApplication.setOrganizationName("SignalForge")
    QCoreApplication.setApplicationName("SignalForge Studio")
    QCoreApplication.setApplicationVersion("1.0.0")
    app = QApplication(argv if argv is not None else sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)
    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#101826"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e9f0fa"))
    app.setPalette(palette)
    return app


def run(argv: list[str] | None = None) -> int:
    """Start the desktop application and return Qt's process result."""
    app = create_application(argv)
    window = SignalForgeWindow()
    window.show()
    return app.exec()
