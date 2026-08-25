"""Custom Qt widgets used by SignalForge Studio."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFontMetrics, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


@dataclass(frozen=True, slots=True)
class PlotSeries:
    """A labeled, colored sequence to be rendered by :class:`SignalPlot`."""

    x: tuple[float, ...]
    y: tuple[float, ...]
    label: str
    color: QColor


class SignalPlot(QWidget):
    """A lightweight high-DPI line plot without a heavyweight plotting stack."""

    def __init__(self, title: str, x_unit: str, y_unit: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._x_unit = x_unit
        self._y_unit = y_unit
        self._series: list[PlotSeries] = []
        self._hover_point: QPointF | None = None
        self._plot_rect = self.rect()
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setAccessibleName(f"{title} plot")

    def set_series(self, series: list[PlotSeries]) -> None:
        """Replace visible series and schedule a repaint."""
        self._series = [item for item in series if item.x and item.y and len(item.x) == len(item.y)]
        self.update()

    def clear(self) -> None:
        """Clear all plot data."""
        self._series = []
        self._hover_point = None
        self.update()

    @staticmethod
    def _format_value(value: float) -> str:
        absolute = abs(value)
        if absolute >= 10_000 or (absolute and absolute < 0.01):
            return f"{value:.2e}"
        if absolute >= 100:
            return f"{value:.0f}"
        if absolute >= 10:
            return f"{value:.1f}"
        return f"{value:.3f}"

    def _bounds(self) -> tuple[float, float, float, float]:
        x_values = [value for item in self._series for value in item.x if isfinite(value)]
        y_values = [value for item in self._series for value in item.y if isfinite(value)]
        if not x_values or not y_values:
            return 0.0, 1.0, -1.0, 1.0
        x_min, x_max = min(x_values), max(x_values)
        y_min, y_max = min(y_values), max(y_values)
        if x_min == x_max:
            x_min -= 0.5
            x_max += 0.5
        if y_min == y_max:
            padding = max(abs(y_min) * 0.2, 1.0)
            y_min -= padding
            y_max += padding
        else:
            padding = (y_max - y_min) * 0.12
            y_min -= padding
            y_max += padding
        return x_min, x_max, y_min, y_max

    def _point_for(self, x: float, y: float, bounds: tuple[float, float, float, float]) -> QPointF:
        x_min, x_max, y_min, y_max = bounds
        x_position = self._plot_rect.left() + (x - x_min) / (x_max - x_min) * self._plot_rect.width()
        y_position = self._plot_rect.bottom() - (y - y_min) / (y_max - y_min) * self._plot_rect.height()
        return QPointF(x_position, y_position)

    def paintEvent(self, event: object) -> None:  # noqa: N802 - Qt callback name
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        background = QColor("#101826")
        plot_background = QColor("#0c1320")
        painter.fillRect(self.rect(), background)

        painter.setPen(QPen(QColor("#f4f7fb")))
        title_font = painter.font()
        title_font.setBold(True)
        title_base_size = title_font.pointSizeF()
        title_font.setPointSizeF((title_base_size if title_base_size > 0 else 10.0) + 1.0)
        painter.setFont(title_font)
        painter.drawText(18, 27, self._title)

        self._plot_rect = self.rect().adjusted(58, 44, -22, -42)
        painter.fillRect(self._plot_rect, plot_background)
        bounds = self._bounds()
        x_min, x_max, y_min, y_max = bounds
        grid_pen = QPen(QColor("#26354b"), 1, Qt.PenStyle.DotLine)
        painter.setPen(grid_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for step in range(1, 5):
            x = self._plot_rect.left() + self._plot_rect.width() * step / 5
            y = self._plot_rect.top() + self._plot_rect.height() * step / 5
            painter.drawLine(int(x), self._plot_rect.top(), int(x), self._plot_rect.bottom())
            painter.drawLine(self._plot_rect.left(), int(y), self._plot_rect.right(), int(y))

        axis_pen = QPen(QColor("#53657f"), 1)
        painter.setPen(axis_pen)
        painter.drawRect(self._plot_rect)
        label_pen = QPen(QColor("#9dafc7"))
        painter.setPen(label_pen)
        label_font = painter.font()
        base_point_size = label_font.pointSizeF()
        label_font.setPointSizeF(max(8.0, (base_point_size if base_point_size > 0 else 9.0) - 1.0))
        painter.setFont(label_font)
        font_metrics = QFontMetrics(label_font)
        for step in range(6):
            x_value = x_min + (x_max - x_min) * step / 5
            y_value = y_min + (y_max - y_min) * (5 - step) / 5
            x_label = self._format_value(x_value)
            y_label = self._format_value(y_value)
            x_position = self._plot_rect.left() + self._plot_rect.width() * step / 5
            y_position = self._plot_rect.top() + self._plot_rect.height() * step / 5
            painter.drawText(int(x_position - font_metrics.horizontalAdvance(x_label) / 2), self.height() - 15, x_label)
            painter.drawText(8, int(y_position + font_metrics.height() / 3), y_label)
        painter.drawText(self._plot_rect.left(), self.height() - 2, f"{self._x_unit}")
        painter.save()
        painter.translate(15, self._plot_rect.bottom())
        painter.rotate(-90)
        painter.drawText(0, 0, self._y_unit)
        painter.restore()

        if not self._series:
            painter.setPen(QPen(QColor("#7d91ad")))
            painter.drawText(self._plot_rect, Qt.AlignmentFlag.AlignCenter, "Generate or import a signal to begin analysis")
            painter.end()
            return

        painter.save()
        painter.setClipRect(self._plot_rect)
        for item in self._series:
            path = QPainterPath()
            stride = max(1, len(item.x) // max(2, self._plot_rect.width() * 2))
            first = True
            for index in range(0, len(item.x), stride):
                point = self._point_for(item.x[index], item.y[index], bounds)
                if first:
                    path.moveTo(point)
                    first = False
                else:
                    path.lineTo(point)
            if (len(item.x) - 1) % stride:
                point = self._point_for(item.x[-1], item.y[-1], bounds)
                path.lineTo(point)
            painter.setPen(QPen(item.color, 1.65))
            painter.drawPath(path)
        painter.restore()

        legend_x = self._plot_rect.right() - 8
        for item in reversed(self._series):
            width = font_metrics.horizontalAdvance(item.label) + 28
            legend_x -= width
            painter.setPen(QPen(item.color, 2.5))
            painter.drawLine(legend_x, 28, legend_x + 14, 28)
            painter.setPen(QPen(QColor("#b9c9de")))
            painter.drawText(legend_x + 19, 32, item.label)
            legend_x -= 12

        if self._hover_point and self._plot_rect.contains(self._hover_point.toPoint()):
            hover_x = max(self._plot_rect.left(), min(self._plot_rect.right(), self._hover_point.x()))
            normalized = (hover_x - self._plot_rect.left()) / max(1, self._plot_rect.width())
            data_x = x_min + normalized * (x_max - x_min)
            painter.setPen(QPen(QColor("#e8edf6"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(int(hover_x), self._plot_rect.top(), int(hover_x), self._plot_rect.bottom())
            text = f"{self._format_value(data_x)} {self._x_unit}"
            text_width = font_metrics.horizontalAdvance(text) + 12
            text_x = min(int(hover_x) + 8, self._plot_rect.right() - text_width)
            painter.fillRect(text_x, self._plot_rect.top() + 8, text_width, font_metrics.height() + 8, QColor("#17253a"))
            painter.setPen(QPen(QColor("#f2f6fb")))
            painter.drawText(text_x + 6, self._plot_rect.top() + font_metrics.height() + 10, text)
        painter.end()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt callback name
        self._hover_point = event.position()
        self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event: object) -> None:  # noqa: N802 - Qt callback name
        self._hover_point = None
        self.update()
        super().leaveEvent(event)


class MetricsPanel(QFrame):
    """A compact panel that presents headline analysis numbers consistently."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("metricsPanel")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._values: dict[str, QLabel] = {}
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)

        heading = QLabel("Analysis")
        heading.setObjectName("panelHeading")
        heading.setAccessibleName("Analysis metrics")
        outer.addWidget(heading)
        self._subtitle = QLabel("Waiting for a signal")
        self._subtitle.setObjectName("mutedLabel")
        self._subtitle.setWordWrap(True)
        outer.addWidget(self._subtitle)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(13)
        for row, (key, label) in enumerate(
            [
                ("rms", "RMS"),
                ("peak", "Peak"),
                ("mean", "Mean"),
                ("dominant", "Dominant"),
                ("duration", "Duration"),
                ("samples", "Samples"),
                ("fft", "FFT size"),
                ("nyquist", "Nyquist"),
            ]
        ):
            name = QLabel(label)
            name.setObjectName("metricName")
            value = QLabel("—")
            value.setObjectName("metricValue")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(name, row, 0)
            grid.addWidget(value, row, 1)
            self._values[key] = value
        outer.addLayout(grid)
        outer.addStretch(1)

    def set_values(self, values: dict[str, str], subtitle: str) -> None:
        """Set displayed metrics using text preformatted by the controller."""
        self._subtitle.setText(subtitle)
        for key, widget in self._values.items():
            widget.setText(values.get(key, "—"))

    def clear(self) -> None:
        """Reset the panel while no signal is loaded."""
        self.set_values({}, "Waiting for a signal")
