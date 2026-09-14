import pytest

from owndash.sensors import system
from owndash.sensors.catalog import metric_definition, read_metric
from owndash.sensors.system import SystemSensorProvider


@pytest.mark.parametrize("used,total,expected", [
    (str(4 * 1024**3), str(16 * 1024**3), 25.0),
    ("0", str(16 * 1024**3), 0.0),
    ("1024", "1024", 100.0),
    ("", "1024", None),
    ("invalid", "1024", None),
    ("nan", "1024", None),
    ("-1", "1024", None),
    ("1025", "1024", None),
    ("0", "0", None),
    ("0", "-1", None),
])
def test_vram_counters(tmp_path, used, total, expected):
    (tmp_path / "mem_info_vram_used").write_text(used)
    (tmp_path / "mem_info_vram_total").write_text(total)
    values = SystemSensorProvider._gpu_vram_sysfs(tmp_path)
    assert values["vram_percent"] == expected
    if expected is None:
        assert all(value is None for value in values.values())
    else:
        assert values["vram_used_gib"] == int(used) / 1024**3
        assert values["vram_total_gib"] == int(total) / 1024**3


def test_missing_vram_counters(tmp_path):
    assert all(value is None for value in SystemSensorProvider._gpu_vram_sysfs(tmp_path).values())


def test_unreadable_vram_counters(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("denied")
    monkeypatch.setattr(system.Path, "read_text", denied)
    assert all(value is None for value in SystemSensorProvider._gpu_vram_sysfs(tmp_path).values())


def test_vram_flows_from_selected_gpu_to_widget_metrics(tmp_path, monkeypatch):
    (tmp_path / "mem_info_vram_used").write_text(str(4 * 1024**3))
    (tmp_path / "mem_info_vram_total").write_text(str(16 * 1024**3))
    provider = SystemSensorProvider()
    monkeypatch.setattr(provider, "_drm_devices", lambda: [(tmp_path, "amdgpu")])
    monkeypatch.setattr(provider, "_nvidia_smi_gpu", lambda: None)
    monkeypatch.setattr(provider, "_gpu_name", lambda *args: "Test Radeon")
    snap = provider.snapshot()
    for key, value, unit in [
        ("gpu.vram_percent", 25.0, "%"),
        ("gpu.vram_used_gib", 4.0, "GiB"),
        ("gpu.vram_total_gib", 16.0, "GiB"),
    ]:
        assert read_metric(snap, key) == value
        assert metric_definition(key).unit == unit
    assert provider.diagnostics()["gpu"]["vram"] is True
    assert "Grafikspeicher: ✓" in provider.diagnostics_text("de")
    assert "VRAM: ✓" in provider.diagnostics_text("en")


def test_no_gpu_does_not_report_zero_vram(monkeypatch):
    provider = SystemSensorProvider()
    monkeypatch.setattr(provider, "_drm_devices", lambda: [])
    monkeypatch.setattr(provider, "_nvidia_smi_gpu", lambda: None)
    assert read_metric(provider.snapshot(), "gpu.vram_percent") is None
    assert provider.diagnostics()["gpu"]["vram"] is False
