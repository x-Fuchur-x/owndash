from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = (ROOT/"src/owndash/sensors/system.py").read_text(encoding="utf-8")
WINDOW = (ROOT/"src/owndash/gui/main_window.py").read_text(encoding="utf-8")
INIT = (ROOT/"src/owndash/__init__.py").read_text(encoding="utf-8")
PYPROJECT = (ROOT/"pyproject.toml").read_text(encoding="utf-8")

def test_beta4_version():
    assert '__version__ = "0.14.0 Beta 4"' in INIT
    assert 'version = "0.14.0b4"' in PYPROJECT

def test_sensor_layer_discovers_common_linux_interfaces():
    assert 'Path("/proc/stat")' in SYSTEM
    assert 'Path("/sys/class/hwmon")' in SYSTEM
    assert 'Path("/sys/class/drm")' in SYSTEM
    assert 'Path("/sys/class/powercap")' in SYSTEM

def test_no_fixed_hwmon_index():
    assert "hwmon0" not in SYSTEM
    assert "hwmon1" not in SYSTEM

def test_nvidia_is_optional():
    assert 'shutil.which("nvidia-smi")' in SYSTEM
    assert "timeout=1.5" in SYSTEM
    assert "return None" in SYSTEM

def test_gpu_drivers_are_capability_based():
    assert '"amdgpu"' in SYSTEM
    assert '"i915"' in SYSTEM
    assert '"xe"' in SYSTEM
    assert '"nvidia"' in SYSTEM

def test_cpu_power_supports_zenergy_and_powercap():
    assert '"zenergy"' in SYSTEM
    assert "_energy_counter_power_from_powercap" in SYSTEM

def test_diagnostics_are_exposed_in_help():
    assert 'QAction("System- und Sensorinformationen …", self)' in WINDOW
    assert "self.sensor_provider.diagnostics_text(self.language)" in WINDOW

def test_bug_report_contains_sensor_diagnostics():
    assert "OwnDash Sensor-Diagnose" in WINDOW
    assert "OwnDash sensor diagnostics" in WINDOW
