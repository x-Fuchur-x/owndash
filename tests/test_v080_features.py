from owndash.core.templates import make_template, template_names
from owndash.themes import ThemeManager
from owndash.widgets.registry import widget_type


def test_chart_widgets_exist():
    assert widget_type("chart") is not None
    assert widget_type("sparkline") is not None


def test_new_templates_exist_and_are_nonempty():
    for name in ("Telemetry Lab", "Racing Stack", "OLED Essentials"):
        assert name in template_names()
        assert make_template(name).widgets


def test_new_themes_exist():
    names = set(ThemeManager.names())
    assert {"Synthwave Grid", "Carbon", "Aurora", "Sunset Drive"} <= names


def test_gaming_gauges_have_metric_binding():
    profile = make_template("Gaming Gauges")
    gauges = [widget for widget in profile.widgets if widget.kind.startswith("gauge_")]
    assert gauges
    assert all("metric_key" in widget.options for widget in gauges)
