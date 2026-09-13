from owndash.core.templates import make_template, template_names


def test_all_templates_fit_canvas():
    for name in template_names():
        profile = make_template(name)
        assert profile.widgets
        for widget in profile.widgets:
            fixed = widget.normalized(profile.canvas_width, profile.canvas_height)
            assert fixed.x + fixed.width <= profile.canvas_width
            assert fixed.y + fixed.height <= profile.canvas_height


def test_gaming_template_contains_gauges():
    profile = make_template("Gaming Gauges")
    assert sum(widget.kind.startswith("gauge_") for widget in profile.widgets) >= 4
