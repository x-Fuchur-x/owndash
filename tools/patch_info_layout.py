from pathlib import Path


main_path = Path("src/owndash/gui/main_window.py")
source = main_path.read_text(encoding="utf-8")

# Keep the already-approved shared read-only information layout patch narrow.
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

for grid_name in ("system_grid", "cpu_grid", "gpu_grid", "services_grid"):
    anchor = f"        {grid_name}.setColumnStretch(1, 1)\n"
    configured = anchor + f"        configure_info_grid({grid_name})\n"
    if configured in source:
        continue
    if anchor not in source:
        raise SystemExit(f"expected grid anchor not found: {grid_name}")
    source = source.replace(anchor, configured, 1)

# Background-image removal UX: explicit button plus Delete-key behavior.
old_image_button = (
    "        image_button = QPushButton(\"Bild wählen …\")\n"
    "        image_button.clicked.connect(self._choose_background_image)\n"
    "        self.bg_edit_check = QCheckBox(\"Bild direkt auf dem Display bearbeiten\")\n"
)
new_image_button = (
    "        image_button = QPushButton(\"Bild wählen …\")\n"
    "        image_button.clicked.connect(self._choose_background_image)\n"
    "        image_actions = QWidget()\n"
    "        image_actions_layout = QHBoxLayout(image_actions)\n"
    "        image_actions_layout.setContentsMargins(0, 0, 0, 0)\n"
    "        image_actions_layout.setSpacing(6)\n"
    "        image_actions_layout.addWidget(image_button, 1)\n"
    "        self.remove_background_button = QPushButton(\"Bild entfernen\")\n"
    "        self.remove_background_button.clicked.connect(self._remove_background_image)\n"
    "        image_actions_layout.addWidget(self.remove_background_button, 1)\n"
    "        self.bg_edit_check = QCheckBox(\"Bild direkt auf dem Display bearbeiten\")\n"
)
if new_image_button not in source:
    if old_image_button not in source:
        raise SystemExit("expected background image button anchor not found")
    source = source.replace(old_image_button, new_image_button, 1)

old_form_row = "        bg_form.addRow(image_button)\n"
new_form_row = "        bg_form.addRow(image_actions)\n"
if new_form_row not in source:
    if old_form_row not in source:
        raise SystemExit("expected background image action row anchor not found")
    source = source.replace(old_form_row, new_form_row, 1)

old_delete = (
    "    def _delete_selected(self) -> None:\n"
    "        selected = self.canvas.selected_widgets()\n"
)
new_delete = (
    "    def _delete_selected(self) -> None:\n"
    "        if self.canvas.background_image_is_selected():\n"
    "            self._remove_background_image()\n"
    "            return\n"
    "        selected = self.canvas.selected_widgets()\n"
)
if new_delete not in source:
    if old_delete not in source:
        raise SystemExit("expected delete-selected anchor not found")
    source = source.replace(old_delete, new_delete, 1)

remove_method_anchor = "    def _sync_background_controls(self, config: BackgroundConfig) -> None:\n"
remove_method = (
    "    def _remove_background_image(self) -> None:\n"
    "        before = self._profile_from_canvas().to_json()\n"
    "        if not self.canvas.remove_background_image():\n"
    "            return\n"
    "        self.bg_edit_check.blockSignals(True)\n"
    "        self.bg_edit_check.setChecked(False)\n"
    "        self.bg_edit_check.blockSignals(False)\n"
    "        self._sync_background_controls(self.canvas.current_background_config())\n"
    "        self._commit_history(before, \"Hintergrundbild entfernen\")\n"
    "        self.statusBar().showMessage(self._t(\"Hintergrundbild entfernt\"), 2500)\n"
    "\n"
)
if remove_method not in source:
    if remove_method_anchor not in source:
        raise SystemExit("expected background controls anchor not found")
    source = source.replace(remove_method_anchor, remove_method + remove_method_anchor, 1)

old_image_enabled = (
    "        image_enabled = config.mode == \"image\" and bool(config.image_path)\n"
    "        for transform_control in (self.bg_x_spin, self.bg_y_spin, self.bg_scale_spin):\n"
)
new_image_enabled = (
    "        image_enabled = config.mode == \"image\" and bool(config.image_path)\n"
    "        if hasattr(self, \"remove_background_button\"):\n"
    "            self.remove_background_button.setEnabled(bool(config.image_path))\n"
    "        for transform_control in (self.bg_x_spin, self.bg_y_spin, self.bg_scale_spin):\n"
)
if new_image_enabled not in source:
    if old_image_enabled not in source:
        raise SystemExit("expected image-enabled anchor not found")
    source = source.replace(old_image_enabled, new_image_enabled, 1)

main_path.write_text(source, encoding="utf-8")


canvas_path = Path("src/owndash/gui/canvas.py")
canvas = canvas_path.read_text(encoding="utf-8")

canvas_anchor = (
    "    def fit_background_image(self, fit: str) -> None:\n"
)
canvas_methods = (
    "    def background_image_is_selected(self) -> bool:\n"
    "        item = self._background_item\n"
    "        return bool(item is not None and item.isSelected())\n"
    "\n"
    "    def remove_background_image(self) -> bool:\n"
    "        if self._background_item is None and not self.background_config.image_path:\n"
    "            return False\n"
    "        config = self.current_background_config()\n"
    "        config.mode = \"gradient\"\n"
    "        config.image_path = \"\"\n"
    "        config.image_x = 0.0\n"
    "        config.image_y = 0.0\n"
    "        config.image_width = 0.0\n"
    "        config.image_height = 0.0\n"
    "        config.image_fit = \"cover\"\n"
    "        self.set_background_edit_enabled(False)\n"
    "        self.set_background_config(config)\n"
    "        return True\n"
    "\n"
)
if canvas_methods not in canvas:
    if canvas_anchor not in canvas:
        raise SystemExit("expected canvas background-fit anchor not found")
    canvas = canvas.replace(canvas_anchor, canvas_methods + canvas_anchor, 1)

canvas_path.write_text(canvas, encoding="utf-8")
