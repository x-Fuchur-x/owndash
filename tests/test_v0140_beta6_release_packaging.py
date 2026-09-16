from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT = (ROOT/"src/owndash/__init__.py").read_text(encoding="utf-8")
PROJECT = (ROOT/"pyproject.toml").read_text(encoding="utf-8")
WINDOW = (ROOT/"src/owndash/gui/main_window.py").read_text(encoding="utf-8")
SYSTEM = (ROOT/"src/owndash/sensors/system.py").read_text(encoding="utf-8")
USB = (ROOT/"src/owndash/hardware/usb_setup.py").read_text(encoding="utf-8")
APPIMAGE = (ROOT/"packaging/appimage/build-appimage.sh").read_text(encoding="utf-8")
WORKFLOW = (ROOT/".github/workflows/appimage.yml").read_text(encoding="utf-8")

def test_beta6_version():
    assert '__version__ = "0.14.0 Beta 3"' in INIT
    assert 'version = "0.14.0b3"' in PROJECT

def test_udev_rule_is_bundled():
    assert '"resources/*.rules"' in PROJECT
    rule = ROOT/"src/owndash/resources/99-owndash-usb.rules"
    assert rule.exists()
    text = rule.read_text(encoding="utf-8")
    assert 'ATTR{idVendor}=="33c3"' in text
    assert 'ATTR{idProduct}=="0e02"' in text
    assert 'TAG+="uaccess"' in text

def test_usb_probe_and_graphical_setup_are_unprivileged_by_default():
    assert "def probe_artinchip_usb()" in USB
    assert "os.access(node, os.R_OK | os.W_OK)" in USB
    assert 'shutil.which("pkexec")' in USB
    assert "No privileged command is run automatically" in USB
    assert "shell=True" not in USB

def test_first_run_checks_display_output_and_can_offer_usb_setup():
    assert 'self._t("Display-Ausgabe")' in WINDOW
    assert 'self._t("Standard-Monitor-Ausgabe")' in WINDOW
    assert 'self._t("ArtInChip / VSDISPLAY verbunden")' in WINDOW
    assert 'self._t("USB-Zugriffsberechtigung")' in WINDOW
    assert 'QPushButton(self._t("USB-Zugriff einrichten")' in WINDOW
    assert "install_udev_rule()" in WINDOW

def test_capability_report_contains_display_section():
    assert '"display": {' in SYSTEM
    assert '"artinchip_connected": usb.connected' in SYSTEM
    assert '"artinchip_accessible": usb.accessible' in SYSTEM
    assert '"graphical_usb_setup": can_offer_graphical_setup()' in SYSTEM

def test_appimage_build_is_scripted():
    assert "pyinstaller" in APPIMAGE
    assert "appimagetool" in APPIMAGE
    assert "OwnDash.AppDir" in APPIMAGE
    assert "APPIMAGE_EXTRACT_AND_RUN=1" in APPIMAGE

def test_github_action_builds_appimage_artifact():
    assert "Build AppImage" in WORKFLOW
    assert "packaging/appimage/build-appimage.sh" in WORKFLOW
    assert "actions/upload-artifact@v7" in WORKFLOW
