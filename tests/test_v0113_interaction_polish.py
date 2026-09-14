from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")

def test_version_0113():
    assert '__version__ = "0.14.0 Beta 2"' in INIT

def test_buttons_have_all_interaction_states():
    for selector in (
        "QPushButton {{",
        "QPushButton:hover {{",
        "QPushButton:pressed {{",
        "QPushButton:focus {{",
        "QPushButton:disabled {{",
    ):
        assert selector in WINDOW

def test_dashboard_buttons_are_equal_action_buttons():
    assert WINDOW.count('setObjectName("dashboardActionButton")') == 4
    assert "row1_layout.addWidget(add_btn, 1)" in WINDOW
    assert "row1_layout.addWidget(duplicate_btn, 1)" in WINDOW
    assert "row2_layout.addWidget(rename_btn, 1)" in WINDOW
    assert "row2_layout.addWidget(delete_btn, 1)" in WINDOW

def test_fields_have_hover_and_focus_feedback():
    assert "QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover" in WINDOW
    assert "QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus" in WINDOW

def test_lists_and_tabs_have_hover_feedback():
    assert "QListWidget::item:hover" in WINDOW
    assert "QTabBar::tab:hover" in WINDOW

def test_pointer_cursor_marks_clickable_controls():
    assert "button.setCursor(Qt.PointingHandCursor)" in WINDOW
    assert "check.setCursor(Qt.PointingHandCursor)" in WINDOW
