from importlib.resources import files

from PySide6.QtGui import QImage


def test_approved_locked_master_replaces_superseded_v10_brand_geometry():
    resource = files("owndash").joinpath("assets", "status-master-locked-480x1920.jpg")
    assert resource.is_file()
    image = QImage.fromData(resource.read_bytes(), "JPG")
    assert not image.isNull()
    assert (image.width(), image.height()) == (480, 1920)
