from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text()
INIT = (ROOT / "src/owndash/__init__.py").read_text()


def test_version_is_at_least_093():
    assert '__version__ = "0.14.0 Beta 3"' in INIT


def test_design_inspector_uses_focus_tabs():
    assert "QTabWidget" in WINDOW
    assert 'self.design_tabs.addTab(project_scroll, "Projekt")' in WINDOW
    assert 'self.design_tabs.addTab(background_scroll, "Hintergrund")' in WINDOW
    assert 'self.design_tabs.addTab(widget_scroll, "Widget")' in WINDOW


def test_widget_inspector_separates_style_and_data():
    assert 'self.widget_detail_tabs.addTab(style_page, "Stil")' in WINDOW
    assert 'self.widget_detail_tabs.addTab(data_page, "Daten")' in WINDOW


def test_toolbar_is_compact_and_commands_remain_in_menus():
    assert 'self.menuBar().addMenu("Bearbeiten")' in WINDOW
    assert 'self.menuBar().addMenu("Anordnen")' in WINDOW
    assert 'self.menuBar().addMenu("Ansicht")' in WINDOW
    assert 'toolbar.addAction(self.display_action)' in WINDOW
