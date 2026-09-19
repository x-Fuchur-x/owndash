import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from owndash.core.preferences import AppPreferences
from owndash.gui.system_state_settings import SystemStateSettingsWidget


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_controls_load_from_preferences(app):
    prefs = AppPreferences(
        system_state_screens=False,
        system_state_theme="bazzite-inspired",
        idle_mode=False,
        idle_timeout_minutes=90,
        lock_screen_state=False,
    )
    widget = SystemStateSettingsWidget(prefs)
    try:
        assert widget.enabled_check.isChecked() is False
        assert widget.theme_combo.currentData() == "bazzite-inspired"
        assert widget.idle_check.isChecked() is False
        assert widget.idle_timeout.value() == 90
        assert widget.lock_check.isChecked() is False
    finally:
        widget.deleteLater()


def test_apply_updates_preferences(app):
    prefs = AppPreferences()
    widget = SystemStateSettingsWidget(prefs)
    try:
        widget.enabled_check.setChecked(True)
        widget.theme_combo.setCurrentIndex(widget.theme_combo.findData("bazzite-inspired"))
        widget.idle_check.setChecked(True)
        widget.idle_timeout.setValue(45)
        widget.lock_check.setChecked(False)
        widget.apply_to(prefs)

        assert prefs.system_state_screens is True
        assert prefs.system_state_theme == "bazzite-inspired"
        assert prefs.idle_mode is True
        assert prefs.idle_timeout_minutes == 45
        assert prefs.lock_screen_state is False
    finally:
        widget.deleteLater()


def test_master_toggle_disables_children_without_destroying_values(app):
    prefs = AppPreferences(
        system_state_screens=True,
        system_state_theme="bazzite-inspired",
        idle_mode=True,
        idle_timeout_minutes=75,
        lock_screen_state=True,
    )
    widget = SystemStateSettingsWidget(prefs)
    try:
        widget.enabled_check.setChecked(False)
        assert widget.theme_combo.isEnabled() is False
        assert widget.idle_check.isEnabled() is False
        assert widget.idle_timeout.isEnabled() is False
        assert widget.lock_check.isEnabled() is False
        assert widget.theme_combo.currentData() == "bazzite-inspired"
        assert widget.idle_timeout.value() == 75

        widget.enabled_check.setChecked(True)
        assert widget.theme_combo.isEnabled() is True
        assert widget.idle_check.isEnabled() is True
        assert widget.idle_timeout.isEnabled() is True
        assert widget.lock_check.isEnabled() is True
        assert widget.theme_combo.currentData() == "bazzite-inspired"
        assert widget.idle_timeout.value() == 75
    finally:
        widget.deleteLater()


def test_idle_toggle_only_controls_timeout_field(app):
    widget = SystemStateSettingsWidget(AppPreferences())
    try:
        widget.idle_check.setChecked(False)
        assert widget.idle_timeout.isEnabled() is False
        assert widget.lock_check.isEnabled() is True
        widget.idle_check.setChecked(True)
        assert widget.idle_timeout.isEnabled() is True
    finally:
        widget.deleteLater()


def test_translation_callback_is_used_for_visible_labels(app):
    translations = {"Systemzustandsanzeigen": "System state screens"}
    widget = SystemStateSettingsWidget(
        AppPreferences(), translate=lambda text: translations.get(text, text)
    )
    try:
        assert widget.title_label.text() == "System state screens"
    finally:
        widget.deleteLater()
