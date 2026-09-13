from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    name: str
    canvas: str
    canvas2: str
    widget: str
    border: str
    accent: str
    title: str
    value: str
    bar_track: str
    opacity: int = 94
    radius: int = 14
    glow: int = 0
    animation: str = "none"

    def widget_options(self) -> dict[str, object]:
        return {
            "background": self.widget,
            "border": self.border,
            "accent": self.accent,
            "title_color": self.title,
            "value_color": self.value,
            "bar_track": self.bar_track,
            "opacity": self.opacity,
            "radius": self.radius,
            "title_size": 10,
            "value_size": 18,
            "glow": self.glow,
            "animation": self.animation,
        }


DEFAULT_THEME_NAME = "Midnight"

# Built-in themes deliberately use only internal colour definitions.  They do
# not ship third-party artwork and therefore remain portable and deterministic.
_BUILTINS = {
    "Midnight": Theme("Midnight", "#0a0c11", "#182132", "#1c222c", "#344050", "#53b3ff", "#9da9ba", "#eef2f8", "#373f4c"),
    "Neon Cyan": Theme("Neon Cyan", "#05080d", "#0b1b26", "#0b1720", "#145c70", "#28e4ff", "#79d8e7", "#f5fdff", "#17333c", glow=28),
    "Crimson": Theme("Crimson", "#0e080b", "#261017", "#211218", "#6b2338", "#ff496f", "#d19aaa", "#fff2f5", "#44202b", glow=18),
    "Matrix": Theme("Matrix", "#030805", "#07160c", "#07120b", "#175d31", "#47ff7a", "#83ca96", "#eaffef", "#173621", radius=10, glow=14),
    "Cyber Purple": Theme("Cyber Purple", "#080511", "#1a0d2b", "#160d24", "#54237c", "#c86cff", "#c5a1dc", "#fff7ff", "#321747", glow=30),
    "Electric Blue": Theme("Electric Blue", "#030814", "#081b38", "#0a1730", "#1f5fa8", "#2f8cff", "#83b8ef", "#f4f9ff", "#17365b", glow=24),
    "OLED Black": Theme("OLED Black", "#000000", "#050505", "#080808", "#242424", "#f2f2f2", "#969696", "#ffffff", "#1a1a1a", opacity=97, radius=10),
    "Amber Terminal": Theme("Amber Terminal", "#080500", "#1a1002", "#181006", "#725014", "#ffb52e", "#d0a85a", "#fff2cf", "#3b2a0c", radius=8, glow=12),
    "Vaporwave": Theme("Vaporwave", "#10091e", "#281148", "#22143a", "#7c3fb2", "#ff66d9", "#cda7e5", "#fff4fd", "#49255f", radius=20, glow=26),
    "Arctic": Theme("Arctic", "#071119", "#102938", "#10212b", "#356273", "#7de6ff", "#a5cad6", "#f7fdff", "#23414b", glow=12),
    "Toxic Lime": Theme("Toxic Lime", "#070a03", "#172205", "#131c08", "#4c6818", "#b6ff36", "#b2cb83", "#f8ffe9", "#30420f", glow=22),
    "Racing Red": Theme("Racing Red", "#090909", "#211010", "#1b1111", "#693030", "#ff3434", "#c99a9a", "#fff7f7", "#3f2020", radius=6, glow=18),
    "Industrial": Theme("Industrial", "#0d0f10", "#1c2022", "#202426", "#4b5358", "#ffb000", "#aeb5b8", "#f6f7f7", "#3b4144", radius=4),
    "Ice White": Theme("Ice White", "#dfeaf0", "#b9d0dc", "#f7fbfd", "#8ba7b4", "#147fa8", "#486775", "#10242d", "#b9ced7", opacity=96, radius=16),
    "Synthwave Grid": Theme("Synthwave Grid", "#09031a", "#2a0a4a", "#160c2b", "#7436a8", "#00f5ff", "#d5a4ff", "#fff5ff", "#392052", glow=32),
    "Carbon": Theme("Carbon", "#090a0b", "#151719", "#17191b", "#3a3f44", "#b8c0c7", "#8e969d", "#f7f8f9", "#2b2e31", opacity=97, radius=8),
    "Aurora": Theme("Aurora", "#031217", "#10243d", "#0a1d24", "#1f6670", "#58ffd2", "#87d7d0", "#f2fffd", "#16444b", glow=24),
    "Sunset Drive": Theme("Sunset Drive", "#160712", "#3a1228", "#28101f", "#843d55", "#ff8a3d", "#e8a1b5", "#fff5ef", "#4b2530", glow=20),
}


class ThemeManager:
    @staticmethod
    def names() -> tuple[str, ...]:
        return tuple(_BUILTINS)

    @staticmethod
    def get(name: str) -> Theme:
        return _BUILTINS.get(name, _BUILTINS[DEFAULT_THEME_NAME])
