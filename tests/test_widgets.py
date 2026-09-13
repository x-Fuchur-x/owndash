from owndash.widgets.registry import widget_type


def test_gauge_presets_have_valid_ranges():
    for key in ("gauge_cpu", "gauge_gpu", "gauge_temp", "gauge_power"):
        preset = widget_type(key)
        assert preset is not None
        assert preset.options["gauge_max"] > preset.options["gauge_min"]
        assert preset.width >= 200 and preset.height >= 200


def test_unknown_widget_type_returns_none():
    assert widget_type("does-not-exist") is None
