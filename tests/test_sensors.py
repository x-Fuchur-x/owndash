from owndash.sensors.system import _format_rate, _percent


def test_percent_is_clamped():
    assert _percent(50, 100) == 50
    assert _percent(200, 100) == 100
    assert _percent(1, 0) == 0


def test_format_rate_has_single_rate_suffix():
    assert _format_rate(1024) == "1.0 KB/s"
    assert "/s/s" not in _format_rate(1024 * 1024)
