from owndash.gui.status_master import _master_image


def test_approved_locked_master_replaces_superseded_v10_brand_geometry():
    image = _master_image()
    assert not image.isNull()
    assert (image.width(), image.height()) == (480, 1920)
