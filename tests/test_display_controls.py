from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIDGET = ROOT / "src" / "owndash" / "gui" / "display_controls.py"
APP_WINDOW = ROOT / "src" / "owndash" / "gui" / "app_window.py"


def test_display_controls_widget_is_capability_driven():
    source = WIDGET.read_text(encoding="utf-8")
    assert "class DisplayControlsWidget" in source
    assert "caps.hardware_brightness" in source
    assert "caps.device_version" in source
    assert "caps.expansion_mode" in source
    assert "set_brightness" in source
    assert "set_expansion_mode" in source
    assert "DisplayProtocolError" in source


def test_display_controls_do_not_claim_power_off():
    source = WIDGET.read_text(encoding="utf-8").lower()
    assert "power off" not in source
    assert "sleep" not in source


def test_app_window_exposes_controls_only_for_connected_supported_backend():
    source = APP_WINDOW.read_text(encoding="utf-8")
    assert "Display-Steuerung …" in source
    assert "self.display_controls_action.setEnabled(False)" in source
    assert "caps.hardware_brightness or caps.device_version or caps.expansion_mode" in source
    assert "DisplayControlsWidget(streamer.backend, info" in source
