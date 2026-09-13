from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def _set_group(palette: QPalette, group: QPalette.ColorGroup, dark: bool) -> None:
    if dark:
        window, base, alternate = QColor("#24272d"), QColor("#171a1f"), QColor("#20242a")
        text, disabled = QColor("#eef1f5"), QColor("#7d838c")
        button, mid, light = QColor("#30343b"), QColor("#4b515b"), QColor("#59616c")
        highlight, highlighted = QColor("#3daee9"), QColor("#ffffff")
        tooltip = QColor("#20242a")
    else:
        window, base, alternate = QColor("#f1f3f5"), QColor("#ffffff"), QColor("#e9edf1")
        text, disabled = QColor("#20242a"), QColor("#8b929b")
        button, mid, light = QColor("#e3e7eb"), QColor("#aeb5bd"), QColor("#ffffff")
        highlight, highlighted = QColor("#3daee9"), QColor("#ffffff")
        tooltip = QColor("#ffffff")

    roles = {
        QPalette.Window: window, QPalette.WindowText: text, QPalette.Base: base,
        QPalette.AlternateBase: alternate, QPalette.ToolTipBase: tooltip,
        QPalette.ToolTipText: text, QPalette.Text: text, QPalette.Button: button,
        QPalette.ButtonText: text, QPalette.BrightText: highlighted,
        QPalette.Highlight: highlight, QPalette.HighlightedText: highlighted,
        QPalette.Mid: mid, QPalette.Light: light, QPalette.PlaceholderText: disabled,
    }
    for role, color in roles.items():
        value = color
        if group == QPalette.Disabled:
            if role in {QPalette.WindowText, QPalette.Text, QPalette.ButtonText, QPalette.PlaceholderText}:
                value = disabled
            elif role == QPalette.Base:
                value = QColor("#e5e9ed") if not dark else QColor("#22262c")
            elif role == QPalette.Button:
                value = QColor("#e1e5e9") if not dark else QColor("#2a2e34")
        palette.setColor(group, role, value)


def make_palette(mode: str, system_palette: QPalette) -> QPalette:
    if mode == "system":
        return QPalette(system_palette)
    palette = QPalette()
    dark = mode == "dark"
    for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
        _set_group(palette, group, dark)
    return palette


def apply_appearance(mode: str, system_palette: QPalette) -> None:
    app = QApplication.instance()
    if app is not None:
        app.setPalette(make_palette(mode, system_palette))
