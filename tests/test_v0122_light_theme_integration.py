from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")

def test_version_0122():
    assert '__version__ = "0.14.0 Beta 1"' in INIT

def test_stylesheet_uses_current_application_palette():
    assert "palette = QPalette(app.palette()) if app is not None else QPalette(self.palette())" in WINDOW

def test_widget_lists_have_explicit_text_color():
    assert "QListWidget {{" in WINDOW
    assert "QListWidget::item {{" in WINDOW
    assert "color: {palette.text().color().name()};" in WINDOW

def test_light_tabs_use_dedicated_light_surface():
    assert 'tab_surface = QColor("#e2e6ea")' in WINDOW
    assert "background-color: {tab_surface.name()};" in WINDOW

def test_selected_tabs_still_merge_into_panels():
    assert "QTabBar::tab:selected {{" in WINDOW
    assert "background-color: {window.name()};" in WINDOW
    assert "QTabBar#dockTabBar::tab:selected {{" in WINDOW
