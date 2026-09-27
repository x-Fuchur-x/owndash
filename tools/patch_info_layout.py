from pathlib import Path

path = Path("src/owndash/gui/main_window.py")
source = path.read_text(encoding="utf-8")

old_import = "from .canvas import DashboardCanvas, WidgetItem\n"
new_import = (
    "from .canvas import DashboardCanvas, WidgetItem\n"
    "from .info_layout import configure_info_grid, make_info_label\n"
)
if new_import not in source:
    if old_import not in source:
        raise SystemExit("expected canvas import anchor not found")
    source = source.replace(old_import, new_import, 1)

old_name = "            name = QLabel(title, dialog)\n            name.setMinimumWidth(145)\n"
new_name = "            name = make_info_label(title, dialog)\n"
if new_name not in source:
    if old_name not in source:
        raise SystemExit("expected diagnostics label anchor not found")
    source = source.replace(old_name, new_name, 1)

old_value = (
    "        def value_label(text: str) -> QLabel:\n"
    "            label = QLabel(text, dialog)\n"
    "            label.setTextInteractionFlags(Qt.TextSelectableByMouse)\n"
    "            return label\n"
)
new_value = (
    "        def value_label(text: str) -> QLabel:\n"
    "            label = QLabel(text, dialog)\n"
    "            label.setAlignment(Qt.AlignLeft | Qt.AlignTop)\n"
    "            label.setWordWrap(True)\n"
    "            label.setTextInteractionFlags(Qt.TextSelectableByMouse)\n"
    "            return label\n"
)
if new_value not in source:
    if old_value not in source:
        raise SystemExit("expected diagnostics value-label anchor not found")
    source = source.replace(old_value, new_value, 1)

anchors = (
    "        system_grid.setColumnStretch(1, 1)\n",
    "        cpu_grid.setColumnStretch(1, 1)\n",
    "        gpu_grid.setColumnStretch(1, 1)\n",
    "        services_grid.setColumnStretch(1, 1)\n",
)
for anchor in anchors:
    configured = anchor + "        configure_info_grid(" + anchor.split(".", 1)[0].strip() + ")\n"
    if configured in source:
        continue
    if anchor not in source:
        raise SystemExit(f"expected grid anchor not found: {anchor.strip()}")
    source = source.replace(anchor, configured, 1)

path.write_text(source, encoding="utf-8")
