from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    key: str
    label: str
    unit: str
    minimum: float
    maximum: float


METRICS: tuple[MetricDefinition, ...] = (
    MetricDefinition("cpu.usage", "CPU · Auslastung", "%", 0, 100),
    MetricDefinition("gpu.usage", "GPU · Auslastung", "%", 0, 100),
    MetricDefinition("gpu.temperature", "GPU · Temperatur", "°C", 20, 110),
    MetricDefinition("gpu.vram_percent", "GPU · VRAM-Auslastung", "%", 0, 100),
    MetricDefinition("gpu.vram_used_gib", "GPU · VRAM belegt", "GiB", 0, 24),
    MetricDefinition("gpu.vram_total_gib", "GPU · VRAM gesamt", "GiB", 0, 24),
    MetricDefinition("memory.percent", "RAM · Auslastung", "%", 0, 100),
    MetricDefinition("storage.percent", "Speicher · Auslastung", "%", 0, 100),
    MetricDefinition("temperature.value", "CPU · Temperatur", "°C", 20, 110),
    MetricDefinition("power.cpu_w", "CPU · Leistung", "W", 0, 200),
    MetricDefinition("power.gpu_w", "GPU · Leistung", "W", 0, 300),
    MetricDefinition("power.total_w", "CPU + GPU · Leistung", "W", 0, 450),
    MetricDefinition("network.down_bps", "Netzwerk · Download", "B/s", 0, 125_000_000),
    MetricDefinition("network.up_bps", "Netzwerk · Upload", "B/s", 0, 125_000_000),
)


def metric_definition(key: str) -> MetricDefinition | None:
    return next((item for item in METRICS if item.key == key), None)


def read_metric(snapshot: dict[str, Any], key: str) -> float | None:
    current: Any = snapshot
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    if isinstance(current, bool) or not isinstance(current, (int, float)):
        return None
    return float(current)
