from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
import time
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QBrush, QImage, QKeySequence, QLinearGradient, QPainter, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem, QGraphicsScene, QGraphicsView

from owndash.core.models import BackgroundConfig
from owndash.themes import Theme
from owndash.sensors.catalog import metric_definition, read_metric
from owndash.widgets.registry import widget_type


@dataclass(frozen=True, slots=True)
class CanvasSize:
    width: int = 480
    height: int = 1920


def _pct(snapshot: dict, section: str) -> float | None:
    value = snapshot.get(section, {}).get("usage" if section in {"cpu", "gpu"} else "percent")
    return float(value) if isinstance(value, (int, float)) else None


def _color(value: object, fallback: str) -> QColor:
    candidate = QColor(str(value))
    return candidate if candidate.isValid() else QColor(fallback)


class WidgetItem(QGraphicsRectItem):
    """Movable, resizable and live-rendered dashboard widget."""

    HANDLE_SIZE = 14.0
    MIN_WIDTH = 40.0
    MIN_HEIGHT = 40.0

    def __init__(
        self,
        kind: str,
        label: str,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        options: dict | None = None,
    ):
        super().__init__(0, 0, width, height)
        self.kind = kind
        self.label = label
        self.snapshot: dict = {}
        self.options: dict = dict(options or {})
        self.snap_size = 10
        self.snap_enabled = True
        self._animation_phase = 0.0
        self._export_mode = False
        self._resizing = False
        self._resize_handle: str | None = None
        self._history: list[float] = []
        self._resize_origin = QPointF()
        self._resize_start_rect = QRectF()
        self._resize_start_pos = QPointF()
        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    def set_snapshot(self, snapshot: dict) -> None:
        self.snapshot = snapshot
        if self.kind in {"chart", "sparkline"}:
            value = read_metric(snapshot, str(self.options.get("metric_key", "cpu.usage")))
            if value is not None:
                self._history.append(value)
                limit = max(10, min(300, int(self.options.get("history_points", 60))))
                if len(self._history) > limit:
                    del self._history[:-limit]
        self.update()

    def set_style_options(self, options: dict) -> None:
        self.options = dict(options)
        locked = bool(self.options.get("locked", False))
        self.setFlag(QGraphicsItem.ItemIsMovable, not locked)
        self.update()

    def set_animation_phase(self, phase: float) -> None:
        self._animation_phase = phase
        if self.animation_is_active():
            self.update()

    def set_export_mode(self, enabled: bool) -> None:
        """Hide editor-only chrome during scene export without changing selection."""
        self._export_mode = bool(enabled)
        self.update()

    def _handle_rects(self) -> dict[str, QRectF]:
        r = self.rect()
        s = self.HANDLE_SIZE
        h = s / 2.0
        return {
            "nw": QRectF(r.left(), r.top(), s, s),
            "n": QRectF(r.center().x() - h, r.top(), s, s),
            "ne": QRectF(r.right() - s, r.top(), s, s),
            "e": QRectF(r.right() - s, r.center().y() - h, s, s),
            "se": QRectF(r.right() - s, r.bottom() - s, s, s),
            "s": QRectF(r.center().x() - h, r.bottom() - s, s, s),
            "sw": QRectF(r.left(), r.bottom() - s, s, s),
            "w": QRectF(r.left(), r.center().y() - h, s, s),
        }

    def _handle_at(self, pos: QPointF) -> str | None:
        if not self.isSelected():
            return None
        for name, rect in self._handle_rects().items():
            if rect.contains(pos):
                return name
        return None

    @staticmethod
    def _cursor_for_handle(handle: str | None):
        return {
            "nw": Qt.SizeFDiagCursor, "se": Qt.SizeFDiagCursor,
            "ne": Qt.SizeBDiagCursor, "sw": Qt.SizeBDiagCursor,
            "n": Qt.SizeVerCursor, "s": Qt.SizeVerCursor,
            "e": Qt.SizeHorCursor, "w": Qt.SizeHorCursor,
        }.get(handle, Qt.OpenHandCursor)

    def nudge(self, dx: float, dy: float) -> None:
        """Move the widget precisely with the keyboard and keep it on-canvas."""
        if bool(self.options.get("locked", False)):
            return
        self.setPos(self.x() + dx, self.y() + dy)

    def hoverMoveEvent(self, event) -> None:  # noqa: ANN001
        self.setCursor(self._cursor_for_handle(self._handle_at(event.pos())))
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event) -> None:  # noqa: ANN001
        self.unsetCursor()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        handle = self._handle_at(event.pos())
        if event.button() == Qt.LeftButton and handle and not bool(self.options.get("locked", False)):
            self._resizing = True
            self._resize_handle = handle
            self._resize_origin = event.scenePos()
            self._resize_start_rect = QRectF(self.rect())
            self._resize_start_pos = QPointF(self.pos())
            event.accept()
            return
        self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: ANN001
        if self._resizing:
            delta = event.scenePos() - self._resize_origin
            handle = self._resize_handle or "se"
            start = self._resize_start_rect
            x = self._resize_start_pos.x()
            y = self._resize_start_pos.y()
            width = start.width()
            height = start.height()
            if "e" in handle:
                width = start.width() + delta.x()
            if "s" in handle:
                height = start.height() + delta.y()
            if "w" in handle:
                width = start.width() - delta.x()
                x = self._resize_start_pos.x() + delta.x()
            if "n" in handle:
                height = start.height() - delta.y()
                y = self._resize_start_pos.y() + delta.y()
            width = max(self.MIN_WIDTH, width)
            height = max(self.MIN_HEIGHT, height)
            if self.snap_enabled:
                width = round(width / self.snap_size) * self.snap_size
                height = round(height / self.snap_size) * self.snap_size
                x = round(x / self.snap_size) * self.snap_size
                y = round(y / self.snap_size) * self.snap_size
            scene_rect = self.scene().sceneRect() if self.scene() else QRectF(0, 0, 480, 1920)
            x = max(0.0, min(x, scene_rect.width() - self.MIN_WIDTH))
            y = max(0.0, min(y, scene_rect.height() - self.MIN_HEIGHT))
            width = min(width, scene_rect.width() - x)
            height = min(height, scene_rect.height() - y)
            self.prepareGeometryChange()
            self.setPos(x, y)
            self.setRect(0, 0, max(self.MIN_WIDTH, width), max(self.MIN_HEIGHT, height))
            event.accept()
            self.update()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001
        self._resizing = False
        self._resize_handle = None
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)
        if self.snap_enabled:
            self.setPos(
                round(self.x() / self.snap_size) * self.snap_size,
                round(self.y() / self.snap_size) * self.snap_size,
            )
        self._clamp_to_canvas()

    def itemChange(self, change, value):  # noqa: ANN001
        if change == QGraphicsItem.ItemPositionChange and self.scene() is not None:
            rect = self.scene().sceneRect()
            proposed = QPointF(value)
            view = self.scene().views()[0] if self.scene().views() else None
            if self.snap_enabled and view is not None and hasattr(view, "snap_widget_position") and not self._resizing:
                proposed = view.snap_widget_position(self, proposed)
            max_x = max(0.0, rect.width() - self.rect().width())
            max_y = max(0.0, rect.height() - self.rect().height())
            return QPointF(min(max(proposed.x(), 0.0), max_x), min(max(proposed.y(), 0.0), max_y))
        return super().itemChange(change, value)

    def _clamp_to_canvas(self) -> None:
        if self.scene() is not None:
            self.setPos(self.pos())

    def _bar(self, painter: QPainter, percent: float | None, top: float, accent: QColor, track: QColor) -> None:
        r = self.rect().adjusted(18, top, -18, -18)
        r.setHeight(12)
        painter.setPen(Qt.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(r, 6, 6)
        if percent is not None:
            filled = QRectF(r)
            filled.setWidth(r.width() * max(0.0, min(100.0, percent)) / 100.0)
            painter.setBrush(accent)
            painter.drawRoundedRect(filled, 6, 6)

    def _gauge_value(self) -> float | None:
        metric_key = str(self.options.get("metric_key", ""))
        if metric_key:
            return read_metric(self.snapshot, metric_key)
        metric = str(self.options.get("gauge_metric", "cpu"))
        legacy = {
            "cpu": "cpu.usage",
            "gpu": "gpu.usage",
            "temperature": "temperature.value",
            "power": "power.total_w",
            "memory": "memory.percent",
        }.get(metric)
        return read_metric(self.snapshot, legacy) if legacy else None

    def _vram_bounds(self, minimum: float, maximum: float) -> tuple[float, float]:
        key = str(self.options.get("metric_key", ""))
        if key == "gpu.vram_percent":
            return 0.0, 100.0
        if key in {"gpu.vram_used_gib", "gpu.vram_total_gib"}:
            total = read_metric(self.snapshot, "gpu.vram_total_gib")
            if total is not None and math.isfinite(total) and total > 0:
                return 0.0, total
        return minimum, maximum

    def _gauge_color(self, value: float | None, accent: QColor, maximum: float) -> QColor:
        active = QColor(accent)
        warn = float(self.options.get("warn", maximum + 1))
        critical = float(self.options.get("critical", maximum + 1))
        if value is not None and value >= critical:
            return QColor("#ff4d5a")
        if value is not None and value >= warn:
            return QColor("#ffb020")
        return active

    def _paint_gauge(self, painter: QPainter, accent: QColor, track: QColor, title_color: QColor, value_color: QColor) -> None:
        value = self._gauge_value()
        minimum = float(self.options.get("gauge_min", 0))
        maximum = float(self.options.get("gauge_max", 100))
        minimum, maximum = self._vram_bounds(minimum, maximum)
        if maximum <= minimum:
            maximum = minimum + 1.0
        ratio = 0.0 if value is None else max(0.0, min(1.0, (value - minimum) / (maximum - minimum)))
        active = self._gauge_color(value, accent, maximum)
        style = str(self.options.get("gauge_style", "arc"))

        painter.setPen(title_color)
        font = painter.font()
        font.setBold(True)
        font.setPointSize(max(7, min(24, int(self.options.get("title_size", 10)))))
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(16, 12, -16, -12), Qt.AlignTop | Qt.AlignHCenter, self.label)

        unit = str(self.options.get("gauge_unit", "%"))
        metric_key = str(self.options.get("metric_key", ""))
        if metric_key in {"gpu.vram_used_gib", "gpu.vram_total_gib"}:
            unit = "GiB"
        elif metric_key == "gpu.vram_percent":
            unit = "%"
        decimals = 1 if unit == "GiB" else 0
        text = "—" if value is None else f"{value:.{decimals}f} {unit}"
        painter.setPen(value_color)
        font.setPointSize(max(12, min(42, int(self.options.get("value_size", 18)) + 6)))
        painter.setFont(font)

        r = self.rect().adjusted(28, 48, -28, -24)
        if style == "bar":
            bar = QRectF(r.left(), r.center().y() - 14, r.width(), 28)
            painter.setPen(Qt.NoPen)
            painter.setBrush(track)
            painter.drawRoundedRect(bar, 14, 14)
            active_bar = QRectF(bar)
            active_bar.setWidth(bar.width() * ratio)
            painter.setBrush(active)
            painter.drawRoundedRect(active_bar, 14, 14)
            painter.setPen(value_color)
            painter.drawText(r, Qt.AlignCenter, text)
            return

        side = min(r.width(), r.height())
        gauge = QRectF(r.center().x() - side / 2, r.center().y() - side / 2, side, side)
        pen_width = max(8.0, min(22.0, side * 0.07))
        painter.setBrush(Qt.NoBrush)
        if style == "ring":
            start, span = 90 * 16, -360 * 16
        elif style == "semi":
            start, span = 180 * 16, -180 * 16
            gauge.translate(0, side * 0.12)
        else:
            start, span = 225 * 16, -270 * 16
        painter.setPen(QPen(track, pen_width, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(gauge, start, span)
        painter.setPen(QPen(active, pen_width, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(gauge, start, int(span * ratio))
        painter.setPen(value_color)
        painter.drawText(gauge, Qt.AlignCenter, text)

    def _paint_chart(self, painter: QPainter, accent: QColor, track: QColor, title_color: QColor, value_color: QColor) -> None:
        metric_key = str(self.options.get("metric_key", "cpu.usage"))
        metric = metric_definition(metric_key)
        label = self.label or (metric.label if metric else "Diagramm")
        current = read_metric(self.snapshot, metric_key)
        unit = str(self.options.get("gauge_unit") or (metric.unit if metric else ""))
        if metric_key in {"gpu.vram_used_gib", "gpu.vram_total_gib"}:
            unit = "GiB"
        elif metric_key == "gpu.vram_percent":
            unit = "%"

        painter.setPen(title_color)
        font = painter.font()
        font.setBold(True)
        font.setPointSize(max(7, min(24, int(self.options.get("title_size", 10)))))
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(16, 10, -16, -10), Qt.AlignTop | Qt.AlignLeft, label)

        painter.setPen(value_color)
        font.setPointSize(max(10, min(30, int(self.options.get("value_size", 18)))))
        painter.setFont(font)
        current_text = "—" if current is None else f"{current:.1f} {unit}".strip()
        painter.drawText(self.rect().adjusted(16, 34, -16, -10), Qt.AlignTop | Qt.AlignRight, current_text)

        plot = self.rect().adjusted(18, 62, -18, -18)
        painter.setPen(QPen(track, 1))
        painter.drawLine(plot.left(), plot.bottom(), plot.right(), plot.bottom())
        if len(self._history) < 2:
            return
        minimum = float(self.options.get("chart_min", metric.minimum if metric else min(self._history)))
        maximum = float(self.options.get("chart_max", metric.maximum if metric else max(self._history)))
        minimum, maximum = self._vram_bounds(minimum, maximum)
        if maximum <= minimum:
            maximum = minimum + 1.0
        points = []
        count = len(self._history)
        for index, sample in enumerate(self._history):
            x = plot.left() + (plot.width() * index / max(1, count - 1))
            ratio = max(0.0, min(1.0, (sample - minimum) / (maximum - minimum)))
            y = plot.bottom() - ratio * plot.height()
            points.append(QPointF(x, y))
        style = str(self.options.get("chart_style", "line"))
        if style == "area":
            from PySide6.QtGui import QPolygonF
            polygon = QPolygonF([QPointF(plot.left(), plot.bottom()), *points, QPointF(plot.right(), plot.bottom())])
            fill = QColor(accent)
            fill.setAlpha(55)
            painter.setPen(Qt.NoPen)
            painter.setBrush(fill)
            painter.drawPolygon(polygon)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(accent, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        for first, second in zip(points, points[1:]):
            painter.drawLine(first, second)

    def _content(self) -> tuple[str, str, float | None]:
        s = self.snapshot
        if self.kind == "cpu":
            value = _pct(s, "cpu")
            return self.label or "CPU", "—" if value is None else f"{value:.0f} %", value
        if self.kind == "gpu":
            value = _pct(s, "gpu")
            temp = s.get("gpu", {}).get("temperature")
            extra = "" if temp is None else f"  ·  {temp:.0f} °C"
            return self.label or "GPU", ("—" if value is None else f"{value:.0f} %") + extra, value
        if self.kind == "memory":
            value = _pct(s, "memory")
            return self.label or "Arbeitsspeicher", "—" if value is None else f"{value:.0f} %", value
        if self.kind == "storage":
            value = _pct(s, "storage")
            return self.label or "Speicher /", "—" if value is None else f"{value:.0f} %", value
        if self.kind == "network":
            net = s.get("network", {})
            return self.label or "Netzwerk", f"↓ {net.get('down_text', '—')}   ↑ {net.get('up_text', '—')}", None
        if self.kind == "temperature":
            temp = s.get("temperature", {})
            value = temp.get("value")
            return self.label or "Temperatur", "—" if value is None else f"{value:.1f} °C", None
        if self.kind == "power":
            power = s.get("power", {}).get("total_w")
            return self.label or "Leistung", "—" if power is None else f"{power:.1f} W", None
        if self.kind == "clock":
            return self.label or "Uhr", datetime.now().strftime("%H:%M:%S"), None
        if self.kind == "text":
            return self.label or "Text", str(self.options.get("text", "Eigener Text")), None
        if self.kind == "image":
            return self.label or "Bild", "Bild-Widget", None
        return self.label, "", None

    def _paint_selection_handles(self, painter: QPainter, accent: QColor) -> None:
        painter.save()
        painter.setPen(QPen(QColor(255, 255, 255, 220), 1, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setBrush(QBrush(accent))
        for rect in self._handle_rects().values():
            painter.drawRect(rect)
        painter.restore()

    def _trigger_metric_value(self) -> float | None:
        """Return the live value used by conditional animation rules."""
        metric_key = str(self.options.get("metric_key", "")).strip()
        if metric_key:
            value = read_metric(self.snapshot, metric_key)
            if value is not None:
                return float(value)
        fallback = {
            "cpu": "cpu.usage",
            "gpu": "gpu.usage",
            "memory": "memory.percent",
            "temperature": "temperature.value",
            "power": "power.total_w",
            "storage": "storage.percent",
        }.get(self.kind)
        value = read_metric(self.snapshot, fallback) if fallback else None
        return float(value) if value is not None else None

    def animation_is_active(self) -> bool:
        animation = str(self.options.get("animation", "none"))
        if animation == "none":
            return False
        trigger = str(self.options.get("animation_trigger", "always"))
        if trigger == "always":
            return True
        value = self._trigger_metric_value()
        if value is None:
            return False
        warn = float(self.options.get("warn", 75.0))
        critical = float(self.options.get("critical", 90.0))
        threshold = float(self.options.get("animation_trigger_value", 80.0))
        if trigger == "warning":
            return value >= warn
        if trigger == "critical":
            return value >= critical
        if trigger == "above":
            return value >= threshold
        if trigger == "below":
            return value <= threshold
        return True

    @staticmethod
    def _mix_color(a: QColor, b: QColor, amount: float) -> QColor:
        amount = max(0.0, min(1.0, float(amount)))
        return QColor(
            round(a.red() + (b.red() - a.red()) * amount),
            round(a.green() + (b.green() - a.green()) * amount),
            round(a.blue() + (b.blue() - a.blue()) * amount),
            round(a.alpha() + (b.alpha() - a.alpha()) * amount),
        )

    def _alert_mix(self) -> tuple[QColor | None, float]:
        """Smoothly approach warning/critical colors instead of hard switching."""
        if not bool(self.options.get("alert_colors", False)):
            return None, 0.0
        value = self._trigger_metric_value()
        if value is None:
            return None, 0.0
        warn = float(self.options.get("warn", 75.0))
        critical = max(warn + 0.001, float(self.options.get("critical", 90.0)))
        band = max(2.0, abs(critical - warn) * 0.35)
        if value < warn - band:
            return None, 0.0
        warning = QColor("#ffb020")
        danger = QColor("#ff4d5a")
        if value < warn:
            return warning, (value - (warn - band)) / band
        if value < critical:
            return self._mix_color(warning, danger, (value - warn) / (critical - warn)), 0.72
        return danger, 1.0

    def paint(self, painter: QPainter, option, widget=None) -> None:  # noqa: ANN001
        del option, widget
        painter.setRenderHint(QPainter.Antialiasing, True)

        background = _color(self.options.get("background"), "#1c222c")
        border = _color(self.options.get("border"), "#344050")
        accent = _color(self.options.get("accent"), "#53b3ff")
        title_color = _color(self.options.get("title_color"), "#9da9ba")
        value_color = _color(self.options.get("value_color"), "#eef2f8")
        track = _color(self.options.get("bar_track"), "#373f4c")
        opacity = max(0, min(100, int(self.options.get("opacity", 94))))
        radius = max(0, min(40, int(self.options.get("radius", 14))))
        glow = max(0, min(100, int(self.options.get("glow", 0))))
        configured_animation = str(self.options.get("animation", "none"))
        animation = configured_animation if self.animation_is_active() else "none"
        speed = max(25, min(300, int(self.options.get("animation_speed", 100)))) / 100.0
        strength = max(0, min(100, int(self.options.get("animation_strength", 70)))) / 100.0
        phase = self._animation_phase * speed

        # Animation parameters are evaluated entirely in paint(), therefore the
        # editor preview and the USB/JPEG output stay visually identical.
        effect_alpha = 1.0
        effect_glow = 1.0
        if animation == "pulse":
            wave = 0.5 + 0.5 * math.sin(phase)
            effect_alpha = 1.0 - strength * 0.48 * (1.0 - wave)
            effect_glow = 0.55 + 0.75 * wave
        elif animation == "breathe":
            wave = 0.5 + 0.5 * math.sin(phase * 0.55)
            effect_alpha = 1.0 - strength * 0.30 * (1.0 - wave)
            effect_glow = 0.72 + 0.48 * wave
        elif animation == "heartbeat":
            beat1 = max(0.0, math.sin(phase * 1.65)) ** 10
            beat2 = max(0.0, math.sin(phase * 1.65 - 0.72)) ** 14
            beat = min(1.0, beat1 + 0.70 * beat2)
            effect_alpha = 1.0 - strength * 0.28 + strength * 0.28 * beat
            effect_glow = 0.70 + 1.10 * strength * beat
        elif animation == "flicker":
            noise = (
                0.52
                + 0.22 * math.sin(phase * 5.1)
                + 0.16 * math.sin(phase * 11.7 + 1.3)
                + 0.10 * math.sin(phase * 23.9 + 0.4)
            )
            noise = max(0.0, min(1.0, noise))
            effect_alpha = 1.0 - strength * 0.42 * (1.0 - noise)
            effect_glow = 0.45 + 1.25 * strength * noise

        if animation == "colorflow":
            wave = 0.5 + 0.5 * math.sin(phase * 0.72)
            target = _color(self.options.get("animation_color"), "#ff3bd4")
            accent = self._mix_color(accent, target, wave * strength)
            border = self._mix_color(border, target, wave * strength * 0.72)
            value_color = self._mix_color(value_color, target, wave * strength * 0.28)

        alert_target, alert_amount = self._alert_mix()
        if alert_target is not None and alert_amount > 0.0:
            accent = self._mix_color(accent, alert_target, alert_amount)
            border = self._mix_color(border, alert_target, alert_amount * 0.82)
            value_color = self._mix_color(value_color, alert_target, alert_amount * 0.22)

        for color in (border, accent, title_color, value_color, track):
            color.setAlphaF(max(0.0, min(1.0, color.alphaF() * effect_alpha)))

        if glow > 0:
            painter.save()
            glow_color = QColor(accent)
            glow_color.setAlphaF(min(0.88, (glow / 100.0) * 0.62 * effect_alpha * effect_glow))
            for width in (10, 6, 3):
                painter.setPen(QPen(glow_color, width))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), radius, radius)
            painter.restore()

        background.setAlphaF((opacity / 100.0) * effect_alpha)
        selected_border = QColor(accent) if self.isSelected() else QColor(border)
        painter.setPen(QPen(selected_border, 2))
        painter.setBrush(background)
        painter.drawRoundedRect(self.rect(), radius, radius)

        # Moving light effects are drawn inside the widget before its content.
        if animation in {"scanner", "shimmer", "radar"} and strength > 0:
            painter.save()
            painter.setClipPath(self.shape())
            rect = self.rect()
            travel = (math.sin(phase * 0.72) * 0.5 + 0.5)
            if animation == "scanner":
                x = rect.left() + travel * rect.width()
                scan = QColor(accent)
                scan.setAlphaF(min(0.75, 0.18 + 0.57 * strength))
                painter.setPen(QPen(scan, max(2.0, 4.0 + 8.0 * strength)))
                painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            elif animation == "radar":
                angle = phase * 0.72
                center = rect.center()
                length = math.hypot(rect.width(), rect.height())
                end = QPointF(center.x() + math.cos(angle) * length, center.y() + math.sin(angle) * length)
                radar = QColor(self.options.get("animation_color", "#ff3bd4"))
                radar.setAlphaF(min(0.74, 0.14 + 0.60 * strength))
                painter.setPen(QPen(radar, max(2.0, 3.0 + 7.0 * strength)))
                painter.drawLine(center, end)
                halo = QColor(radar)
                halo.setAlphaF(radar.alphaF() * 0.22)
                painter.setPen(QPen(halo, max(8.0, 12.0 + 18.0 * strength)))
                painter.drawLine(center, end)
            else:
                band_width = max(28.0, rect.width() * (0.10 + 0.10 * strength))
                center = rect.left() - band_width + travel * (rect.width() + 2 * band_width)
                gradient = QLinearGradient(center - band_width, rect.top(), center + band_width, rect.bottom())
                clear = QColor(accent)
                clear.setAlpha(0)
                shine = QColor(accent)
                shine.setAlphaF(min(0.62, 0.16 + 0.46 * strength))
                gradient.setColorAt(0.0, clear)
                gradient.setColorAt(0.5, shine)
                gradient.setColorAt(1.0, clear)
                painter.fillRect(rect, QBrush(gradient))
            painter.restore()

        if self.kind.startswith("gauge_"):
            self._paint_gauge(painter, accent, track, title_color, value_color)
            if self.isSelected() and not self._export_mode:
                painter.setPen(QPen(QColor(255, 255, 255), 1, Qt.DashLine))
                painter.setBrush(QBrush(accent))
                painter.drawRect(self._handle_rect())
            return

        if self.kind in {"chart", "sparkline"}:
            self._paint_chart(painter, accent, track, title_color, value_color)
            if self.isSelected() and not self._export_mode:
                painter.setPen(QPen(QColor(255, 255, 255), 1, Qt.DashLine))
                painter.setBrush(QBrush(accent))
                painter.drawRect(self._handle_rect())
            return

        title, value, percent = self._content()
        painter.setPen(title_color)
        font = painter.font()
        font.setPointSize(max(7, min(28, int(self.options.get("title_size", 10)))))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(18, 12, -18, -12), Qt.AlignTop | Qt.AlignLeft, title)

        painter.setPen(value_color)
        font.setPointSize(max(9, min(48, int(self.options.get("value_size", 18)))))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(18, 42, -18, -34), Qt.AlignTop | Qt.AlignLeft, value)

        if percent is not None and self.rect().height() >= 110:
            self._bar(painter, percent, self.rect().height() - 34, accent, track)

        if self.isSelected() and not self._export_mode:
            self._paint_selection_handles(painter, accent)


class BackgroundImageItem(QGraphicsRectItem):
    """Editable background image living behind all dashboard widgets.

    The item keeps the source aspect ratio while resizing and writes its
    geometry back through a callback after mouse interaction.  Because the
    same graphics item is rendered by QGraphicsScene.render(), editor preview
    and USB output stay pixel-identical.
    """

    HANDLE_SIZE = 18.0
    MIN_SIZE = 40.0

    def __init__(self, pixmap: QPixmap, commit_callback):  # noqa: ANN001
        super().__init__()
        self.pixmap = pixmap
        self._commit_callback = commit_callback
        self._editing_enabled = False
        self._export_mode = False
        self._resizing = False
        self._resize_origin = QPointF()
        self._resize_start_rect = QRectF()
        self._aspect = (pixmap.width() / pixmap.height()) if pixmap.height() else 1.0
        self.setZValue(-1000.0)
        self.setAcceptHoverEvents(True)
        self.setPen(Qt.NoPen)
        self.setBrush(Qt.NoBrush)

    def set_export_mode(self, enabled: bool) -> None:
        self._export_mode = bool(enabled)
        self.update()

    def set_editing_enabled(self, enabled: bool) -> None:
        self._editing_enabled = bool(enabled)
        self.setFlag(QGraphicsItem.ItemIsMovable, enabled)
        self.setFlag(QGraphicsItem.ItemIsSelectable, enabled)
        self.setAcceptedMouseButtons(Qt.LeftButton if enabled else Qt.NoButton)
        if not enabled:
            self.setSelected(False)
            self.unsetCursor()
        self.update()

    def _handle_rects(self) -> dict[str, QRectF]:
        r = self.rect()
        s = self.HANDLE_SIZE
        h = s / 2.0
        return {
            "nw": QRectF(r.left(), r.top(), s, s),
            "n": QRectF(r.center().x() - h, r.top(), s, s),
            "ne": QRectF(r.right() - s, r.top(), s, s),
            "e": QRectF(r.right() - s, r.center().y() - h, s, s),
            "se": QRectF(r.right() - s, r.bottom() - s, s, s),
            "s": QRectF(r.center().x() - h, r.bottom() - s, s, s),
            "sw": QRectF(r.left(), r.bottom() - s, s, s),
            "w": QRectF(r.left(), r.center().y() - h, s, s),
        }

    def _handle_at(self, pos: QPointF) -> str | None:
        if not self.isSelected():
            return None
        for name, rect in self._handle_rects().items():
            if rect.contains(pos):
                return name
        return None

    @staticmethod
    def _cursor_for_handle(handle: str | None):
        return {
            "nw": Qt.SizeFDiagCursor, "se": Qt.SizeFDiagCursor,
            "ne": Qt.SizeBDiagCursor, "sw": Qt.SizeBDiagCursor,
            "n": Qt.SizeVerCursor, "s": Qt.SizeVerCursor,
            "e": Qt.SizeHorCursor, "w": Qt.SizeHorCursor,
        }.get(handle, Qt.OpenHandCursor)

    def hoverMoveEvent(self, event) -> None:  # noqa: ANN001
        if not self._editing_enabled:
            self.unsetCursor()
        elif self.isSelected() and self._handle_rect().contains(event.pos()):
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self.setCursor(Qt.OpenHandCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        if (
            self._editing_enabled
            and event.button() == Qt.LeftButton
            and self.isSelected()
            and self._handle_rect().contains(event.pos())
        ):
            self._resizing = True
            self._resize_origin = event.scenePos()
            self._resize_start_rect = QRectF(self.rect())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: ANN001
        if self._resizing:
            delta = event.scenePos() - self._resize_origin
            width = max(self.MIN_SIZE, self._resize_start_rect.width() + delta.x())
            height = width / self._aspect if self._aspect > 0 else self._resize_start_rect.height()
            if delta.y() > delta.x() / max(self._aspect, 0.001):
                height = max(self.MIN_SIZE, self._resize_start_rect.height() + delta.y())
                width = height * self._aspect
            self.setRect(0.0, 0.0, width, height)
            event.accept()
            self.update()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001
        self._resizing = False
        super().mouseReleaseEvent(event)
        if self._editing_enabled:
            self._commit_callback()

    def paint(self, painter: QPainter, option, widget=None) -> None:  # noqa: ANN001
        del option, widget
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawPixmap(self.rect(), self.pixmap, QRectF(self.pixmap.rect()))
        if self._editing_enabled and self.isSelected() and not self._export_mode:
            painter.setPen(QPen(QColor(90, 190, 255, 235), 2.0, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.rect())
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(90, 190, 255, 235))
            painter.drawRect(self._handle_rect())


class DashboardCanvas(QGraphicsView):
    selection_changed = Signal(object)
    geometry_changed = Signal(object)
    background_geometry_changed = Signal()
    background_image_dropped = Signal(str)

    def __init__(self, parent=None, size: CanvasSize | None = None):
        super().__init__(parent)
        self.canvas_size = size or CanvasSize()
        self.grid_size = 10
        self.grid_enabled = True
        self.snap_enabled = True
        self.background_config = BackgroundConfig()
        self.default_widget_options: dict = {}
        self._background_pixmap = QPixmap()
        self._background_item: BackgroundImageItem | None = None
        self._background_edit_enabled = False
        self._guide_x: float | None = None
        self._guide_y: float | None = None
        self._clipboard_widgets: list[dict] = []
        self._paste_offset = 0
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._scene.setSceneRect(QRectF(0, 0, self.canvas_size.width, self.canvas_size.height))
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setAcceptDrops(True)
        self._scene.selectionChanged.connect(self._emit_selection)
        self._animation_phase = 0.0
        self._animation_clock = time.monotonic()
        self._animation_timer = QTimer(self)
        self._animation_timer.setTimerType(Qt.PreciseTimer)
        self._animation_timer.timeout.connect(self._animate)
        # Editor animation is intentionally faster than the USB cadence.
        # Time-based phase calculation prevents timer jitter from changing the
        # apparent animation speed when the GUI is briefly busy encoding JPEGs.
        self._animation_timer.start(50)  # ~20 FPS editor preview; USB output has its own cadence
        # Export caches: animated dashboards reuse the non-moving scene layer,
        # while completely static dashboards can reuse the already encoded JPEG.
        # This keeps the USB path visually identical but avoids repainting every
        # widget for every animation frame.
        self._static_export_signature = None
        self._static_export_layer: QImage | None = None
        self._static_jpeg_signature = None
        self._static_jpeg_payload: bytes | None = None
        # Aurora export runs on its own cadence. Animated widgets may refresh
        # faster without forcing the expensive gradient background to be rebuilt.
        self._aurora_export_image: QImage | None = None
        self._aurora_export_signature = None
        self._aurora_export_rendered_at = 0.0
        self._aurora_export_interval_s = 1.0 / 3.0

    def set_canvas_size(self, width: int, height: int, *, scale_widgets: bool = True) -> None:
        """Resize the logical dashboard and optionally scale the existing layout."""
        width = max(160, int(width))
        height = max(160, int(height))
        old_w = float(self.canvas_size.width)
        old_h = float(self.canvas_size.height)
        if width == self.canvas_size.width and height == self.canvas_size.height:
            return

        sx = width / old_w if old_w else 1.0
        sy = height / old_h if old_h else 1.0
        if scale_widgets:
            for item in self.widget_items():
                r = item.rect()
                item.setPos(item.x() * sx, item.y() * sy)
                item.setRect(0, 0, max(item.MIN_WIDTH, r.width() * sx), max(item.MIN_HEIGHT, r.height() * sy))

        if self._background_item is not None and scale_widgets:
            r = self._background_item.rect()
            self._background_item.setPos(self._background_item.x() * sx, self._background_item.y() * sy)
            self._background_item.setRect(0, 0, r.width() * sx, r.height() * sy)

        self.canvas_size = CanvasSize(width, height)
        self._scene.setSceneRect(QRectF(0, 0, width, height))
        self._static_export_signature = None
        self._static_export_layer = None
        self._static_jpeg_signature = None
        self._static_jpeg_payload = None
        self._aurora_export_image = None
        self.viewport().update()

    def _animate(self) -> None:
        elapsed = time.monotonic() - self._animation_clock
        self._animation_phase = (elapsed * 2.8) % (math.tau * 10)
        moving = False
        for item in self.widget_items():
            item.set_animation_phase(self._animation_phase)
            moving = moving or item.animation_is_active()
        if self.background_config.mode == "aurora":
            moving = True
            if self.isVisible():
                self.viewport().update()
        # Do not repaint the whole editor while it is hidden in the tray.
        # The time-based phase still advances so USB output keeps moving.
        if moving and self.isVisible():
            self._scene.update()

    def has_active_motion(self) -> bool:
        """Return whether frequent display frames are visually useful."""
        if self.background_config.mode == "aurora":
            return True
        return any(item.animation_is_active() for item in self.widget_items())

    def has_widget_motion(self) -> bool:
        """Return whether any widget itself needs animation frames."""
        return any(item.animation_is_active() for item in self.widget_items())

    def has_aurora_motion(self) -> bool:
        return self.background_config.mode == "aurora"

    def set_aurora_export_interval(self, milliseconds: int) -> None:
        self._aurora_export_interval_s = max(0.08, int(milliseconds) / 1000.0)

    def set_background_config(self, config: BackgroundConfig) -> None:
        self.background_config = BackgroundConfig(
            mode=config.mode,
            color=config.color,
            color2=config.color2,
            image_path=config.image_path,
            image_x=float(config.image_x),
            image_y=float(config.image_y),
            image_width=float(config.image_width),
            image_height=float(config.image_height),
            image_opacity=max(0, min(100, int(config.image_opacity))),
            image_fit=str(config.image_fit or "cover"),
            aurora_color1=str(config.aurora_color1 or "#00e7ff"),
            aurora_color2=str(config.aurora_color2 or "#8d5cff"),
            aurora_color3=str(config.aurora_color3 or "#00ffa8"),
            aurora_speed=max(25, min(300, int(config.aurora_speed))),
            aurora_intensity=max(0, min(100, int(config.aurora_intensity))),
        )
        self._aurora_export_image = None
        self._aurora_export_signature = None
        self._aurora_export_rendered_at = 0.0
        self._background_pixmap = QPixmap()
        if self._background_item is not None:
            self._scene.removeItem(self._background_item)
            self._background_item = None
        if self.background_config.mode == "image" and self.background_config.image_path:
            path = Path(self.background_config.image_path).expanduser()
            if path.is_file():
                self._background_pixmap = QPixmap(str(path))
                if not self._background_pixmap.isNull():
                    self._background_item = BackgroundImageItem(self._background_pixmap, self._background_item_committed)
                    self._scene.addItem(self._background_item)
                    self._background_item.setOpacity(self.background_config.image_opacity / 100.0)
                    self._apply_background_geometry()
                    self._background_item.set_editing_enabled(self._background_edit_enabled)
        self.viewport().update()

    def _default_background_geometry(self, fit: str) -> tuple[float, float, float, float]:
        if self._background_pixmap.isNull():
            return (0.0, 0.0, float(self.canvas_size.width), float(self.canvas_size.height))
        pw = float(self._background_pixmap.width())
        ph = float(self._background_pixmap.height())
        cw = float(self.canvas_size.width)
        ch = float(self.canvas_size.height)
        if fit == "original":
            width, height = pw, ph
        else:
            factor = min(cw / pw, ch / ph) if fit == "contain" else max(cw / pw, ch / ph)
            width, height = pw * factor, ph * factor
        return ((cw - width) / 2.0, (ch - height) / 2.0, width, height)

    def _apply_background_geometry(self) -> None:
        item = self._background_item
        if item is None:
            return
        cfg = self.background_config
        if cfg.image_fit == "manual" and cfg.image_width > 0 and cfg.image_height > 0:
            x, y, width, height = cfg.image_x, cfg.image_y, cfg.image_width, cfg.image_height
        else:
            x, y, width, height = self._default_background_geometry(cfg.image_fit)
            cfg.image_x, cfg.image_y = x, y
            cfg.image_width, cfg.image_height = width, height
        item.setRect(0.0, 0.0, max(1.0, width), max(1.0, height))
        item.setPos(x, y)

    def _background_item_committed(self) -> None:
        item = self._background_item
        if item is None:
            return
        self.background_config.image_x = float(item.x())
        self.background_config.image_y = float(item.y())
        self.background_config.image_width = float(item.rect().width())
        self.background_config.image_height = float(item.rect().height())
        self.background_config.image_fit = "manual"
        self.background_geometry_changed.emit()

    def set_background_edit_enabled(self, enabled: bool) -> None:
        self._background_edit_enabled = bool(enabled)
        if self._background_item is not None:
            self._background_item.set_editing_enabled(enabled)
            if enabled:
                self._scene.clearSelection()
                self._background_item.setSelected(True)
        self.setDragMode(QGraphicsView.NoDrag if enabled else QGraphicsView.RubberBandDrag)
        self.viewport().update()

    def fit_background_image(self, fit: str) -> None:
        if fit not in {"cover", "contain", "original"} or self._background_item is None:
            return
        self.background_config.image_fit = fit
        x, y, width, height = self._default_background_geometry(fit)
        self.background_config.image_x = x
        self.background_config.image_y = y
        self.background_config.image_width = width
        self.background_config.image_height = height
        self._apply_background_geometry()
        self.background_geometry_changed.emit()
        self.viewport().update()

    def center_background_image(self) -> None:
        item = self._background_item
        if item is None:
            return
        x = (self.canvas_size.width - item.rect().width()) / 2.0
        y = (self.canvas_size.height - item.rect().height()) / 2.0
        item.setPos(x, y)
        self._background_item_committed()
        self.viewport().update()

    def set_background_opacity(self, opacity: int) -> None:
        value = max(0, min(100, int(opacity)))
        self.background_config.image_opacity = value
        if self._background_item is not None:
            self._background_item.setOpacity(value / 100.0)
        self.viewport().update()

    def current_background_config(self) -> BackgroundConfig:
        if self._background_item is not None:
            self.background_config.image_x = float(self._background_item.x())
            self.background_config.image_y = float(self._background_item.y())
            self.background_config.image_width = float(self._background_item.rect().width())
            self.background_config.image_height = float(self._background_item.rect().height())
        return BackgroundConfig(**self.background_config.__dict__) if hasattr(self.background_config, "__dict__") else BackgroundConfig(
            mode=self.background_config.mode, color=self.background_config.color, color2=self.background_config.color2,
            image_path=self.background_config.image_path, image_x=self.background_config.image_x, image_y=self.background_config.image_y,
            image_width=self.background_config.image_width, image_height=self.background_config.image_height,
            image_opacity=self.background_config.image_opacity, image_fit=self.background_config.image_fit,
            aurora_color1=self.background_config.aurora_color1, aurora_color2=self.background_config.aurora_color2,
            aurora_color3=self.background_config.aurora_color3, aurora_speed=self.background_config.aurora_speed,
            aurora_intensity=self.background_config.aurora_intensity,
        )

    def apply_theme(self, theme: Theme, *, apply_to_widgets: bool = True) -> None:
        self.default_widget_options = theme.widget_options()
        self.set_background_config(BackgroundConfig(mode="gradient", color=theme.canvas, color2=theme.canvas2))
        if apply_to_widgets:
            options = theme.widget_options()
            for item in self.widget_items():
                semantic_keys = {"text", "image_path", "locked", "metric_key", "gauge_metric", "gauge_min", "gauge_max", "gauge_unit", "gauge_style", "warn", "critical", "chart_style", "history_points", "chart_min", "chart_max"}
                preserved = {key: value for key, value in item.options.items() if key in semantic_keys}
                item.set_style_options({**options, **preserved})

    def _paint_background(self, painter: QPainter, rect: QRectF, *, include_grid: bool) -> None:
        """Paint the dashboard background for both editor and exported frames.

        QGraphicsView.drawBackground() is a *view* hook and is not invoked by
        QGraphicsScene.render().  Keeping the actual painting in this shared
        helper guarantees that the editor preview and the USB/JPEG output use
        exactly the same solid, gradient or image background.
        """
        scene_rect = self.sceneRect()
        config = self.background_config
        if config.mode == "gradient":
            gradient = QLinearGradient(scene_rect.topLeft(), scene_rect.bottomRight())
            gradient.setColorAt(0.0, _color(config.color, "#101217"))
            gradient.setColorAt(1.0, _color(config.color2, "#1b2433"))
            painter.fillRect(rect, gradient)
        elif config.mode == "aurora":
            # A native, animated background rendered by the same path used for
            # editor preview and USB export.  The base gradient stays dark while
            # three soft light fields drift independently across the tall canvas.
            base = QLinearGradient(scene_rect.topLeft(), scene_rect.bottomRight())
            c1 = _color(config.color, "#07101f")
            c2 = _color(config.color2, "#16102f")
            c1.setAlpha(255)
            c2.setAlpha(255)
            base.setColorAt(0.0, c1)
            base.setColorAt(1.0, c2)
            painter.fillRect(rect, base)
            painter.save()
            speed = max(25, min(300, int(config.aurora_speed))) / 100.0
            strength = max(0, min(100, int(config.aurora_intensity))) / 100.0
            phase = self._animation_phase * speed
            lights = (
                (0.18 + 0.22 * math.sin(phase * 0.31), 0.22 + 0.14 * math.cos(phase * 0.23), _color(config.aurora_color1, "#00e7ff"), 0.62 * strength),
                (0.76 + 0.18 * math.cos(phase * 0.27 + 1.1), 0.50 + 0.20 * math.sin(phase * 0.19), _color(config.aurora_color2, "#8d5cff"), 0.56 * strength),
                (0.35 + 0.26 * math.sin(phase * 0.17 + 2.4), 0.80 + 0.10 * math.cos(phase * 0.29), _color(config.aurora_color3, "#00ffa8"), 0.46 * strength),
            )
            radius = max(scene_rect.width(), scene_rect.height()) * 0.34
            for nx, ny, color, alpha in lights:
                center = QPointF(scene_rect.left() + nx * scene_rect.width(), scene_rect.top() + ny * scene_rect.height())
                glow = QRadialGradient(center, radius)
                bright = QColor(color)
                bright.setAlphaF(alpha)
                clear = QColor(color)
                clear.setAlpha(0)
                glow.setColorAt(0.0, bright)
                glow.setColorAt(0.45, QColor(bright.red(), bright.green(), bright.blue(), int(bright.alpha() * 0.45)))
                glow.setColorAt(1.0, clear)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(glow))
                painter.drawEllipse(center, radius, radius)
            painter.restore()
        elif config.mode == "image":
            # The actual image is a scene item so it can be moved/resized with
            # the mouse and the exact same transform reaches USB output.
            painter.fillRect(rect, _color(config.color, "#101217"))
        else:
            painter.fillRect(rect, _color(config.color, "#101217"))

        if not include_grid:
            return
        painter.save()
        painter.setPen(QPen(QColor(255, 255, 255, 18), 0))
        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        x = left
        while x < rect.right():
            painter.drawLine(x, rect.top(), x, rect.bottom())
            x += self.grid_size
        y = top
        while y < rect.bottom():
            painter.drawLine(rect.left(), y, rect.right(), y)
            y += self.grid_size
        painter.restore()

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        self._paint_background(painter, rect, include_grid=self.grid_enabled)

    def snap_widget_position(self, item: WidgetItem, proposed: QPointF) -> QPointF:
        """Magnetically snap widget edges/centres to canvas and nearby widgets."""
        threshold = 6.0
        w, h = item.rect().width(), item.rect().height()
        x, y = proposed.x(), proposed.y()
        x_candidates = [0.0, self.sceneRect().width() / 2.0, self.sceneRect().width()]
        y_candidates = [0.0, self.sceneRect().height() / 2.0, self.sceneRect().height()]
        for other in self.widget_items():
            if other is item:
                continue
            x_candidates += [other.x(), other.x() + other.rect().width()/2.0, other.x() + other.rect().width()]
            y_candidates += [other.y(), other.y() + other.rect().height()/2.0, other.y() + other.rect().height()]
        points_x = [(x, 0.0), (x + w/2.0, w/2.0), (x + w, w)]
        points_y = [(y, 0.0), (y + h/2.0, h/2.0), (y + h, h)]
        best_x = min(((abs(px-c), c-offset) for px, offset in points_x for c in x_candidates), default=(999, x))
        best_y = min(((abs(py-c), c-offset) for py, offset in points_y for c in y_candidates), default=(999, y))
        self._guide_x = None
        self._guide_y = None
        if best_x[0] <= threshold:
            x = best_x[1]
            # find actual guide coordinate from snapped edge/centre
            for px, off in points_x:
                for c in x_candidates:
                    if abs(px-c) == best_x[0]:
                        self._guide_x = c
                        break
                if self._guide_x is not None:
                    break
        if best_y[0] <= threshold:
            y = best_y[1]
            for py, off in points_y:
                for c in y_candidates:
                    if abs(py-c) == best_y[0]:
                        self._guide_y = c
                        break
                if self._guide_y is not None:
                    break
        self.viewport().update()
        return QPointF(x, y)

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        super().drawForeground(painter, rect)
        if self._guide_x is None and self._guide_y is None:
            return
        painter.save()
        painter.setPen(QPen(QColor(83, 179, 255, 220), 1, Qt.DashLine))
        if self._guide_x is not None:
            painter.drawLine(QPointF(self._guide_x, self.sceneRect().top()), QPointF(self._guide_x, self.sceneRect().bottom()))
        if self._guide_y is not None:
            painter.drawLine(QPointF(self.sceneRect().left(), self._guide_y), QPointF(self.sceneRect().right(), self._guide_y))
        painter.restore()

    def clear_guides(self) -> None:
        self._guide_x = None
        self._guide_y = None
        self.viewport().update()

    def copy_selected_widgets(self) -> bool:
        selected = self.selected_widgets()
        if not selected:
            return False
        self._clipboard_widgets = [
            {"kind": i.kind, "label": i.label, "x": i.x(), "y": i.y(),
             "width": i.rect().width(), "height": i.rect().height(), "options": dict(i.options), "z": i.zValue()}
            for i in selected
        ]
        self._paste_offset = 0
        return True

    def paste_widgets(self) -> list[WidgetItem]:
        if not self._clipboard_widgets:
            return []
        self._paste_offset += 20
        self._scene.clearSelection()
        created = []
        for data in self._clipboard_widgets:
            pos = QPointF(data["x"] + self._paste_offset, data["y"] + self._paste_offset)
            item = self.add_widget(data["kind"], data["label"], pos, options=data["options"], width=int(data["width"]), height=int(data["height"]))
            item.setZValue(float(data["z"]) + 0.01)
            item.setSelected(True)
            created.append(item)
        return created

    def set_grid_enabled(self, enabled: bool) -> None:
        self.grid_enabled = enabled
        self.viewport().update()

    def set_snap_enabled(self, enabled: bool) -> None:
        self.snap_enabled = enabled
        for item in self.widget_items():
            item.snap_enabled = enabled

    def add_widget(
        self,
        kind: str,
        label: str,
        position: QPointF | None = None,
        *,
        options: dict | None = None,
        width: int = 400,
        height: int = 180,
    ) -> WidgetItem:
        if position is None:
            offset = 20 + (len(self.widget_items()) * 20) % 200
            position = QPointF(offset, offset)
        preset = widget_type(kind)
        preset_options = dict(preset.options or {}) if preset is not None else {}
        base_options = dict(self.default_widget_options if options is None else options)
        resolved_options = {**base_options, **preset_options}
        if preset is not None and width == 400 and height == 180:
            width, height = preset.width, preset.height
        item = WidgetItem(kind, label, position.x(), position.y(), width, height, options=resolved_options)
        item.snap_enabled = self.snap_enabled
        self._scene.addItem(item)
        self._scene.clearSelection()
        item.setSelected(True)
        item.setPos(item.pos())  # clamp initial drop to canvas
        return item

    def widget_items(self) -> list[WidgetItem]:
        return [item for item in self._scene.items() if isinstance(item, WidgetItem)]

    def selected_widgets(self) -> list[WidgetItem]:
        return [item for item in self._scene.selectedItems() if isinstance(item, WidgetItem)]

    def clear_widgets(self) -> None:
        for item in self.widget_items():
            self._scene.removeItem(item)

    def set_snapshot(self, snapshot: dict) -> None:
        for item in self.widget_items():
            item.set_snapshot(snapshot)


    @staticmethod
    def _item_export_signature(item: WidgetItem) -> tuple:
        """Cheap fingerprint for cache invalidation of a widget's visible state."""
        r = item.rect()
        return (
            id(item), round(item.x(), 3), round(item.y(), 3),
            round(r.width(), 3), round(r.height(), 3), round(item.zValue(), 3),
            item.label, repr(sorted(item.options.items())), id(item.snapshot),
        )

    def _background_export_signature(self) -> tuple:
        cfg = self.background_config
        bg = self._background_item
        bg_geometry = None
        if bg is not None:
            r = bg.rect()
            bg_geometry = (round(bg.x(), 3), round(bg.y(), 3), round(r.width(), 3), round(r.height(), 3))
        return (
            cfg.mode, cfg.color, cfg.color2, cfg.image_path, cfg.image_opacity, cfg.image_fit,
            cfg.aurora_color1, cfg.aurora_color2, cfg.aurora_color3,
            cfg.aurora_speed, cfg.aurora_intensity, bg_geometry,
        )

    def _static_scene_signature(self, static_widgets: list[WidgetItem]) -> tuple:
        return (
            self._background_export_signature(),
            tuple(self._item_export_signature(item) for item in static_widgets),
        )

    def _render_scene_subset(self, painter: QPainter, visible_widgets: set[WidgetItem], *, show_background_item: bool) -> None:
        """Render a widget subset without changing editor selection or focus.

        Hiding a selected QGraphicsItem implicitly deselects it. Animated export
        used to hide/show items for every frame, which immediately cleared the
        user's selection after enabling effects such as Breathe. Temporary
        opacity keeps items in the scene and preserves selection state.
        """
        widgets = self.widget_items()
        prior_opacity = [(item, item.opacity()) for item in widgets]
        bg_opacity = self._background_item.opacity() if self._background_item is not None else None
        try:
            for item in widgets:
                item.setOpacity(1.0 if item in visible_widgets else 0.0)
            if self._background_item is not None:
                self._background_item.setOpacity(bg_opacity if show_background_item else 0.0)
            self._scene.render(
                painter,
                QRectF(0, 0, self.canvas_size.width, self.canvas_size.height),
                self._scene.sceneRect(),
            )
        finally:
            for item, opacity in prior_opacity:
                item.setOpacity(opacity)
            if self._background_item is not None and bg_opacity is not None:
                self._background_item.setOpacity(bg_opacity)

    def render_jpeg(self, quality: int = 84) -> bytes:
        """Render the clean dashboard with a cached static layer.

        The final JPEG follows the current logical canvas size. Non-moving
        widgets no longer need to be
        repainted for every animation frame. Completely static dashboards also
        reuse the encoded JPEG until their visible state changes.
        """
        width = int(self.canvas_size.width)
        height = int(self.canvas_size.height)
        quality = max(50, min(95, int(quality)))
        widgets = self.widget_items()
        animated = [item for item in widgets if item.animation_is_active()]
        static_widgets = [item for item in widgets if item not in animated]
        moving_background = self.background_config.mode == "aurora"
        motion = moving_background or bool(animated)
        signature = self._static_scene_signature(static_widgets)

        # Static dashboards: if neither sensor snapshot nor editor state changed,
        # return the exact previous JPEG without repainting or re-encoding.
        full_signature = (signature, tuple(self._item_export_signature(item) for item in animated), quality)
        if not motion and self._static_jpeg_signature == full_signature and self._static_jpeg_payload:
            return self._static_jpeg_payload

        grid_was_enabled = self.grid_enabled
        self.grid_enabled = False
        for item in widgets:
            item.set_export_mode(True)
        if self._background_item is not None:
            self._background_item.set_export_mode(True)
        try:
            # Build/reuse the non-moving scene layer. For Aurora the layer is
            # transparent, because the animated background is painted beneath it
            # on each output frame. Otherwise it already contains the background.
            if self._static_export_signature != signature or self._static_export_layer is None:
                if moving_background:
                    layer = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
                    layer.fill(Qt.transparent)
                else:
                    layer = QImage(width, height, QImage.Format_RGB32)
                    layer.fill(Qt.black)
                painter = QPainter(layer)
                painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
                if not moving_background:
                    self._paint_background(painter, QRectF(0, 0, width, height), include_grid=False)
                self._render_scene_subset(
                    painter, set(static_widgets),
                    show_background_item=(self.background_config.mode == "image" and not moving_background),
                )
                painter.end()
                self._static_export_layer = layer
                self._static_export_signature = signature
                self._static_jpeg_signature = None
                self._static_jpeg_payload = None

            if moving_background:
                image = QImage(width, height, QImage.Format_RGB32)
                image.fill(Qt.black)
                painter = QPainter(image)
                painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)

                # Aurora is intentionally soft/blurred, so calculating its radial
                # gradients at quarter resolution preserves the look while
                # avoiding nearly a million full-resolution gradient pixels per
                # output frame. Qt then scales that small raster once.
                aurora_w = max(96, width // 4)
                aurora_h = max(384, height // 4)
                now = time.monotonic()
                aurora_signature = (
                    aurora_w, aurora_h,
                    self.background_config.aurora_color1,
                    self.background_config.aurora_color2,
                    self.background_config.aurora_color3,
                    int(self.background_config.aurora_speed),
                    int(self.background_config.aurora_intensity),
                )
                aurora_due = (
                    self._aurora_export_image is None
                    or self._aurora_export_signature != aurora_signature
                    or now - self._aurora_export_rendered_at >= self._aurora_export_interval_s
                )
                if aurora_due:
                    aurora = QImage(aurora_w, aurora_h, QImage.Format_RGB32)
                    aurora.fill(Qt.black)
                    aurora_painter = QPainter(aurora)
                    aurora_painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
                    self._paint_background(
                        aurora_painter,
                        QRectF(0, 0, aurora_w, aurora_h),
                        include_grid=False,
                    )
                    aurora_painter.end()
                    self._aurora_export_image = aurora
                    self._aurora_export_signature = aurora_signature
                    self._aurora_export_rendered_at = now
                if self._aurora_export_image is not None:
                    painter.drawImage(QRectF(0, 0, width, height), self._aurora_export_image)

                if self._static_export_layer is not None:
                    painter.drawImage(0, 0, self._static_export_layer)
            else:
                image = self._static_export_layer.copy() if self._static_export_layer is not None else QImage(width, height, QImage.Format_RGB32)
                painter = QPainter(image)
                painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)

            if animated:
                self._render_scene_subset(painter, set(animated), show_background_item=False)
            painter.end()
        finally:
            self.grid_enabled = grid_was_enabled
            for item in widgets:
                item.set_export_mode(False)
            if self._background_item is not None:
                self._background_item.set_export_mode(False)

        buffer = QBuffer()
        if not buffer.open(QIODevice.WriteOnly):
            raise RuntimeError("JPEG-Puffer konnte nicht geöffnet werden")
        ok = image.save(buffer, "JPEG", quality)
        payload = bytes(buffer.data())
        buffer.close()
        if not ok or not payload:
            raise RuntimeError("Dashboard konnte nicht als JPEG gerendert werden")
        if not motion:
            self._static_jpeg_signature = full_signature
            self._static_jpeg_payload = payload
        return payload

    def dragEnterEvent(self, event) -> None:  # noqa: ANN001
        mime = event.mimeData()
        if mime.hasFormat("application/x-owndash-widget"):
            event.acceptProposedAction()
            return
        if mime.hasUrls() and any(
            url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
            for url in mime.urls()
        ):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # noqa: ANN001
        mime = event.mimeData()
        if mime.hasFormat("application/x-owndash-widget") or mime.hasUrls():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: ANN001
        mime = event.mimeData()
        if mime.hasFormat("application/x-owndash-widget"):
            payload = bytes(mime.data("application/x-owndash-widget")).decode("utf-8", errors="replace")
            if "\t" not in payload:
                event.ignore()
                return
            kind, label = payload.split("\t", 1)
            scene_pos = self.mapToScene(event.position().toPoint())
            self.add_widget(kind, label, scene_pos)
            self.geometry_changed.emit(self.selected_widget())
            event.acceptProposedAction()
            return
        if mime.hasUrls():
            for url in mime.urls():
                if not url.isLocalFile():
                    continue
                path = Path(url.toLocalFile())
                if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
                    self.background_image_dropped.emit(str(path))
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001
        super().mouseReleaseEvent(event)
        self.clear_guides()
        item = self.selected_widget()
        if item is not None:
            self.geometry_changed.emit(item)

    def selected_widget(self) -> WidgetItem | None:
        items = self.selected_widgets()
        return items[0] if len(items) == 1 else None

    def keyPressEvent(self, event) -> None:  # noqa: ANN001
        """Arrow keys nudge selected widgets; Shift uses the configured grid step."""
        if event.matches(QKeySequence.Copy):
            if self.copy_selected_widgets():
                event.accept()
                return
        if event.matches(QKeySequence.Paste):
            created = self.paste_widgets()
            if created:
                self.geometry_changed.emit(created[0] if len(created) == 1 else None)
                event.accept()
                return
        delta = {
            Qt.Key_Left: (-1.0, 0.0),
            Qt.Key_Right: (1.0, 0.0),
            Qt.Key_Up: (0.0, -1.0),
            Qt.Key_Down: (0.0, 1.0),
        }.get(event.key())
        selected = self.selected_widgets()
        if delta is not None and selected:
            step = float(self.grid_size if event.modifiers() & Qt.ShiftModifier else 1.0)
            for item in selected:
                item.nudge(delta[0] * step, delta[1] * step)
            self.geometry_changed.emit(self.selected_widget())
            event.accept()
            return
        super().keyPressEvent(event)

    def _emit_selection(self) -> None:
        selected = self.selected_widgets()
        self.selection_changed.emit(selected[0] if len(selected) == 1 else selected)
