from importlib.resources import files


def test_application_icon_is_packaged():
    icon = files("owndash").joinpath("assets", "owndash.svg")
    assert icon.is_file()
    text = icon.read_text(encoding="utf-8")
    assert "<svg" in text
    assert "OwnDash" not in text  # icon remains readable at small sizes without text

