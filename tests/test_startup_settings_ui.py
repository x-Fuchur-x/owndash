import owndash.gui.app_window as app_window


def test_startup_settings_groupbox_is_imported():
    assert hasattr(app_window, "QGroupBox")
