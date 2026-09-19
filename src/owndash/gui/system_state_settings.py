from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from owndash.core.preferences import AppPreferences


class SystemStateSettingsWidget(QWidget):
    """Compact editor for system-state screen preferences.

    The widget owns no timers or platform services. It only edits preferences,
    which keeps the settings dialog cheap and makes the runtime integration
    independent from UI lifetime.
    """

    def __init__(
        self,
        preferences: AppPreferences,
        parent: QWidget | None = None,
        *,
        translate: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self._t = translate or (lambda text: text)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 8, 0, 0)
        outer.setSpacing(8)

        self.title_label = QLabel(self._t("Systemzustandsanzeigen"), self)
        font = self.title_label.font()
        font.setBold(True)
        self.title_label.setFont(font)
        outer.addWidget(self.title_label)

        self.enabled_check = QCheckBox(
            self._t("Systemzustände auf dem Display anzeigen"), self
        )
        self.enabled_check.setChecked(preferences.system_state_screens)
        outer.addWidget(self.enabled_check)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        self.theme_combo = QComboBox(self)
        self.theme_combo.addItem("OwnDash", "owndash")
        self.theme_combo.addItem(self._t("Bazzite-inspiriert"), "bazzite-inspired")
        theme_index = self.theme_combo.findData(preferences.system_state_theme)
        self.theme_combo.setCurrentIndex(max(0, theme_index))
        form.addRow(self._t("Theme"), self.theme_combo)

        self.idle_check = QCheckBox(self._t("Ruhemodus"), self)
        self.idle_check.setChecked(preferences.idle_mode)
        form.addRow("", self.idle_check)

        timeout_row = QWidget(self)
        timeout_layout = QHBoxLayout(timeout_row)
        timeout_layout.setContentsMargins(0, 0, 0, 0)
        timeout_layout.setSpacing(6)
        self.idle_timeout = QSpinBox(timeout_row)
        self.idle_timeout.setRange(1, 240)
        self.idle_timeout.setValue(preferences.idle_timeout_minutes)
        self.idle_timeout.setSuffix(f" {self._t('Minuten')}")
        timeout_layout.addWidget(self.idle_timeout)
        timeout_layout.addStretch(1)
        form.addRow(self._t("Zeit bis Ruhemodus"), timeout_row)

        self.lock_check = QCheckBox(
            self._t("Sperrbildschirm berücksichtigen"), self
        )
        self.lock_check.setChecked(preferences.lock_screen_state)
        form.addRow("", self.lock_check)

        outer.addLayout(form)

        self.enabled_check.toggled.connect(self._sync_enabled)
        self.idle_check.toggled.connect(self._sync_enabled)
        self._sync_enabled()

    def _sync_enabled(self) -> None:
        master = self.enabled_check.isChecked()
        self.theme_combo.setEnabled(master)
        self.idle_check.setEnabled(master)
        self.idle_timeout.setEnabled(master and self.idle_check.isChecked())
        self.lock_check.setEnabled(master)

    def apply_to(self, preferences: AppPreferences) -> None:
        preferences.system_state_screens = self.enabled_check.isChecked()
        preferences.system_state_theme = str(self.theme_combo.currentData())
        preferences.idle_mode = self.idle_check.isChecked()
        preferences.idle_timeout_minutes = int(self.idle_timeout.value())
        preferences.lock_screen_state = self.lock_check.isChecked()
