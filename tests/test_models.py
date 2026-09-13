from owndash.core.models import BackgroundConfig, Profile, WidgetConfig


def test_widget_normalization_keeps_widget_inside_canvas():
    widget = WidgetConfig("cpu", -10, 1900, 900, 500)
    fixed = widget.normalized(480, 1920)
    assert fixed.x == 0
    assert fixed.y == 1420
    assert fixed.width == 480
    assert fixed.height == 500


def test_profile_json_roundtrip_preserves_appearance():
    profile = Profile(
        theme="Neon Cyan",
        background=BackgroundConfig(mode="gradient", color="#010203", color2="#040506"),
        widgets=[
            WidgetConfig(
                "cpu",
                10,
                20,
                300,
                160,
                title="CPU",
                options={"accent": "#00ffff", "opacity": 85, "animation": "pulse"},
            )
        ],
    )
    restored = Profile.from_json(profile.to_json())
    assert restored == profile


def test_legacy_profile_background_string_is_supported():
    restored = Profile.from_json(
        '{"name":"Old","background":"#123456","widgets":[{"kind":"cpu","x":0,"y":0,"width":100,"height":100}]}'
    )
    assert restored.background.mode == "solid"
    assert restored.background.color == "#123456"


def test_widget_z_order_roundtrip():
    profile = Profile(widgets=[WidgetConfig("cpu", 0, 0, 100, 100, z=4.5)])
    restored = Profile.from_json(profile.to_json())
    assert restored.widgets[0].z == 4.5


def test_background_image_transform_roundtrip():
    profile = Profile(background=BackgroundConfig(
        mode="image", image_path="/tmp/background.png",
        image_x=-120.5, image_y=33.0, image_width=900.0, image_height=506.25,
        image_opacity=73, image_fit="manual",
    ))
    restored = Profile.from_json(profile.to_json())
    assert restored.background == profile.background


def test_legacy_image_background_gets_safe_transform_defaults():
    restored = Profile.from_json('{"background":{"mode":"image","image_path":"/tmp/old.png"},"widgets":[]}')
    assert restored.background.image_fit == "cover"
    assert restored.background.image_width == 0.0
    assert restored.background.image_opacity == 100
