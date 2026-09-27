from pathlib import Path

import owndash.hardware.usb_setup as usb_setup


ROOT = Path(__file__).resolve().parents[1]
USB = (ROOT / "src/owndash/hardware/usb_setup.py").read_text(encoding="utf-8")
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")


def test_beta3_usb_setup_uses_single_pkexec_authentication():
    """USB setup should require only one graphical administrator authentication."""
    assert USB.count("[pkexec,") == 1


def test_beta3_usb_setup_verifies_access_after_installation():
    """Success must only be reported after OwnDash checks real USB access."""
    assert "probe_artinchip_usb()" in USB
    assert ".accessible" in USB


def test_usb_uaccess_rule_runs_before_systemd_seat_acl_rule():
    """TAG+=uaccess must be present before systemd's later seat ACL processing."""
    assert 'RULE_NAME = "70-owndash-usb.rules"' in USB


def test_usb_setup_migrates_legacy_late_rule():
    """Re-running graphical USB setup must remove the old too-late 99-* rule."""
    assert 'LEGACY_RULE_NAME = "99-owndash-usb.rules"' in USB
    assert "rm -f" in USB
    assert "LEGACY_RULE_NAME" in USB


def test_legacy_late_rule_is_detected_for_proactive_migration():
    """A working display must still request setup before suspend exposes bad rule ordering."""
    assert "def legacy_udev_rule_installed()" in USB
    assert "not legacy_udev_rule_installed()" in USB


def test_passive_udev_state_reports_current_rule(tmp_path, monkeypatch):
    probe = getattr(usb_setup, "probe_owndash_udev_state", None)
    assert probe is not None
    monkeypatch.setattr(usb_setup, "UDEV_RULE_DIR", tmp_path)
    (tmp_path / usb_setup.RULE_NAME).write_text("rule", encoding="utf-8")
    assert probe() == "ok"


def test_passive_udev_state_prefers_legacy_rule(tmp_path, monkeypatch):
    probe = getattr(usb_setup, "probe_owndash_udev_state", None)
    assert probe is not None
    monkeypatch.setattr(usb_setup, "UDEV_RULE_DIR", tmp_path)
    (tmp_path / usb_setup.RULE_NAME).write_text("rule", encoding="utf-8")
    (tmp_path / usb_setup.LEGACY_RULE_NAME).write_text("legacy", encoding="utf-8")
    assert probe() == "legacy"


def test_passive_udev_state_reports_missing_rule(tmp_path, monkeypatch):
    probe = getattr(usb_setup, "probe_owndash_udev_state", None)
    assert probe is not None
    monkeypatch.setattr(usb_setup, "UDEV_RULE_DIR", tmp_path)
    assert probe() == "missing"


def test_passive_udev_state_reports_unknown_when_directory_unreadable(monkeypatch):
    probe = getattr(usb_setup, "probe_owndash_udev_state", None)
    assert probe is not None

    class UnreadableRuleDir:
        def __truediv__(self, _name):
            raise OSError("cannot inspect")

    monkeypatch.setattr(usb_setup, "UDEV_RULE_DIR", UnreadableRuleDir())
    assert probe() == "unknown"


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
