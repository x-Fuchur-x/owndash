from __future__ import annotations

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from owndash.core.preferences import AppPreferences
from owndash.gui.app_window import SafeShutdownWindow


@pytest.fixture
def window(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(
        "owndash.gui.main_window.load_preferences",
        lambda: AppPreferences(setup_completed=True, check_updates=False, language="de"),
    )
    monkeypatch.setattr("owndash.gui.main_window.SystemSensorProvider.snapshot", lambda self: {})
    current = SafeShutdownWindow()
    monkeypatch.setattr(current, "_push_display_frame", lambda: None)
    yield current
    for timer in current.findChildren(QTimer):
        timer.stop()
    current.hide()
    current.deleteLater()
    app.processEvents()


def test_language_switch_retranslates_builtin_widget_titles(window):
    temperature = window.canvas.add_widget("temperature", "Temperatur")
    network = window.canvas.add_widget("network", "Netzwerk")
    gauge_temperature = window.canvas.add_widget("gauge_temp", "Temperatur")

    window.language = "en"
    window._retranslate_ui()

    assert temperature.label == "Temperature"
    assert network.label == "Network"
    assert gauge_temperature.label == "Temperature"

    window.language = "de"
    window._retranslate_ui()

    assert temperature.label == "Temperatur"
    assert network.label == "Netzwerk"
    assert gauge_temperature.label == "Temperatur"


def test_language_switch_does_not_overwrite_custom_widget_title(window):
    custom = window.canvas.add_widget("temperature", "CPU Hotspot")

    window.language = "en"
    window._retranslate_ui()

    assert custom.label == "CPU Hotspot"
