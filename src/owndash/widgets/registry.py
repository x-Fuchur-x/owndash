from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WidgetType:
    key: str
    label: str
    width: int = 400
    height: int = 180
    options: dict | None = None


DEFAULT_WIDGETS = (
    WidgetType("cpu", "CPU"),
    WidgetType("gpu", "GPU"),
    WidgetType("memory", "Arbeitsspeicher"),
    WidgetType("storage", "Speicher"),
    WidgetType("network", "Netzwerk"),
    WidgetType("temperature", "Temperatur"),
    WidgetType("power", "Leistung"),
    WidgetType("clock", "Uhr"),
    WidgetType("gauge_cpu", "Tacho · CPU", 300, 300, {"metric_key": "cpu.usage", "gauge_metric": "cpu", "gauge_min": 0, "gauge_max": 100, "gauge_unit": "%", "gauge_style": "arc", "warn": 75, "critical": 90}),
    WidgetType("gauge_gpu", "Tacho · GPU", 300, 300, {"metric_key": "gpu.usage", "gauge_metric": "gpu", "gauge_min": 0, "gauge_max": 100, "gauge_unit": "%", "gauge_style": "arc", "warn": 75, "critical": 90}),
    WidgetType("gauge_temp", "Tacho · Temperatur", 300, 300, {"metric_key": "temperature.value", "gauge_metric": "temperature", "gauge_min": 20, "gauge_max": 100, "gauge_unit": "°C", "gauge_style": "arc", "warn": 70, "critical": 85}),
    WidgetType("gauge_power", "Tacho · Leistung", 300, 300, {"metric_key": "power.total_w", "gauge_metric": "power", "gauge_min": 0, "gauge_max": 200, "gauge_unit": "W", "gauge_style": "arc", "warn": 140, "critical": 180}),
    WidgetType("chart", "Diagramm", 420, 220, {"metric_key": "cpu.usage", "chart_style": "line", "history_points": 60, "gauge_unit": "%"}),
    WidgetType("sparkline", "Sparkline", 420, 140, {"metric_key": "gpu.usage", "chart_style": "area", "history_points": 60, "gauge_unit": "%"}),
    WidgetType("text", "Text"),
    WidgetType("image", "Bild"),
)


def widget_type(key: str) -> WidgetType | None:
    return next((item for item in DEFAULT_WIDGETS if item.key == key), None)
