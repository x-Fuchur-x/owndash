from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")
I18N = (ROOT / "src/owndash/i18n.py").read_text(encoding="utf-8")
APPEARANCE = (ROOT / "src/owndash/appearance.py").read_text(encoding="utf-8")
PREFERENCES = (ROOT / "src/owndash/core/preferences.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")


def test_version_0120():
    assert '__version__ = "0.14.0 Beta 1"' in INIT


def test_preferences_are_loaded_before_ui_build():
    load_pos = WINDOW.index("self.preferences: AppPreferences = load_preferences()")
    toolbar_pos = WINDOW.index("self._build_toolbar()")
    assert load_pos < toolbar_pos


def test_system_language_is_default_and_german_english_supported():
    assert 'language: str = "system"' in PREFERENCES
    assert '{"system", "de", "en"}' in PREFERENCES
    assert 'return "de" if system.startswith("de") else "en"' in I18N


def test_appearance_supports_system_dark_light():
    assert 'appearance: str = "system"' in PREFERENCES
    assert '{"system", "dark", "light"}' in PREFERENCES
    assert 'if mode == "system":' in APPEARANCE
    assert 'dark = mode == "dark"' in APPEARANCE


def test_settings_are_persisted():
    assert 'default_config_dir() / "settings.json"' in PREFERENCES
    assert "save_preferences(self.preferences)" in WINDOW


def test_settings_dialog_exposes_language_and_appearance():
    assert 'settings_action = QAction("Einstellungen …", self)' in WINDOW
    assert 'language_combo.addItem(self._t("Systemsprache"), "system")' in WINDOW
    assert 'language_combo.addItem(self._t("Deutsch"), "de")' in WINDOW
    assert 'language_combo.addItem(self._t("Englisch"), "en")' in WINDOW
    assert 'appearance_combo.addItem(self._t("System"), "system")' in WINDOW
    assert 'appearance_combo.addItem(self._t("Dunkel"), "dark")' in WINDOW
    assert 'appearance_combo.addItem(self._t("Hell"), "light")' in WINDOW


def test_language_switch_retranslates_existing_ui():
    assert "retranslate_tree(self, self.language)" in WINDOW
    assert "def retranslate_tree" in I18N
    assert "_owndash_source_text" in I18N
    assert "_owndash_tab_sources" in I18N


def test_widget_palette_is_retranslated_too():
    assert "definition = widget_type(str(item.data(Qt.UserRole)))" in WINDOW
    assert "item.setText(self._t(definition.label))" in WINDOW


def test_appearance_is_palette_based_for_linux_integration():
    assert "self._system_palette = QPalette(QApplication.instance().palette())" in WINDOW
    assert "apply_appearance(self.preferences.appearance, self._system_palette)" in WINDOW
    assert "app.setPalette(make_palette(mode, system_palette))" in APPEARANCE


def test_english_dictionary_covers_core_navigation():
    tree = ast.parse(I18N)
    keys = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "EN":
            if isinstance(node.value, ast.Dict):
                keys = {k.value for k in node.value.keys if isinstance(k, ast.Constant)}
    required = {
        "Projekt", "Bearbeiten", "Anordnen", "Ansicht", "Speichern", "Öffnen",
        "Widgets", "Ebenen", "Dashboards", "Layout", "Design", "Hintergrund",
        "Einstellungen", "Sprache", "Erscheinungsbild",
    }
    assert required <= keys
