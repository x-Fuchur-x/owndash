from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT/"src/owndash/gui/main_window.py").read_text(encoding="utf-8")
SYSTEM = (ROOT/"src/owndash/sensors/system.py").read_text(encoding="utf-8")
I18N = (ROOT/"src/owndash/i18n.py").read_text(encoding="utf-8")

def test_diagnostics_uses_structured_cards():
    assert "system_box = QGroupBox" in WINDOW
    assert "cpu_box = QGroupBox" in WINDOW
    assert "gpu_box = QGroupBox" in WINDOW
    assert "services_box = QGroupBox" in WINDOW
    assert "QGridLayout" in WINDOW

def test_available_sensors_get_green_check():
    assert 'QLabel("✓" if available else "—"' in WINDOW
    assert "status_green" in WINDOW

def test_diagnostics_has_consistent_spacing():
    assert "setHorizontalSpacing(22)" in WINDOW
    assert "setVerticalSpacing(9)" in WINDOW
    assert "setFixedWidth(34)" in WINDOW

def test_gpu_name_uses_optional_lspci():
    assert 'shutil.which("lspci")' in SYSTEM
    assert '[binary, "-s", pci_address]' in SYSTEM
    assert "timeout=1.0" in SYSTEM
    assert "AMD GPU {device_id}" in SYSTEM

def test_new_diagnostics_strings_are_localized():
    assert '"Weitere Systemwerte": "Additional system values"' in I18N
    assert '"Verfügbar": "Available"' in I18N
    assert '"Nicht verfügbar": "Not available"' in I18N
