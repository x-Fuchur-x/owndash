from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
USB = (ROOT / "src/owndash/hardware/usb_setup.py").read_text(encoding="utf-8")


def test_beta3_usb_setup_uses_single_pkexec_authentication():
    """USB setup should require only one graphical administrator authentication."""
    assert USB.count("[pkexec,") == 1


def test_beta3_usb_setup_verifies_access_after_installation():
    """Success must only be reported after OwnDash checks real USB access."""
    assert "probe_artinchip_usb()" in USB
    assert ".accessible" in USB


WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")


def test_beta3_missing_usb_access_is_marked_as_required():
    """A connected USB display without access must not look optional."""
    assert '"Einrichtung erforderlich"' in WINDOW
    assert "error_color" in WINDOW


CANVAS = (ROOT / "src/owndash/gui/canvas.py").read_text(encoding="utf-8")


def test_beta3_canvas_uses_multi_handle_api_consistently():
    """Canvas items must not call the removed single resize-handle API."""
    assert "_handle_rect()" not in CANVAS
    assert "_handle_rects()" in CANVAS


def test_beta3_fresh_start_initializes_dashboard_page():
    """A fresh start must create a real dashboard page before editor actions run."""
    assert "self.dashboard_pages = [self._page_from_canvas(" in WINDOW
