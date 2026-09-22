from pathlib import Path

path = Path("src/owndash/gui/system_state_frame.py")
text = path.read_text(encoding="utf-8")

replacements = {
    "diameter = width * 0.72": "diameter = width * 0.68",
    "icon_side = width * 0.20": "icon_side = width * 0.18",
    "wordmark_rect=QRectF(width * 0.20, height * 0.285, width * 0.60, height * 0.047),":
        "wordmark_rect=QRectF(width * 0.23, height * 0.286, width * 0.54, height * 0.045),",
    "wordmark_font_px=width * 0.102,": "wordmark_font_px=width * 0.090,",
    "status_rect=QRectF(width * 0.15, height * 0.525, width * 0.70, height * 0.052),":
        "status_rect=QRectF(width * 0.18, height * 0.527, width * 0.64, height * 0.050),",
    "status_font_px=width * 0.112,": "status_font_px=width * 0.092,",
    "(-0.20, palette.cyan, 54),": "(-0.20, palette.cyan, 38),",
    "(0.20, palette.magenta, 48),": "(0.20, palette.magenta, 34),",
    "segments=10, coverage=0.62, width_scale=0.023,":
        "segments=10, coverage=0.62, width_scale=0.016,",
    "segments=16, coverage=0.31, width_scale=0.0075,":
        "segments=16, coverage=0.31, width_scale=0.0055,",
    "core.setAlpha(34)": "core.setAlpha(18)",
    "color.setAlpha(18)": "color.setAlpha(8)",
    "font = _fit_single_line_font(image, APP_NAME, rect, px, bold=True, family=\"DejaVu Sans\")":
        "font = _fit_single_line_font(image, APP_NAME, rect, px, bold=False, family=\"DejaVu Sans\")",
    "for width_scale, opacity in ((12.0, 0.10), (7.0, 0.18), (3.5, 0.32)):":
        "for width_scale, opacity in ((7.0, 0.07), (4.0, 0.12), (2.2, 0.22)):",
    "painter.setPen(QPen(glow, max(7.0, short * 0.023), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))":
        "painter.setPen(QPen(glow, max(4.0, short * 0.012), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))",
    "clock_text, width * 0.122, palette.primary": "clock_text, width * 0.098, palette.primary",
    "date_text, width * 0.041, palette.secondary": "date_text, width * 0.034, palette.secondary",
    "painter.setOpacity(0.18)\n    painter.setPen(QPen(QBrush(rim), max(10.0, short * 0.024)":
        "painter.setOpacity(0.28)\n    painter.setPen(QPen(QBrush(rim), max(9.0, short * 0.020)",
    "gc = QColor(palette.cyan); gc.setAlpha(42)": "gc = QColor(palette.cyan); gc.setAlpha(58)",
    "gm = QColor(palette.magenta); gm.setAlpha(22)": "gm = QColor(palette.magenta); gm.setAlpha(34)",
}

for old, new in replacements.items():
    if old not in text:
        raise RuntimeError(f"expected renderer fragment not found: {old!r}")
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("Refined v12 renderer after master-image comparison")
