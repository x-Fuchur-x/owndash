from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT/"src/owndash/gui/main_window.py").read_text(encoding="utf-8")

def test_setup_rows_cannot_collapse_into_each_other():
    assert "row_height = 32" in WINDOW
    assert "name.setFixedHeight(row_height)" in WINDOW
    assert "label.setFixedHeight(row_height)" in WINDOW
    assert "grid.setRowMinimumHeight(row, row_height)" in WINDOW
    assert "box.setMinimumHeight(54 + len(rows) * row_height)" in WINDOW

def test_setup_has_stable_status_column():
    assert "label.setMinimumWidth(220)" in WINDOW
    assert "grid.setColumnMinimumWidth(1, 220)" in WINDOW

def test_setup_sections_scroll_instead_of_being_compressed():
    assert "sections_scroll = QScrollArea(dialog)" in WINDOW
    assert "sections_scroll.setWidgetResizable(True)" in WINDOW
    assert "sections_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)" in WINDOW
    assert "outer.addWidget(sections_scroll, 1)" in WINDOW

def test_setup_dialog_has_more_vertical_room():
    assert "dialog.setMinimumSize(720, 680)" in WINDOW
    assert "dialog.resize(800, 760)" in WINDOW
