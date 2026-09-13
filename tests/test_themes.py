from owndash.themes import DEFAULT_THEME_NAME, ThemeManager


def test_default_theme_and_presets_have_complete_widget_options():
    assert DEFAULT_THEME_NAME in ThemeManager.names()
    required = {"background", "border", "accent", "title_color", "value_color", "bar_track", "opacity", "radius", "title_size", "value_size", "glow", "animation"}
    for name in ThemeManager.names():
        theme = ThemeManager.get(name)
        assert required <= theme.widget_options().keys()


def test_unknown_theme_falls_back_to_default():
    assert ThemeManager.get("does-not-exist") == ThemeManager.get(DEFAULT_THEME_NAME)


def test_theme_pack_contains_extended_presets():
    names = set(ThemeManager.names())
    assert len(names) >= 14
    assert {
        "Cyber Purple",
        "OLED Black",
        "Vaporwave",
        "Racing Red",
        "Ice White",
    } <= names
