from __future__ import annotations

from owndash.core.models import BackgroundConfig, Profile, WidgetConfig


def _gauge(kind: str, title: str, x: int, y: int, metric: str, unit: str, minimum: int, maximum: int, warn: int, critical: int) -> WidgetConfig:
    return WidgetConfig(
        kind=kind, x=x, y=y, width=210, height=260, title=title,
        options={"metric_key": {"cpu": "cpu.usage", "gpu": "gpu.usage", "temperature": "temperature.value", "power": "power.total_w", "memory": "memory.percent"}.get(metric, "cpu.usage"), "gauge_metric": metric, "gauge_unit": unit, "gauge_min": minimum, "gauge_max": maximum, "gauge_style": "arc", "warn": warn, "critical": critical},
    )


def template_names() -> tuple[str, ...]:
    return ("Gaming Gauges", "System Compact", "Telemetry Lab", "Racing Stack", "OLED Essentials", "Minimal")


def make_template(name: str) -> Profile:
    if name == "Gaming Gauges":
        return Profile(
            name=name, theme="Neon Cyan", background=BackgroundConfig(mode="gradient", color="#080B12", color2="#11182A"),
            widgets=[
                _gauge("gauge_cpu", "CPU", 20, 40, "cpu", "%", 0, 100, 75, 90),
                _gauge("gauge_gpu", "GPU", 250, 40, "gpu", "%", 0, 100, 75, 90),
                _gauge("gauge_temp", "Temperatur", 20, 330, "temperature", "°C", 20, 100, 70, 85),
                _gauge("gauge_power", "Leistung", 250, 330, "power", "W", 0, 200, 140, 180),
                WidgetConfig("memory", 20, 630, 440, 160, "RAM"),
                WidgetConfig("network", 20, 810, 440, 160, "Netzwerk"),
                WidgetConfig("clock", 20, 990, 440, 160, "Uhr"),
            ],
        )
    if name == "Telemetry Lab":
        return Profile(
            name=name, theme="Electric Blue", background=BackgroundConfig(mode="gradient", color="#020713", color2="#0a1b34"),
            widgets=[
                WidgetConfig("chart", 20, 40, 440, 260, "CPU Verlauf", options={"metric_key": "cpu.usage", "chart_style": "area", "history_points": 90, "gauge_unit": "%"}),
                WidgetConfig("chart", 20, 320, 440, 260, "GPU Verlauf", options={"metric_key": "gpu.usage", "chart_style": "line", "history_points": 90, "gauge_unit": "%"}),
                WidgetConfig("sparkline", 20, 600, 440, 170, "Temperatur", options={"metric_key": "temperature.value", "chart_style": "area", "history_points": 60, "gauge_unit": "°C"}),
                _gauge("gauge_power", "Leistung", 20, 790, "power", "W", 0, 350, 220, 300),
                WidgetConfig("network", 20, 1090, 440, 160, "Netzwerk"),
                WidgetConfig("clock", 20, 1270, 440, 150, "Uhr"),
            ],
        )
    if name == "Racing Stack":
        cpu = _gauge("gauge_cpu", "CPU", 20, 40, "cpu", "%", 0, 100, 75, 90)
        gpu = _gauge("gauge_gpu", "GPU", 250, 40, "gpu", "%", 0, 100, 75, 90)
        temp = _gauge("gauge_temp", "TEMP", 20, 340, "temperature", "°C", 20, 100, 70, 85)
        for widget in (cpu, gpu, temp):
            widget.options["gauge_style"] = "semi"
        return Profile(
            name=name, theme="Racing Red", background=BackgroundConfig(mode="solid", color="#050505"),
            widgets=[cpu, gpu, temp, WidgetConfig("chart", 20, 650, 440, 220, "GPU Verlauf", options={"metric_key": "gpu.usage", "chart_style": "line", "history_points": 60, "gauge_unit": "%"}), WidgetConfig("clock", 20, 890, 440, 150, "Uhr")],
        )
    if name == "OLED Essentials":
        ring = _gauge("gauge_cpu", "CPU", 90, 80, "cpu", "%", 0, 100, 75, 90)
        ring.width = 300
        ring.options["gauge_style"] = "ring"
        return Profile(
            name=name, theme="OLED Black", background=BackgroundConfig(mode="solid", color="#000000"),
            widgets=[ring, WidgetConfig("gpu", 40, 420, 400, 160, "GPU"), WidgetConfig("memory", 40, 600, 400, 150, "RAM"), WidgetConfig("temperature", 40, 770, 400, 150, "Temperatur"), WidgetConfig("clock", 40, 940, 400, 160, "Uhr")],
        )
    if name == "System Compact":
        return Profile(
            name=name, theme="Midnight", widgets=[
                WidgetConfig("cpu", 20, 30, 440, 170, "CPU"),
                WidgetConfig("gpu", 20, 220, 440, 170, "GPU"),
                WidgetConfig("memory", 20, 410, 440, 150, "Arbeitsspeicher"),
                WidgetConfig("storage", 20, 580, 440, 150, "Speicher"),
                WidgetConfig("network", 20, 750, 440, 150, "Netzwerk"),
                WidgetConfig("temperature", 20, 920, 440, 150, "Temperatur"),
                WidgetConfig("power", 20, 1090, 440, 150, "Leistung"),
                WidgetConfig("clock", 20, 1260, 440, 150, "Uhr"),
            ],
        )
    return Profile(
        name="Minimal", theme="Midnight", background=BackgroundConfig(mode="solid", color="#090B10"),
        widgets=[
            WidgetConfig("clock", 40, 100, 400, 180, "Uhr"),
            _gauge("gauge_cpu", "CPU", 40, 340, "cpu", "%", 0, 100, 75, 90),
            WidgetConfig("network", 40, 650, 400, 160, "Netzwerk"),
        ],
    )
