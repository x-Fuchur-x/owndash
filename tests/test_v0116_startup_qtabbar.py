from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
WINDOW_PATH = ROOT / "src/owndash/gui/main_window.py"
WINDOW = WINDOW_PATH.read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")

def test_version_0116():
    assert '__version__ = "0.14.0 Beta 3"' in INIT

def test_qtabbar_is_imported_when_referenced():
    tree = ast.parse(WINDOW)
    qtwidgets_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "PySide6.QtWidgets":
            qtwidgets_imports.update(alias.name for alias in node.names)
    assert "QTabBar" in qtwidgets_imports
    assert "findChildren(QTabBar)" in WINDOW
