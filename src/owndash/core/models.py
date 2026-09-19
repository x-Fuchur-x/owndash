from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Any


@dataclass(slots=True)
class BackgroundConfig:
    mode: str = "solid"  # solid | gradient | image | aurora
    color: str = "#101217"
    color2: str = "#1b2433"
    image_path: str = ""
    image_x: float = 0.0
    image_y: float = 0.0
    image_width: float = 0.0
    image_height: float = 0.0
    image_opacity: int = 100
    image_fit: str = "cover"  # cover | contain | original | manual
    aurora_color1: str = "#00e7ff"
    aurora_color2: str = "#8d5cff"
    aurora_color3: str = "#00ffa8"
    aurora_speed: int = 100
    aurora_intensity: int = 70

    @classmethod
    def from_raw(cls, raw: object, legacy_color: str | None = None) -> "BackgroundConfig":
        if isinstance(raw, dict):
            allowed = {
                key: raw[key]
                for key in (
                    "mode", "color", "color2", "image_path",
                    "image_x", "image_y", "image_width", "image_height",
                    "image_opacity", "image_fit",
                    "aurora_color1", "aurora_color2", "aurora_color3",
                    "aurora_speed", "aurora_intensity",
                )
                if key in raw
            }
            return cls(**allowed)
        return cls(color=legacy_color or cls().color)


@dataclass(slots=True)
class WidgetConfig:
    kind: str
    x: int
    y: int
    width: int
    height: int
    title: str = ""
    enabled: bool = True
    z: float = 0.0
    options: dict[str, Any] = field(default_factory=dict)

    def normalized(self, canvas_width: int, canvas_height: int) -> "WidgetConfig":
        width = max(40, min(int(self.width), canvas_width))
        height = max(40, min(int(self.height), canvas_height))
        x = max(0, min(int(self.x), canvas_width - width))
        y = max(0, min(int(self.y), canvas_height - height))
        return WidgetConfig(
            kind=str(self.kind),
            x=x,
            y=y,
            width=width,
            height=height,
            title=str(self.title),
            enabled=bool(self.enabled),
            z=float(self.z),
            options=dict(self.options or {}),
        )


@dataclass(slots=True)
class DashboardPage:
    name: str = "Dashboard"
    theme: str = "Midnight"
    background: BackgroundConfig = field(default_factory=BackgroundConfig)
    widgets: list[WidgetConfig] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: object) -> "DashboardPage":
        if not isinstance(raw, dict):
            return cls()
        widgets_raw = raw.get("widgets", [])
        widgets = [
            WidgetConfig(**item)
            for item in widgets_raw
            if isinstance(item, dict)
        ] if isinstance(widgets_raw, list) else []
        background = BackgroundConfig.from_raw(raw.get("background"))
        return cls(
            name=str(raw.get("name", "Dashboard")),
            theme=str(raw.get("theme", "Midnight")),
            background=background,
            widgets=widgets,
        )


@dataclass(slots=True)
class Profile:
    name: str = "Default"
    canvas_width: int = 480
    canvas_height: int = 1920
    rotation: int = 270
    theme: str = "Midnight"
    background: BackgroundConfig = field(default_factory=BackgroundConfig)
    widgets: list[WidgetConfig] = field(default_factory=list)
    pages: list[DashboardPage] = field(default_factory=list)
    active_page: int = 0
    auto_cycle: bool = False
    auto_cycle_seconds: int = 10
    display_backend: str = "aic_usb"
    display_device_id: str = "auto"
    layout_bounds: list[float] | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "Profile":
        raw = json.loads(text)
        if not isinstance(raw, dict):
            raise ValueError("Profile root must be a JSON object")

        widgets_raw = raw.pop("widgets", [])
        if not isinstance(widgets_raw, list):
            raise ValueError("Profile widgets must be a list")
        widgets = [WidgetConfig(**item) for item in widgets_raw if isinstance(item, dict)]

        pages_raw = raw.pop("pages", [])
        if pages_raw is None:
            pages_raw = []
        if not isinstance(pages_raw, list):
            raise ValueError("Profile pages must be a list")
        pages = [DashboardPage.from_raw(item) for item in pages_raw if isinstance(item, dict)]

        legacy_background = raw.pop("background", None)
        background = BackgroundConfig.from_raw(
            legacy_background,
            legacy_color=legacy_background if isinstance(legacy_background, str) else None,
        )

        allowed = {
            "name", "canvas_width", "canvas_height", "rotation", "theme",
            "active_page", "auto_cycle", "auto_cycle_seconds",
            "display_backend", "display_device_id", "layout_bounds",
        }
        profile_args = {key: value for key, value in raw.items() if key in allowed}
        return cls(background=background, widgets=widgets, pages=pages, **profile_args)
