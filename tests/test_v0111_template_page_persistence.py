from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")

def test_version_0111():
    assert '__version__ = "0.14.0 Beta 4"' in INIT

def test_template_no_longer_replaces_whole_profile():
    start = WINDOW.index("    def _load_template(self) -> None:")
    end = WINDOW.index("\n    def _add_selected_widget", start)
    block = WINDOW[start:end]
    assert "_apply_profile(make_template(name)" not in block
    assert "self.dashboard_pages[self.active_page_index] = template_page" in block

def test_template_preserves_current_dashboard_name():
    start = WINDOW.index("    def _load_template(self) -> None:")
    end = WINDOW.index("\n    def _add_selected_widget", start)
    block = WINDOW[start:end]
    assert "name=self.dashboard_pages[self.active_page_index].name" in block

def test_template_resyncs_dashboard_ui_without_dropping_pages():
    start = WINDOW.index("    def _load_template(self) -> None:")
    end = WINDOW.index("\n    def _add_selected_widget", start)
    block = WINDOW[start:end]
    assert "self._sync_pages_ui()" in block
    assert "self._capture_active_page()" in block
