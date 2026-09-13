from __future__ import annotations

from pathlib import Path
import platform
import webbrowser

from PySide6.QtCore import QMimeData, QObject, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QDrag, QKeySequence, QPalette, QUndoCommand, QUndoStack
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QLayout,
    QListWidget,
    QListWidgetItem,
    QApplication,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QSizePolicy,
    QSpinBox,
    QSystemTrayIcon,
    QTabBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from owndash import APP_NAME, __version__
from owndash.project_info import GITHUB_ISSUES_URL, GITHUB_URL
from owndash.assets import app_icon_path
from owndash.core.config import default_profile_path, load_profile, save_profile
from owndash.core.preferences import AppPreferences, load_preferences, save_preferences
from owndash.appearance import apply_appearance
from owndash.i18n import resolved_language, retranslate_tree, tr
from owndash.core.models import BackgroundConfig, DashboardPage, Profile, WidgetConfig
from owndash.core.display_devices import logical_size
from owndash.core.streaming import DisplayStreamer
from owndash.core.templates import make_template, template_names
from owndash.hardware.aic_usb import AicUsbDisplayBackend, UsbBackendSettings
from owndash.hardware.usb_setup import install_udev_rule
from owndash.hardware.screen_display import ScreenBackendSettings, ScreenDisplayBackend, ScreenPresenter
from owndash.sensors.system import SystemSensorProvider, system_capabilities
from owndash.sensors.catalog import METRICS, metric_definition
from owndash.themes import DEFAULT_THEME_NAME, ThemeManager
from owndash.widgets.registry import DEFAULT_WIDGETS, widget_type

from .canvas import DashboardCanvas, WidgetItem






class FocusSafeSpinBox(QSpinBox):
    """Spin box that only consumes the mouse wheel while it owns focus."""

    def wheelEvent(self, event) -> None:  # noqa: ANN001
        if not self.hasFocus():
            event.ignore()
            return
        super().wheelEvent(event)


class FocusSafeDoubleSpinBox(QDoubleSpinBox):
    """Double spin box that lets the inspector scroll unless actively edited."""

    def wheelEvent(self, event) -> None:  # noqa: ANN001
        if not self.hasFocus():
            event.ignore()
            return
        super().wheelEvent(event)


class DisplayBridge(QObject):
    status = Signal(str)
    connected = Signal(object)
    error = Signal(object)


class WidgetPalette(QListWidget):
    def startDrag(self, supported_actions) -> None:  # noqa: ANN001
        del supported_actions
        item = self.currentItem()
        if item is None:
            return
        kind = item.data(Qt.UserRole)
        mime = QMimeData()
        mime.setData("application/x-owndash-widget", f"{kind}\t{item.text()}".encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)


class ProfileCommand(QUndoCommand):
    def __init__(self, window: "MainWindow", before: str, after: str, text: str):
        super().__init__(text)
        self.window = window
        self.before = before
        self.after = after
        self._first_redo = True

    def undo(self) -> None:
        self.window._restore_profile_json(self.before)

    def redo(self) -> None:
        if self._first_redo:
            self._first_redo = False
            return
        self.window._restore_profile_json(self.after)


class MainWindow(QMainWindow):
    CONTROL_HEIGHT = 34
    NUMERIC_FIELD_WIDTH = 138
    COMPACT_FIELD_WIDTH = 190

    def __init__(self):
        super().__init__()
        self.profile_path = default_profile_path()
        self.preferences: AppPreferences = load_preferences()
        self.language = resolved_language(self.preferences.language)
        self._system_palette = QPalette(QApplication.instance().palette())
        apply_appearance(self.preferences.appearance, self._system_palette)

        self.sensor_provider = SystemSensorProvider()
        self.undo_stack = QUndoStack(self)
        self._history_json = ""
        self._restoring = False
        self.current_theme_name = DEFAULT_THEME_NAME
        self.display_bridge = DisplayBridge(self)
        self.display_bridge.status.connect(self._display_status)
        self.display_bridge.connected.connect(self._display_connected)
        self.display_bridge.error.connect(self._display_error)
        self.display_streamer: DisplayStreamer | None = None
        self.display_connected = False
        self.keep_display_running_on_close = True
        self._force_quit = False
        self._tray_hint_shown = False

        self._performance_mode = "Balanced"
        self._performance_profiles = {
            "Eco": {"widget_ms": 333, "aurora_ms": 667, "quality": 52},
            "Balanced": {"widget_ms": 200, "aurora_ms": 400, "quality": 58},
            "Smooth": {"widget_ms": 125, "aurora_ms": 250, "quality": 65},
        }
        self._display_idle_interval_ms = 500
        self._last_display_payload: bytes | None = None
        self.display_backend_key = "aic_usb"
        self.display_device_id = "auto"
        self._screen_presenter: ScreenPresenter | None = None

        self.dashboard_pages: list[DashboardPage] = []
        self.active_page_index = 0
        self._switching_page = False

        self.setWindowTitle("")
        self.canvas = DashboardCanvas()
        self.setCentralWidget(self.canvas)
        self._build_toolbar()
        self._build_widget_dock()
        self._build_properties_dock()
        self._build_appearance_dock()
        self._build_layers_dock()
        self._build_pages_dock()
        self._configure_docks()
        self._apply_ui_polish()
        self._build_tray()
        self._retranslate_ui()
        self._fit_to_available_screen()

        self.canvas.selection_changed.connect(self._sync_properties)
        self.canvas.selection_changed.connect(lambda _item: self._refresh_layers())
        self.canvas.geometry_changed.connect(self._geometry_committed)
        self.canvas.background_geometry_changed.connect(self._background_geometry_committed)
        self.canvas.background_image_dropped.connect(self._set_dropped_background_image)
        self.statusBar().showMessage(self._t("Bereit · Live-Vorschau aktiv"))

        self._load_default_if_present()
        if not self.canvas.widget_items():
            self._apply_theme(DEFAULT_THEME_NAME, commit=False)
        self._history_json = self._profile_from_canvas().to_json()

        self.live_timer = QTimer(self)
        self.live_timer.timeout.connect(self._refresh_live_data)
        self.live_timer.start(1000)
        self._refresh_live_data()

        self.display_timer = QTimer(self)
        self.display_timer.setTimerType(Qt.PreciseTimer)
        self.display_timer.setInterval(250)
        self.display_timer.timeout.connect(self._push_display_frame)
        self._apply_performance_mode("Balanced", announce=False)

        self.page_cycle_timer = QTimer(self)
        self.page_cycle_timer.timeout.connect(self._next_dashboard_page)
        self._sync_page_cycle_timer()

        if not self.preferences.setup_completed:
            QTimer.singleShot(250, lambda: self._show_setup_assistant(first_run=True))

    def _t(self, text: str) -> str:
        return tr(text, self.language)

    def _retranslate_ui(self) -> None:
        retranslate_tree(self, self.language)
        if hasattr(self, "widget_list"):
            for index in range(self.widget_list.count()):
                item = self.widget_list.item(index)
                definition = widget_type(str(item.data(Qt.UserRole)))
                if definition is not None:
                    item.setText(self._t(definition.label))
        self.setWindowTitle("")
        if hasattr(self, "tray_icon"):
            self.tray_icon.setToolTip("OwnDash")

    def _open_settings(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(self._t("Einstellungen"))
        dialog.setModal(True)
        dialog.setMinimumWidth(420)

        outer = QVBoxLayout(dialog)
        form = QFormLayout()
        self._polish_form(form)

        language_combo = QComboBox(dialog)
        language_combo.addItem(self._t("Systemsprache"), "system")
        language_combo.addItem(self._t("Deutsch"), "de")
        language_combo.addItem(self._t("Englisch"), "en")
        language_index = language_combo.findData(self.preferences.language)
        language_combo.setCurrentIndex(max(0, language_index))

        appearance_combo = QComboBox(dialog)
        appearance_combo.addItem(self._t("System"), "system")
        appearance_combo.addItem(self._t("Dunkel"), "dark")
        appearance_combo.addItem(self._t("Hell"), "light")
        appearance_index = appearance_combo.findData(self.preferences.appearance)
        appearance_combo.setCurrentIndex(max(0, appearance_index))

        form.addRow(self._t("Sprache"), language_combo)
        form.addRow(self._t("Erscheinungsbild"), appearance_combo)
        outer.addLayout(form)

        hint = QLabel(self._t("Sprache und Erscheinungsbild werden sofort angewendet."), dialog)
        hint.setWordWrap(True)
        outer.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Cancel, dialog)
        apply_button = buttons.button(QDialogButtonBox.Apply)
        cancel_button = buttons.button(QDialogButtonBox.Cancel)
        if apply_button is not None:
            apply_button.setText(self._t("Übernehmen"))
        if cancel_button is not None:
            cancel_button.setText(self._t("Abbrechen"))
        if apply_button is not None:
            apply_button.clicked.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        outer.addWidget(buttons)

        if dialog.exec() != QDialog.Accepted:
            return

        self.preferences.language = str(language_combo.currentData())
        self.preferences.appearance = str(appearance_combo.currentData())
        save_preferences(self.preferences)

        self.language = resolved_language(self.preferences.language)
        apply_appearance(self.preferences.appearance, self._system_palette)
        self._apply_ui_polish()
        self._retranslate_ui()
        self.statusBar().showMessage(self._t("Bereit · Live-Vorschau aktiv"), 2500)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Projekt", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        save_action = QAction("Speichern", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._save)
        load_action = QAction("Öffnen", self)
        load_action.setShortcut(QKeySequence.Open)
        load_action.triggered.connect(self._open)
        delete_action = QAction("Löschen", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self._delete_selected)
        duplicate_action = QAction("Duplizieren", self)
        duplicate_action.setShortcut("Ctrl+D")
        duplicate_action.triggered.connect(self._duplicate_selected)
        copy_action = QAction("Kopieren", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self._copy_selected)
        paste_action = QAction("Einfügen", self)
        paste_action.setShortcut(QKeySequence.Paste)
        paste_action.triggered.connect(self._paste_widgets)
        front_action = QAction("Nach vorn", self)
        front_action.triggered.connect(lambda: self._change_layer("front"))
        back_action = QAction("Nach hinten", self)
        back_action.triggered.connect(lambda: self._change_layer("back"))
        zoom_out = QAction("−", self)
        zoom_out.setToolTip("Vorschau verkleinern")
        zoom_out.triggered.connect(lambda: self._zoom_canvas(0.85))
        zoom_reset = QAction("100 %", self)
        zoom_reset.triggered.connect(self._reset_zoom)
        zoom_in = QAction("+", self)
        zoom_in.setToolTip("Vorschau vergrößern")
        zoom_in.triggered.connect(lambda: self._zoom_canvas(1.15))
        undo_action = self.undo_stack.createUndoAction(self, "Rückgängig")
        undo_action.setShortcut(QKeySequence.Undo)
        redo_action = self.undo_stack.createRedoAction(self, "Wiederholen")
        redo_action.setShortcut(QKeySequence.Redo)
        align_left = QAction("Links ausrichten", self)
        align_left.triggered.connect(lambda: self._align_selected("left"))
        align_top = QAction("Oben ausrichten", self)
        align_top.triggered.connect(lambda: self._align_selected("top"))
        align_hcenter = QAction("Horizontal zentrieren", self)
        align_hcenter.triggered.connect(lambda: self._align_selected("hcenter"))
        align_vcenter = QAction("Vertikal zentrieren", self)
        align_vcenter.triggered.connect(lambda: self._align_selected("vcenter"))
        self.display_action = QAction("Display starten", self)
        self.display_action.setCheckable(True)
        self.display_action.toggled.connect(self._toggle_display_stream)

        # Keep the toolbar intentionally small. Less common editor commands live
        # in menus while their keyboard shortcuts continue to work normally.
        toolbar.addAction(save_action)
        toolbar.addAction(load_action)
        toolbar.addSeparator()
        toolbar.addAction(undo_action)
        toolbar.addAction(redo_action)
        toolbar.addSeparator()
        toolbar.addAction(zoom_out)
        toolbar.addAction(zoom_reset)
        toolbar.addAction(zoom_in)
        toolbar.addSeparator()
        toolbar.addAction(self.display_action)

        edit_menu = self.menuBar().addMenu("Bearbeiten")
        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(copy_action)
        edit_menu.addAction(paste_action)
        edit_menu.addAction(duplicate_action)
        edit_menu.addAction(delete_action)

        arrange_menu = self.menuBar().addMenu("Anordnen")
        arrange_menu.addAction(front_action)
        arrange_menu.addAction(back_action)
        arrange_menu.addSeparator()
        arrange_menu.addAction(align_left)
        arrange_menu.addAction(align_top)
        arrange_menu.addAction(align_hcenter)
        arrange_menu.addAction(align_vcenter)

        view_menu = self.menuBar().addMenu("Ansicht")
        view_menu.addAction(zoom_out)
        view_menu.addAction(zoom_reset)
        view_menu.addAction(zoom_in)
        view_menu.addSeparator()
        settings_action = QAction("Einstellungen …", self)
        settings_action.triggered.connect(self._open_settings)
        view_menu.addAction(settings_action)

        display_menu = self.menuBar().addMenu("Display")
        display_menu.addAction(self.display_action)
        display_select_action = QAction("Display auswählen …", self)
        display_select_action.triggered.connect(self._open_display_settings)
        display_menu.addAction(display_select_action)
        self.keep_running_action = QAction("Beim Schließen im Hintergrund weiterlaufen", self)
        self.keep_running_action.setCheckable(True)
        self.keep_running_action.setChecked(True)
        self.keep_running_action.toggled.connect(self._set_keep_running_on_close)
        display_menu.addAction(self.keep_running_action)
        display_menu.addSeparator()
        performance_menu = display_menu.addMenu("Performance")
        self.performance_action_group = QActionGroup(self)
        self.performance_action_group.setExclusive(True)
        self.performance_actions = {}
        for mode in ("Eco", "Balanced", "Smooth"):
            action = QAction(mode, self)
            action.setCheckable(True)
            action.setChecked(mode == self._performance_mode)
            action.triggered.connect(lambda checked=False, selected=mode: self._apply_performance_mode(selected) if checked else None)
            self.performance_action_group.addAction(action)
            performance_menu.addAction(action)
            self.performance_actions[mode] = action

        help_menu = self.menuBar().addMenu("Hilfe")

        help_action = QAction("OwnDash-Hilfe …", self)
        help_action.triggered.connect(self._show_help_dialog)
        help_menu.addAction(help_action)

        setup_action = QAction("Systemprüfung …", self)
        setup_action.triggered.connect(lambda: self._show_setup_assistant(first_run=False))
        help_menu.addAction(setup_action)

        diagnostics_action = QAction("System- und Sensorinformationen …", self)
        diagnostics_action.triggered.connect(self._show_sensor_diagnostics)
        help_menu.addAction(diagnostics_action)
        help_menu.addSeparator()

        about_action = QAction("Über OwnDash …", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)
        changelog_action = QAction("Änderungsprotokoll …", self)
        changelog_action.triggered.connect(self._show_changelog_dialog)
        help_menu.addAction(changelog_action)

        github_action = QAction("OwnDash auf GitHub", self)
        github_action.triggered.connect(self._open_project_page)
        help_menu.addAction(github_action)

        help_menu.addSeparator()
        bug_action = QAction("Fehler melden …", self)
        bug_action.triggered.connect(self._report_bug)
        help_menu.addAction(bug_action)

    def _show_setup_assistant(self, first_run: bool = False) -> None:
        capabilities = system_capabilities()
        required = capabilities["required"]
        optional = capabilities["optional"]
        display_caps = capabilities["display"]
        diag = capabilities["diagnostics"]

        dialog = QDialog(self)
        dialog.setWindowTitle(self._t("Willkommen bei OwnDash") if first_run else self._t("OwnDash-Systemprüfung"))
        dialog.setMinimumSize(720, 680)
        dialog.resize(800, 760)

        outer = QVBoxLayout(dialog)
        outer.setContentsMargins(22, 20, 22, 18)
        outer.setSpacing(12)

        title = QLabel(
            f"<h2>{self._t('Willkommen bei OwnDash') if first_run else self._t('OwnDash-Systemprüfung')}</h2>",
            dialog,
        )
        title.setTextFormat(Qt.RichText)
        outer.addWidget(title)

        intro = QLabel(
            self._t("OwnDash prüft automatisch, ob dein Linux-System bereit ist. Du musst dafür keine technischen Einstellungen kennen."),
            dialog,
        )
        intro.setWordWrap(True)
        outer.addWidget(intro)

        palette_dark = dialog.palette().color(QPalette.Window).lightness() < 128
        ok_color = "#43d17a" if palette_dark else "#148a45"
        warning_color = "#f2bd4b" if palette_dark else "#9a6500"
        muted_color = "#aeb7c4" if palette_dark else "#5d6673"

        row_height = 32

        def status(available: bool, optional_item: bool = False) -> QLabel:
            if available:
                label = QLabel("✓  " + self._t("Bereit"), dialog)
                label.setStyleSheet(f"font-weight: 700; color: {ok_color};")
            elif optional_item:
                label = QLabel("○  " + self._t("Optional / nicht verfügbar"), dialog)
                label.setStyleSheet(f"font-weight: 600; color: {muted_color};")
            else:
                label = QLabel("!  " + self._t("Aufmerksamkeit erforderlich"), dialog)
                label.setStyleSheet(f"font-weight: 700; color: {warning_color};")
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            label.setMinimumWidth(220)
            label.setFixedHeight(row_height)
            return label

        def section(title_text: str, rows: list[tuple[str, bool, bool]]) -> QGroupBox:
            box = QGroupBox(title_text, dialog)
            # Do not let Qt compress rows below their readable height when the
            # desktop uses a larger font or display scaling.
            box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            grid = QGridLayout(box)
            grid.setContentsMargins(16, 18, 16, 14)
            grid.setHorizontalSpacing(24)
            grid.setVerticalSpacing(4)
            grid.setColumnStretch(0, 1)
            grid.setColumnMinimumWidth(1, 220)
            for row, (label_text, available, optional_item) in enumerate(rows):
                name = QLabel(label_text, dialog)
                name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                name.setFixedHeight(row_height)
                grid.addWidget(name, row, 0)
                grid.addWidget(status(available, optional_item), row, 1)
                grid.setRowMinimumHeight(row, row_height)
                grid.setRowStretch(row, 0)
            box.setMinimumHeight(54 + len(rows) * row_height)
            return box

        sections_widget = QWidget(dialog)
        sections_layout = QVBoxLayout(sections_widget)
        sections_layout.setContentsMargins(0, 0, 0, 0)
        sections_layout.setSpacing(12)

        sections_layout.addWidget(section(self._t("Grundvoraussetzungen"), [
            (self._t("Linux-System"), bool(required["linux"]), False),
            (self._t("Grafische Oberfläche (Wayland / X11)"), bool(required["graphical_session"]), False),
            (self._t("Linux-Systeminformationen (/proc)"), bool(required["proc"]), False),
            (self._t("Linux-Hardwareinformationen (/sys)"), bool(required["sys"]), False),
        ]))

        sections_layout.addWidget(section(self._t("Hardware und Sensoren"), [
            (self._t("CPU-Auslastung"), bool(diag["cpu"]["usage"]), True),
            (self._t("CPU-Temperatur"), bool(diag["cpu"]["temperature"]), True),
            (self._t("CPU-Leistung"), bool(diag["cpu"]["power"]), True),
            (self._t("GPU-Auslastung"), bool(diag["gpu"]["usage"]), True),
            (self._t("GPU-Temperatur"), bool(diag["gpu"]["temperature"]), True),
            (self._t("GPU-Leistung"), bool(diag["gpu"]["power"]), True),
        ]))

        screen_count = len(QApplication.instance().screens()) if QApplication.instance() is not None else 0
        display_rows = [
            (self._t("Standard-Monitor-Ausgabe"), screen_count > 0, False),
            (
                self._t("ArtInChip / VSDISPLAY verbunden"),
                bool(display_caps["artinchip_connected"]),
                True,
            ),
        ]
        if display_caps["artinchip_connected"]:
            display_rows.append(
                (
                    self._t("USB-Zugriffsberechtigung"),
                    bool(display_caps["artinchip_accessible"]),
                    True,
                )
            )
        sections_layout.addWidget(section(self._t("Display-Ausgabe"), display_rows))

        if (
            display_caps["artinchip_connected"]
            and not display_caps["artinchip_accessible"]
            and display_caps["graphical_usb_setup"]
        ):
            usb_box = QHBoxLayout()
            usb_hint = QLabel(
                self._t("Das USB-Display wurde erkannt, OwnDash benötigt aber noch Zugriffsrechte."),
                dialog,
            )
            usb_hint.setWordWrap(True)
            usb_box.addWidget(usb_hint, 1)
            usb_setup_button = QPushButton(self._t("USB-Zugriff einrichten"), dialog)

            def setup_usb_access() -> None:
                usb_setup_button.setEnabled(False)
                ok, message = install_udev_rule()
                if ok:
                    QMessageBox.information(dialog, self._t("USB-Zugriff"), self._t(message))
                    dialog.accept()
                    QTimer.singleShot(250, lambda: self._show_setup_assistant(first_run=False))
                else:
                    QMessageBox.warning(dialog, self._t("USB-Zugriff"), self._t(message))
                    usb_setup_button.setEnabled(True)

            usb_setup_button.clicked.connect(setup_usb_access)
            usb_box.addWidget(usb_setup_button)
            sections_layout.addLayout(usb_box)

        optional_rows = [
            (self._t("Sensor-Schnittstelle (hwmon)"), bool(optional["hwmon"]), True),
            (self._t("Leistungs-Schnittstelle (powercap)"), bool(optional["powercap"]), True),
            (self._t("Lesbare PCI-Hardwarenamen (lspci)"), bool(optional["lspci"]), True),
        ]
        if str(diag["gpu"]["driver"]).lower() == "nvidia":
            optional_rows.append((self._t("NVIDIA-Sensordaten (nvidia-smi)"), bool(optional["nvidia_smi"]), True))
        sections_layout.addWidget(section(self._t("Optionale Erweiterungen"), optional_rows))
        sections_layout.addStretch(1)

        sections_scroll = QScrollArea(dialog)
        sections_scroll.setWidgetResizable(True)
        sections_scroll.setFrameShape(QFrame.NoFrame)
        sections_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sections_scroll.setWidget(sections_widget)
        outer.addWidget(sections_scroll, 1)

        required_ok = all(bool(value) for value in required.values())
        summary = QLabel(dialog)
        summary.setWordWrap(True)
        if required_ok:
            summary.setText("✓  " + self._t("OwnDash ist auf diesem System grundsätzlich einsatzbereit. Nicht verfügbare optionale Sensoren schränken nur einzelne Messwerte ein."))
            summary.setStyleSheet(f"font-weight: 600; color: {ok_color};")
        else:
            summary.setText("!  " + self._t("Mindestens eine Grundvoraussetzung fehlt. OwnDash kann auf diesem System möglicherweise nicht vollständig ausgeführt werden."))
            summary.setStyleSheet(f"font-weight: 600; color: {warning_color};")
        outer.addWidget(summary)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, dialog)
        close_button = buttons.button(QDialogButtonBox.Close)
        if close_button is not None:
            close_button.setText(self._t("Schließen"))
        if first_run:
            continue_button = buttons.addButton(self._t("OwnDash starten"), QDialogButtonBox.AcceptRole)
            continue_button.clicked.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        outer.addWidget(buttons)

        dialog.exec()

        if first_run:
            self.preferences.setup_completed = True
            save_preferences(self.preferences)

    def _show_sensor_diagnostics(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(self._t("System- und Sensorinformationen"))
        dialog.setMinimumSize(700, 610)
        dialog.resize(760, 660)

        outer = QVBoxLayout(dialog)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(14)

        intro = QLabel(
            self._t("OwnDash erkennt Sensoren dynamisch. Ein grünes Häkchen bedeutet, dass der Wert auf diesem System verfügbar ist."),
            dialog,
        )
        intro.setWordWrap(True)
        outer.addWidget(intro)

        # Diagnostics cards use the active Qt palette so the same dialog keeps
        # clear contrast in OwnDash Dark, OwnDash Light and native System mode.
        window_color = dialog.palette().color(QPalette.Window)
        dark_ui = window_color.lightness() < 128
        card_border = "#596575" if dark_ui else "#aab3c0"
        card_background = "#20262e" if dark_ui else "#fbfcfe"
        card_title = "#f1f4f8" if dark_ui else "#20252c"
        status_green = "#43d17a" if dark_ui else "#148a45"
        muted_text = "#aeb7c4" if dark_ui else "#5d6673"

        card_style = (
            "QGroupBox {"
            f"  border: 1px solid {card_border};"
            "  border-radius: 9px;"
            "  margin-top: 12px;"
            "  padding-top: 8px;"
            f"  background-color: {card_background};"
            "}"
            "QGroupBox::title {"
            "  subcontrol-origin: margin;"
            "  subcontrol-position: top left;"
            "  left: 12px;"
            "  padding: 0 6px;"
            f"  color: {card_title};"
            f"  background-color: {card_background};"
            "  font-weight: 600;"
            "}"
        )

        info = self.sensor_provider.diagnostics()

        def value_label(text: str) -> QLabel:
            label = QLabel(text, dialog)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            return label

        def status_label(available: bool) -> QLabel:
            label = QLabel("✓" if available else "—", dialog)
            label.setAlignment(Qt.AlignCenter)
            label.setFixedWidth(34)
            if available:
                label.setStyleSheet(
                    f"font-weight: 700; font-size: 18px; color: {status_green};"
                )
                label.setToolTip(self._t("Verfügbar"))
            else:
                label.setStyleSheet(
                    f"font-weight: 600; color: {muted_text};"
                )
                label.setToolTip(self._t("Nicht verfügbar"))
            return label

        def add_row(grid: QGridLayout, row: int, title: str, value: str | None = None, available: bool | None = None) -> None:
            name = QLabel(title, dialog)
            name.setMinimumWidth(145)
            grid.addWidget(name, row, 0)
            if value is not None:
                grid.addWidget(value_label(value), row, 1)
            else:
                grid.addWidget(QLabel("", dialog), row, 1)
            if available is not None:
                grid.addWidget(status_label(available), row, 2)

        system_box = QGroupBox(self._t("System"), dialog)
        system_box.setStyleSheet(card_style)
        system_grid = QGridLayout(system_box)
        system_grid.setContentsMargins(16, 16, 16, 16)
        system_grid.setHorizontalSpacing(22)
        system_grid.setVerticalSpacing(9)
        system_grid.setColumnStretch(1, 1)
        add_row(system_grid, 0, self._t("Distribution"), str(info["system"]["distribution"]))
        add_row(system_grid, 1, self._t("Kernel"), str(info["system"]["kernel"]))
        add_row(system_grid, 2, self._t("Desktop"), str(info["system"]["desktop"]))
        add_row(system_grid, 3, self._t("Sitzung"), str(info["system"]["session"]))
        outer.addWidget(system_box)

        hardware_row = QHBoxLayout()
        hardware_row.setSpacing(14)

        cpu_box = QGroupBox("CPU", dialog)
        cpu_box.setStyleSheet(card_style)
        cpu_grid = QGridLayout(cpu_box)
        cpu_grid.setContentsMargins(16, 16, 16, 16)
        cpu_grid.setHorizontalSpacing(18)
        cpu_grid.setVerticalSpacing(9)
        cpu_grid.setColumnStretch(1, 1)
        cpu_name = value_label(str(info["cpu"]["name"]))
        cpu_name.setWordWrap(True)
        cpu_grid.addWidget(cpu_name, 0, 0, 1, 3)
        add_row(cpu_grid, 1, self._t("Auslastung"), available=bool(info["cpu"]["usage"]))
        add_row(cpu_grid, 2, self._t("Temperatur"), available=bool(info["cpu"]["temperature"]))
        add_row(cpu_grid, 3, self._t("Leistung"), available=bool(info["cpu"]["power"]))
        hardware_row.addWidget(cpu_box, 1)

        gpu_box = QGroupBox("GPU", dialog)
        gpu_box.setStyleSheet(card_style)
        gpu_grid = QGridLayout(gpu_box)
        gpu_grid.setContentsMargins(16, 16, 16, 16)
        gpu_grid.setHorizontalSpacing(18)
        gpu_grid.setVerticalSpacing(9)
        gpu_grid.setColumnStretch(1, 1)
        gpu_name = value_label(str(info["gpu"]["name"]))
        gpu_name.setWordWrap(True)
        gpu_grid.addWidget(gpu_name, 0, 0, 1, 3)
        add_row(gpu_grid, 1, self._t("Treiber"), str(info["gpu"]["driver"]))
        add_row(gpu_grid, 2, self._t("Auslastung"), available=bool(info["gpu"]["usage"]))
        add_row(gpu_grid, 3, self._t("Temperatur"), available=bool(info["gpu"]["temperature"]))
        add_row(gpu_grid, 4, self._t("Leistung"), available=bool(info["gpu"]["power"]))
        hardware_row.addWidget(gpu_box, 1)

        outer.addLayout(hardware_row)

        services_box = QGroupBox(self._t("Weitere Systemwerte"), dialog)
        services_box.setStyleSheet(card_style)
        services_grid = QGridLayout(services_box)
        services_grid.setContentsMargins(16, 16, 16, 16)
        services_grid.setHorizontalSpacing(22)
        services_grid.setVerticalSpacing(9)
        services_grid.setColumnStretch(1, 1)
        add_row(services_grid, 0, self._t("Arbeitsspeicher"), available=bool(info["memory"]))
        add_row(services_grid, 1, self._t("Speicher"), available=bool(info["storage"]))
        add_row(services_grid, 2, self._t("Netzwerk"), available=bool(info["network"]))
        outer.addWidget(services_box)

        hint = QLabel(
            self._t("Fehlende Sensoren sind kein Fehler: Welche Werte verfügbar sind, hängt von Hardware, Kernel und Treiber ab."),
            dialog,
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {muted_text};")
        outer.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, dialog)
        close_button = buttons.button(QDialogButtonBox.Close)
        if close_button is not None:
            close_button.setText(self._t("Schließen"))
        buttons.rejected.connect(dialog.reject)
        outer.addWidget(buttons)
        dialog.exec()

    def _show_help_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(self._t("OwnDash-Hilfe"))
        dialog.setMinimumSize(760, 620)
        dialog.resize(820, 680)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel(f"<h2>{self._t('OwnDash-Hilfe')}</h2>", dialog)
        title.setTextFormat(Qt.RichText)
        layout.addWidget(title)

        browser = QTextBrowser(dialog)
        browser.setOpenExternalLinks(True)

        if self.language == "de":
            browser.setHtml(f"""
            <h3>Erste Schritte</h3>
            <ol>
              <li>Wähle unter <b>Display</b> das gewünschte Ausgabegerät.</li>
              <li>Erstelle ein Dashboard oder lade eine Vorlage.</li>
              <li>Füge Widgets per Doppelklick oder über <b>Zum Dashboard hinzufügen</b> hinzu.</li>
              <li>Passe Layout, Design, Datenquelle und Animationen an.</li>
              <li>Klicke auf <b>Display starten</b>, um das Dashboard auszugeben.</li>
            </ol>

            <h3>Displays und Ausgabe</h3>
            <p><b>VSDISPLAY / ArtInChip:</b> Unterstützte ArtInChip-USB-Displays können direkt von OwnDash angesteuert werden.</p>
            <p><b>Standardmonitor:</b> PC-Gehäusedisplays, HDMI-/DisplayPort-/USB-C-Monitore und andere von Linux als Monitor erkannte Displays können über die Standardmonitor-Ausgabe verwendet werden.</p>
            <p>Prüfe vor dem Übernehmen immer, dass wirklich das gewünschte Zusatzdisplay ausgewählt ist. OwnDash bietet eine Rückgängig-/Sicherheitsfunktion für versehentliche Displaywechsel.</p>

            <h3>Dashboards und Widgets</h3>
            <p>OwnDash unterstützt mehrere Dashboard-Seiten, Vorlagen, Ebenen, Raster, Ausrichtung, Hintergründe sowie verschiedene Sensor-, Diagramm- und Tacho-Widgets. Widgets lassen sich verschieben, skalieren, duplizieren und aneinander ausrichten.</p>

            <h3>Sensoren</h3>
            <p>OwnDash erkennt Sensoren zur Laufzeit und ist nicht auf Bazzite oder KDE festgelegt. CPU, RAM, Speicher und Netzwerk verwenden allgemeine Linux-Schnittstellen. Temperatur- und Leistungswerte werden dynamisch über sysfs/hwmon bzw. powercap erkannt. AMD- und Intel-GPUs werden über Linux-Schnittstellen erkannt; bei NVIDIA kann OwnDash zusätzlich <code>nvidia-smi</code> verwenden, wenn es installiert ist.</p>
            <p>Welche Werte verfügbar sind, hängt von Kernel, Treiber und Hardware ab. Fehlende Sensoren werden als nicht verfügbar behandelt und führen nicht zu einem Programmfehler. Unter <b>Hilfe → System- und Sensorinformationen …</b> siehst du, was OwnDash auf deinem Rechner erkannt hat.</p>

            <h3>Hintergründe und Animationen</h3>
            <p>Eigene Bilder können als Dashboard-Hintergrund verwendet und positioniert, skaliert und in der Deckkraft angepasst werden. Zusätzlich stehen animierte Hintergründe und Widget-Effekte zur Verfügung. Der Leistungsmodus bestimmt den Kompromiss zwischen flüssiger Darstellung und CPU-Last.</p>

            <h3>Mehrere Dashboards</h3>
            <p>Im Reiter <b>Dashboards</b> kannst du Seiten erstellen, duplizieren, umbenennen und löschen. Optional kann OwnDash automatisch zwischen ihnen wechseln.</p>

            <h3>FAQ</h3>
            <p><b>Mein Display bleibt schwarz oder wird nicht erkannt.</b><br>
            Prüfe Verbindung und Stromversorgung. Bei einem ArtInChip-USB-Display darf kein anderes Programm gleichzeitig auf das Gerät zugreifen.</p>

            <p><b>Warum erscheint mein Hauptmonitor in der Displayauswahl?</b><br>
            Die Standardmonitor-Ausgabe zeigt die von Linux erkannten Bildschirme. Wähle dort ausschließlich das gewünschte Zusatzdisplay.</p>

            <p><b>Warum sind manche Sensorwerte nicht verfügbar?</b><br>
            Nicht jede Hardware stellt dieselben Sensoren unter Linux bereit. OwnDash zeigt nur Werte an, die es auf dem jeweiligen System ermitteln kann.</p>

            <p><b>Warum steigt die CPU-Auslastung bei Animationen?</b><br>
            Animierte Widgets und Hintergründe müssen häufiger neu gerendert und übertragen werden. Nutze bei Bedarf den Leistungsmodus <b>Eco</b>.</p>

            <p><b>Wo kann ich einen Fehler melden?</b><br>
            Nutze <b>Hilfe → Fehler melden …</b>. OwnDash öffnet eine vorbereitete GitHub-Fehlermeldung.</p>

            <h3>Weitere Informationen</h3>
            <p><a href="{GITHUB_URL}">OwnDash-Projektseite auf GitHub</a></p>
            """)
        else:
            browser.setHtml(f"""
            <h3>Getting started</h3>
            <ol>
              <li>Select the desired output device from the <b>Display</b> menu.</li>
              <li>Create a dashboard or load a template.</li>
              <li>Add widgets by double-clicking them or using <b>Add to dashboard</b>.</li>
              <li>Adjust layout, design, data source and animations.</li>
              <li>Click <b>Start display</b> to output the dashboard.</li>
            </ol>

            <h3>Displays and output</h3>
            <p><b>VSDISPLAY / ArtInChip:</b> Supported ArtInChip USB displays can be driven directly by OwnDash.</p>
            <p><b>Standard monitor:</b> PC case displays, HDMI/DisplayPort/USB-C monitors and other displays recognized by Linux as monitors can use the standard monitor output.</p>
            <p>Before applying a display change, always verify that the intended secondary display is selected. OwnDash provides an undo/safety mechanism for accidental display changes.</p>

            <h3>Dashboards and widgets</h3>
            <p>OwnDash supports multiple dashboard pages, templates, layers, grids, alignment, backgrounds and several sensor, chart and gauge widgets. Widgets can be moved, resized, duplicated and aligned.</p>

            <h3>Sensors</h3>
            <p>OwnDash detects sensors at runtime and is not tied to Bazzite or KDE. CPU, memory, storage and network use common Linux interfaces. Temperature and power readings are discovered dynamically through sysfs/hwmon and powercap. AMD and Intel GPUs use Linux interfaces; for NVIDIA, OwnDash can additionally use <code>nvidia-smi</code> when it is installed.</p>
            <p>Availability depends on the kernel, driver and hardware. Missing sensors are treated as unavailable and do not break the application. Open <b>Help → System and sensor information …</b> to see what OwnDash detected on your system.</p>

            <h3>Backgrounds and animations</h3>
            <p>Custom images can be used as dashboard backgrounds and positioned, scaled and adjusted for opacity. Animated backgrounds and widget effects are also available. The performance mode controls the balance between smooth motion and CPU usage.</p>

            <h3>Multiple dashboards</h3>
            <p>Use the <b>Dashboards</b> tab to create, duplicate, rename and delete pages. OwnDash can optionally cycle through them automatically.</p>

            <h3>FAQ</h3>
            <p><b>My display stays black or is not detected.</b><br>
            Check its connection and power. For an ArtInChip USB display, make sure no other application is accessing the device at the same time.</p>

            <p><b>Why does my main monitor appear in the display list?</b><br>
            Standard monitor output lists screens detected by Linux. Select only the intended secondary display.</p>

            <p><b>Why are some sensor readings unavailable?</b><br>
            Not all hardware exposes the same sensors under Linux. OwnDash only displays readings it can obtain from the current system.</p>

            <p><b>Why does CPU usage increase with animations?</b><br>
            Animated widgets and backgrounds need to be rendered and transmitted more frequently. Use the <b>Eco</b> performance mode if needed.</p>

            <p><b>Where can I report a bug?</b><br>
            Use <b>Help → Report a bug …</b>. OwnDash opens a prepared GitHub issue.</p>

            <h3>More information</h3>
            <p><a href="{GITHUB_URL}">OwnDash project page on GitHub</a></p>
            """)

        layout.addWidget(browser, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, dialog)
        close_button = buttons.button(QDialogButtonBox.Close)
        if close_button is not None:
            close_button.setText(self._t("Schließen"))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.exec()

    def _show_about_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(self._t("Über OwnDash"))
        dialog.setMinimumSize(560, 480)
        layout = QVBoxLayout(dialog)

        with app_icon_path() as icon_path:
            logo = QLabel(dialog)
            pixmap = self.windowIcon().pixmap(72, 72)
            logo.setPixmap(pixmap)
            logo.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo)

        title = QLabel(f"<h2>{APP_NAME}</h2><div>{__version__}</div>", dialog)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        description = QLabel(
            self._t("Ein freier Dashboard-Editor für PC-Gehäusedisplays unter Linux."),
            dialog,
        )
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        layout.addWidget(description)

        details = QLabel(
            f"<b>{self._t('Entwickler / Copyright')}:</b> Markus Rosinski © 2026<br>"
            f"<b>{self._t('Lizenz')}:</b> MIT License<br>"
            f"<b>{self._t('Projektstatus')}:</b> Beta",
            dialog,
        )
        details.setTextFormat(Qt.RichText)
        details.setAlignment(Qt.AlignCenter)
        layout.addWidget(details)

        project_link = QLabel(
            f"<b>{self._t('Projektseite')}:</b> <a href='{GITHUB_URL}'>GitHub</a>",
            dialog,
        )
        project_link.setTextFormat(Qt.RichText)
        project_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        project_link.setOpenExternalLinks(True)
        project_link.setAlignment(Qt.AlignCenter)
        layout.addWidget(project_link)

        note = QLabel(
            self._t("Hinweise zu verwendeten Open-Source-Komponenten befinden sich in THIRD_PARTY.md."),
            dialog,
        )
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignCenter)
        note.setMinimumHeight(64)
        layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, dialog)
        close_button = buttons.button(QDialogButtonBox.Close)
        if close_button is not None:
            close_button.setText(self._t("Schließen"))
        buttons.rejected.connect(dialog.reject)
        buttons.clicked.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def _open_project_page(self) -> None:
        if not webbrowser.open(GITHUB_URL):
            QMessageBox.information(
                self,
                self._t("Projektseite"),
                self._t("Der Browser konnte nicht geöffnet werden. Öffne bitte die OwnDash-Projektseite auf GitHub."),
            )

    def _show_changelog_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(self._t("Änderungsprotokoll"))
        dialog.resize(720, 560)
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser(dialog)
        changelog = Path(__file__).resolve().parents[3] / "CHANGELOG.md"
        try:
            browser.setMarkdown(changelog.read_text(encoding="utf-8"))
        except OSError:
            browser.setPlainText(self._t("Das Änderungsprotokoll konnte nicht geladen werden."))
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, dialog)
        close_button = buttons.button(QDialogButtonBox.Close)
        if close_button is not None:
            close_button.setText(self._t("Schließen"))
        buttons.rejected.connect(dialog.reject)
        buttons.clicked.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def _report_bug(self) -> None:
        system = platform.system()
        release = platform.release()
        version = __version__
        diagnostics = self.sensor_provider.diagnostics_text(self.language)
        title = f"[Bug] OwnDash {version}: "
        if self.language == "de":
            body = (
                "## Beschreibung\n"
                "<!-- Was ist passiert? -->\n\n"
                "## Schritte zum Reproduzieren\n"
                "1. \n"
                "2. \n"
                "3. \n\n"
                "## Erwartetes Verhalten\n"
                "<!-- Was hätte stattdessen passieren sollen? -->\n\n"
                "## Systeminformationen\n"
                f"- OwnDash: {version}\n"
                f"- OS / Kernel: {system} {release}\n"
                "- Linux-Distribution / Desktop: \n"
                "- Display-Modell / Verbindung: \n\n"
                "## OwnDash Sensor-Diagnose\n"
                "```text\n"
                f"{diagnostics}\n"
                "```\n\n"
                "## Zusätzliche Informationen\n"
                "<!-- Screenshots, Logs oder weitere hilfreiche Angaben. -->\n"
            )
        else:
            body = (
                "## Description\n"
                "<!-- What happened? -->\n\n"
                "## Steps to reproduce\n"
                "1. \n"
                "2. \n"
                "3. \n\n"
                "## Expected behavior\n"
                "<!-- What did you expect to happen? -->\n\n"
                "## System information\n"
                f"- OwnDash: {version}\n"
                f"- OS / kernel: {system} {release}\n"
                "- Linux distribution / desktop: \n"
                "- Display model / connection: \n\n"
                "## OwnDash sensor diagnostics\n"
                "```text\n"
                f"{diagnostics}\n"
                "```\n\n"
                "## Additional context\n"
                "<!-- Screenshots, logs or anything else that may help. -->\n"
            )
        from urllib.parse import urlencode
        url = f"{GITHUB_ISSUES_URL}/new?" + urlencode(
            {"title": title, "body": body}
        )
        if not webbrowser.open(url):
            QMessageBox.information(
                self,
                self._t("Fehler melden"),
                self._t("Der Browser konnte nicht geöffnet werden. Öffne bitte den GitHub-Issue-Tracker des Projekts."),
            )

    def _available_screen_devices(self) -> list[tuple[str, str, int, int, object]]:
        devices = []
        app = QApplication.instance()
        if app is None:
            return devices
        for index, screen in enumerate(app.screens()):
            geometry = screen.geometry()
            device_id = f"screen:{index}:{screen.name()}"
            devices.append((device_id, screen.name() or f"Monitor {index + 1}", geometry.width(), geometry.height(), geometry))
        return devices

    def _open_display_settings(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(self._t("Display auswählen"))
        dialog.setModal(True)
        dialog.setMinimumWidth(460)
        outer = QVBoxLayout(dialog)
        form = QFormLayout()
        self._polish_form(form)

        backend_combo = QComboBox(dialog)
        backend_combo.addItem("ArtInChip USB / VSDISPLAY", "aic_usb")
        backend_combo.addItem(self._t("Standard-Monitor (HDMI/DP/USB-C)"), "screen")
        backend_combo.setCurrentIndex(max(0, backend_combo.findData(self.display_backend_key)))

        device_combo = QComboBox(dialog)
        rotation_combo = QComboBox(dialog)
        for rotation in (0, 90, 180, 270):
            rotation_combo.addItem(f"{rotation}°", rotation)

        profile = self._profile_from_canvas()
        rotation_combo.setCurrentIndex(max(0, rotation_combo.findData(profile.rotation)))

        def populate_devices() -> None:
            device_combo.clear()
            if backend_combo.currentData() == "aic_usb":
                device_combo.addItem(self._t("Automatisch erkennen"), "auto")
            else:
                for device_id, name, width, height, _geometry in self._available_screen_devices():
                    device_combo.addItem(f"{name} · {width}×{height}", device_id)
            idx = device_combo.findData(self.display_device_id)
            if idx >= 0:
                device_combo.setCurrentIndex(idx)

        backend_combo.currentIndexChanged.connect(populate_devices)
        populate_devices()

        form.addRow(self._t("Ausgabe"), backend_combo)
        form.addRow(self._t("Gerät"), device_combo)
        form.addRow(self._t("Rotation"), rotation_combo)
        outer.addLayout(form)

        hint = QLabel(self._t("Normale Linux-Monitore funktionieren direkt. Proprietäre USB-Displays benötigen ein passendes OwnDash-Backend."), dialog)
        hint.setWordWrap(True)
        outer.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Cancel, dialog)
        buttons.button(QDialogButtonBox.Apply).setText(self._t("Übernehmen"))
        buttons.button(QDialogButtonBox.Cancel).setText(self._t("Abbrechen"))
        buttons.button(QDialogButtonBox.Apply).clicked.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        outer.addWidget(buttons)

        if dialog.exec() != QDialog.Accepted:
            return

        before = self._profile_from_canvas().to_json()
        new_backend = str(backend_combo.currentData())
        new_device = str(device_combo.currentData() or "auto")
        new_rotation = int(rotation_combo.currentData())

        old_backend = self.display_backend_key
        old_device = self.display_device_id
        old_rotation = int(getattr(self, "_display_rotation", 270))
        target_changed = (
            new_backend != old_backend
            or new_device != old_device
            or new_rotation != old_rotation
        )

        # Never resize/reconfigure the logical canvas while the old backend is
        # still streaming. Doing that can send frames with the new target size
        # to the previous USB display and cause visible flicker/corruption.
        was_running = bool(
            self.display_connected
            or (self.display_streamer is not None and self.display_streamer.running)
        )
        if target_changed and was_running:
            self._stop_display_stream()

        self.display_backend_key = new_backend
        self.display_device_id = new_device
        self._set_profile_display_geometry(new_rotation)
        self._commit_history(before, "Display ändern")

        if target_changed and was_running:
            QTimer.singleShot(0, self._start_display_stream)
            self.statusBar().showMessage(self._t("Display wird auf die neue Ausgabe umgeschaltet …"), 3000)
        else:
            self.statusBar().showMessage(self._t("Display-Konfiguration aktualisiert"), 2500)

    def _set_profile_display_geometry(self, rotation: int) -> None:
        if self.display_backend_key == "screen":
            selected = next((d for d in self._available_screen_devices() if d[0] == self.display_device_id), None)
            if selected is not None:
                _id, _name, width, height, _geometry = selected
                logical_w, logical_h = logical_size(width, height, rotation)
                self._resize_dashboard_canvas(logical_w, logical_h, scale_widgets=True)
        self._display_rotation = rotation

    def _resize_dashboard_canvas(self, width: int, height: int, *, scale_widgets: bool) -> None:
        self.canvas.set_canvas_size(width, height, scale_widgets=scale_widgets)
        self.x_spin.setRange(0, width)
        self.y_spin.setRange(0, height)
        self.w_spin.setRange(40, width)
        self.h_spin.setRange(40, height)

    def _build_tray(self) -> None:
        """Keep live dashboards moving after the editor window is closed."""
        self.tray_icon = QSystemTrayIcon(QApplication.instance().windowIcon(), self)
        tray_menu = QMenu(self)
        show_action = tray_menu.addAction("OwnDash öffnen")
        show_action.triggered.connect(self._show_from_tray)
        self.tray_display_action = tray_menu.addAction("Display stoppen")
        self.tray_display_action.triggered.connect(self._stop_display_stream)
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("OwnDash vollständig beenden")
        quit_action.triggered.connect(self._quit_from_tray)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("OwnDash")
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()

    def _set_keep_running_on_close(self, enabled: bool) -> None:
        self.keep_display_running_on_close = bool(enabled)

    def _tray_activated(self, reason) -> None:  # noqa: ANN001
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _quit_from_tray(self) -> None:
        self._force_quit = True
        self._stop_display_stream()
        self.tray_icon.hide()
        QApplication.quit()

    def _build_widget_dock(self) -> None:
        dock = QDockWidget("Widgets", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        self.widget_list = WidgetPalette()
        self.widget_list.setDragEnabled(True)
        for widget_type in DEFAULT_WIDGETS:
            item = QListWidgetItem(widget_type.label)
            item.setData(Qt.UserRole, widget_type.key)
            self.widget_list.addItem(item)
        self.widget_list.itemDoubleClicked.connect(lambda _: self._add_selected_widget())
        self.template_combo = QComboBox()
        self.template_combo.addItems(template_names())
        self._polish_field(self.template_combo)
        template_button = QPushButton("Vorlage laden")
        template_button.clicked.connect(self._load_template)
        add_button = QPushButton("Zum Dashboard hinzufügen")
        add_button.clicked.connect(self._add_selected_widget)
        layout.addWidget(QLabel("Widget ziehen oder doppelklicken"))
        layout.addWidget(self.widget_list)
        layout.addWidget(add_button)
        layout.addWidget(QLabel("Dashboard-Vorlagen"))
        layout.addWidget(self.template_combo)
        layout.addWidget(template_button)
        body.setMinimumSize(0, 0)
        body.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        dock.setMinimumSize(180, 120)
        dock.setWidget(body)
        self.widget_dock = dock
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

    def _build_properties_dock(self) -> None:
        dock = QDockWidget("Layout", self)
        body = QWidget()
        form = QFormLayout(body)
        self._polish_form(form)
        self.x_spin = FocusSafeSpinBox()
        self.x_spin.setRange(0, 480)
        self.y_spin = FocusSafeSpinBox()
        self.y_spin.setRange(0, 1920)
        self.w_spin = FocusSafeSpinBox()
        self.w_spin.setRange(40, 480)
        self.h_spin = FocusSafeSpinBox()
        self.h_spin.setRange(40, 1920)
        form.addRow("X", self.x_spin)
        form.addRow("Y", self.y_spin)
        form.addRow("Breite", self.w_spin)
        form.addRow("Höhe", self.h_spin)
        form.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        for spin in (self.x_spin, self.y_spin, self.w_spin, self.h_spin):
            self._configure_spinbox(spin)
            # Arrow buttons/keys update the widget immediately.  Keyboard tracking
            # is disabled, so typed multi-digit values are only committed once
            # Enter is pressed or the editor loses focus instead of being applied
            # digit-by-digit.
            spin.valueChanged.connect(self._apply_geometry_properties)

        self.grid_check = QCheckBox("Raster anzeigen")
        self.grid_check.setChecked(True)
        self.grid_check.toggled.connect(self.canvas.set_grid_enabled)
        self.snap_check = QCheckBox("Am Raster einrasten")
        self.snap_check.setChecked(True)
        self.snap_check.toggled.connect(self.canvas.set_snap_enabled)
        form.addRow(self.grid_check)
        form.addRow(self.snap_check)
        body.setMinimumSize(0, 0)
        body.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        dock.setMinimumSize(200, 120)
        dock.setWidget(body)
        self.properties_dock = dock
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

    def _build_appearance_dock(self) -> None:
        dock = QDockWidget("Design", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        body = QWidget()
        layout = QVBoxLayout(body)
        # The inspector lives inside a scroll area.  Its content must keep its
        # natural minimum height; otherwise Qt may squeeze QGroupBoxes below
        # their size hint and controls overlap/clipping occurs on KDE.
        layout.setSizeConstraint(QLayout.SetMinimumSize)

        # Keep the inspector calm and focused: project, background and widget
        # controls live on separate tabs instead of one very long settings page.
        self.design_tabs = QTabWidget()
        self.design_tabs.setDocumentMode(True)

        def make_tab_page():
            page = QWidget()
            page.setFocusPolicy(Qt.ClickFocus)
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(8, 8, 8, 8)
            page_layout.setSpacing(10)
            page_layout.setSizeConstraint(QLayout.SetMinimumSize)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFocusPolicy(Qt.ClickFocus)
            scroll.viewport().setFocusPolicy(Qt.ClickFocus)
            scroll.setFrameShape(QScrollArea.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setWidget(page)
            return scroll, page, page_layout

        project_scroll, project_page, project_layout = make_tab_page()
        background_scroll, background_page, background_layout = make_tab_page()
        widget_scroll, widget_page, widget_layout = make_tab_page()

        self.design_tabs.addTab(project_scroll, "Projekt")
        self.design_tabs.addTab(background_scroll, "Hintergrund")
        self.design_tabs.addTab(widget_scroll, "Widget")
        layout.addWidget(self.design_tabs)

        theme_group = QGroupBox("Theme")
        theme_form = QFormLayout(theme_group)
        self._polish_form(theme_form)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(ThemeManager.names())
        self.theme_combo.setCurrentText(DEFAULT_THEME_NAME)
        self._polish_field(self.theme_combo, compact=True)
        self.theme_combo.currentTextChanged.connect(lambda name: self._apply_theme(name, commit=True))
        theme_form.addRow("Preset", self.theme_combo)
        project_layout.addWidget(theme_group)
        project_layout.addStretch(1)

        bg_group = QGroupBox("Hintergrund")
        bg_form = QFormLayout(bg_group)
        self._polish_form(bg_form)
        self.bg_mode_combo = QComboBox()
        self.bg_mode_combo.addItem("Einfarbig", "solid")
        self.bg_mode_combo.addItem("Verlauf", "gradient")
        self.bg_mode_combo.addItem("Bild", "image")
        self.bg_mode_combo.addItem("Live Aurora ✦", "aurora")
        self.bg_mode_combo.currentIndexChanged.connect(self._apply_background_controls)
        self._polish_field(self.bg_mode_combo, compact=True)
        self.bg_color1 = self._make_color_button("#101217", self._apply_background_controls)
        self.bg_color2 = self._make_color_button("#1b2433", self._apply_background_controls)
        self.bg_image = QLineEdit()
        self.bg_image.setReadOnly(True)
        image_button = QPushButton("Bild wählen …")
        image_button.clicked.connect(self._choose_background_image)
        self.bg_edit_check = QCheckBox("Bild direkt auf dem Display bearbeiten")
        self.bg_edit_check.toggled.connect(self.canvas.set_background_edit_enabled)
        self.bg_opacity_spin = FocusSafeSpinBox()
        self.bg_opacity_spin.setRange(0, 100)
        self.bg_opacity_spin.setSuffix(" %")
        self.bg_opacity_spin.setKeyboardTracking(False)
        self.bg_opacity_spin.valueChanged.connect(self.canvas.set_background_opacity)
        self.bg_opacity_spin.editingFinished.connect(self._background_geometry_committed)
        self.bg_x_spin = FocusSafeDoubleSpinBox()
        self.bg_x_spin.setRange(-5000.0, 5000.0)
        self.bg_x_spin.setDecimals(1)
        self.bg_y_spin = FocusSafeDoubleSpinBox()
        self.bg_y_spin.setRange(-5000.0, 5000.0)
        self.bg_y_spin.setDecimals(1)
        self.bg_scale_spin = FocusSafeSpinBox()
        self.bg_scale_spin.setRange(10, 500)
        self.bg_scale_spin.setSuffix(" %")
        for spin in (self.bg_x_spin, self.bg_y_spin):
            spin.setKeyboardTracking(False)
            spin.valueChanged.connect(self._apply_background_transform_controls)
        self.bg_scale_spin.setKeyboardTracking(False)
        self.bg_scale_spin.valueChanged.connect(self._apply_background_transform_controls)
        for spin in (self.bg_opacity_spin, self.bg_x_spin, self.bg_y_spin, self.bg_scale_spin):
            self._configure_spinbox(spin)

        fit_row = QWidget()
        fit_layout = QHBoxLayout(fit_row)
        fit_layout.setContentsMargins(0, 0, 0, 0)
        fit_layout.setSpacing(6)
        for label, mode in (("Füllen", "cover"), ("Einpassen", "contain"), ("Original", "original")):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, fit=mode: self.canvas.fit_background_image(fit))
            fit_layout.addWidget(button)
        center_button = QPushButton("Zentrieren")
        center_button.clicked.connect(self.canvas.center_background_image)
        fit_layout.addWidget(center_button)

        hint = QLabel("Tipp: Bilddatei direkt auf die Vorschau ziehen. Dann aktivieren, verschieben und unten rechts skalieren.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(mid); font-size: 10px;")

        bg_form.addRow("Typ", self.bg_mode_combo)
        bg_form.addRow("Farbe 1", self.bg_color1)
        bg_form.addRow("Farbe 2", self.bg_color2)
        bg_form.addRow("Bild", self.bg_image)
        bg_form.addRow(image_button)
        bg_form.addRow("Deckkraft", self.bg_opacity_spin)
        bg_form.addRow("Position X", self.bg_x_spin)
        bg_form.addRow("Position Y", self.bg_y_spin)
        bg_form.addRow("Skalierung", self.bg_scale_spin)
        bg_form.addRow(self.bg_edit_check)
        bg_form.addRow("Anordnung", fit_row)
        bg_form.addRow(hint)
        background_layout.addWidget(bg_group)

        self.aurora_group = QGroupBox("Live Aurora")
        aurora_form = QFormLayout(self.aurora_group)
        self._polish_form(aurora_form)
        self.aurora_color1 = self._make_color_button("#00e7ff", self._apply_background_controls)
        self.aurora_color2 = self._make_color_button("#8d5cff", self._apply_background_controls)
        self.aurora_color3 = self._make_color_button("#00ffa8", self._apply_background_controls)
        self.aurora_speed_spin = FocusSafeSpinBox()
        self.aurora_speed_spin.setRange(25, 300)
        self.aurora_speed_spin.setValue(100)
        self.aurora_speed_spin.setSuffix(" %")
        self.aurora_speed_spin.setKeyboardTracking(False)
        self.aurora_speed_spin.valueChanged.connect(self._apply_background_controls)
        self.aurora_intensity_spin = FocusSafeSpinBox()
        self.aurora_intensity_spin.setRange(0, 100)
        self.aurora_intensity_spin.setValue(70)
        self.aurora_intensity_spin.setSuffix(" %")
        self.aurora_intensity_spin.setKeyboardTracking(False)
        self.aurora_intensity_spin.valueChanged.connect(self._apply_background_controls)
        for spin in (self.aurora_speed_spin, self.aurora_intensity_spin):
            self._configure_spinbox(spin)
        aurora_form.addRow("Licht 1", self.aurora_color1)
        aurora_form.addRow("Licht 2", self.aurora_color2)
        aurora_form.addRow("Licht 3", self.aurora_color3)
        aurora_form.addRow("Tempo", self.aurora_speed_spin)
        aurora_form.addRow("Intensität", self.aurora_intensity_spin)
        self.aurora_group.setVisible(False)
        background_layout.addWidget(self.aurora_group)
        background_layout.addStretch(1)

        widget_group = QGroupBox("Ausgewähltes Widget")
        widget_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        widget_outer = QVBoxLayout(widget_group)
        widget_outer.setContentsMargins(10, 12, 10, 12)
        widget_outer.setSpacing(12)

        # A second, shallow tab level keeps common styling separate from the
        # sensor-specific controls. Only the controls relevant to the task are
        # visible at once, which is much calmer on the narrow portrait editor.
        self.widget_detail_tabs = QTabWidget()
        self.widget_detail_tabs.setDocumentMode(True)
        style_page = QWidget()
        style_layout = QVBoxLayout(style_page)
        style_layout.setContentsMargins(4, 8, 4, 4)
        style_layout.setSpacing(10)
        animation_page = QWidget()
        animation_layout = QVBoxLayout(animation_page)
        animation_layout.setContentsMargins(4, 8, 4, 4)
        animation_layout.setSpacing(10)
        data_page = QWidget()
        data_layout = QVBoxLayout(data_page)
        data_layout.setContentsMargins(4, 8, 4, 4)
        data_layout.setSpacing(10)
        self.widget_detail_tabs.addTab(style_page, "Stil")
        self.widget_detail_tabs.addTab(animation_page, "Animation")
        self.widget_detail_tabs.addTab(data_page, "Daten")
        widget_outer.addWidget(self.widget_detail_tabs)

        base_group = QGroupBox("Darstellung")
        self.base_group = base_group
        base_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        base_form = QFormLayout(base_group)
        self._polish_form(base_form)
        base_form.setContentsMargins(10, 12, 10, 12)
        base_form.setHorizontalSpacing(14)
        base_form.setVerticalSpacing(10)
        base_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.title_edit = QLineEdit()
        self.title_edit.editingFinished.connect(self._apply_widget_style)
        self.widget_bg = self._make_color_button("#1c222c", self._apply_widget_style)
        self.widget_border = self._make_color_button("#344050", self._apply_widget_style)
        self.widget_accent = self._make_color_button("#53b3ff", self._apply_widget_style)
        self.widget_title_color = self._make_color_button("#9da9ba", self._apply_widget_style)
        self.widget_value_color = self._make_color_button("#eef2f8", self._apply_widget_style)
        base_form.addRow("Titel", self.title_edit)
        base_form.addRow("Fläche", self.widget_bg)
        base_form.addRow("Rahmen", self.widget_border)
        base_form.addRow("Akzent", self.widget_accent)
        base_form.addRow("Titel-Farbe", self.widget_title_color)
        base_form.addRow("Wert-Farbe", self.widget_value_color)
        style_layout.addWidget(base_group)

        typography_group = QGroupBox("Typografie")
        self.typography_group = typography_group
        typography_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        typography_form = QFormLayout(typography_group)
        self._polish_form(typography_form)
        typography_form.setContentsMargins(10, 12, 10, 12)
        typography_form.setHorizontalSpacing(14)
        typography_form.setVerticalSpacing(10)
        typography_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.title_size_spin = FocusSafeSpinBox()
        self.title_size_spin.setRange(7, 28)
        self.value_size_spin = FocusSafeSpinBox()
        self.value_size_spin.setRange(9, 48)
        typography_form.addRow("Titelgröße", self.title_size_spin)
        typography_form.addRow("Wertgröße", self.value_size_spin)
        style_layout.addWidget(typography_group)

        effects_group = QGroupBox("Effekte")
        self.effects_group = effects_group
        effects_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        effects_form = QFormLayout(effects_group)
        self._polish_form(effects_form)
        effects_form.setContentsMargins(10, 12, 10, 12)
        effects_form.setHorizontalSpacing(14)
        effects_form.setVerticalSpacing(10)
        effects_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.opacity_spin = FocusSafeSpinBox()
        self.opacity_spin.setRange(10, 100)
        self.opacity_spin.setSuffix(" %")
        self.radius_spin = FocusSafeSpinBox()
        self.radius_spin.setRange(0, 40)
        self.glow_spin = FocusSafeSpinBox()
        self.glow_spin.setRange(0, 100)
        self.glow_spin.setSuffix(" %")
        self.lock_check = QCheckBox("Widget sperren")
        self.lock_check.toggled.connect(self._apply_widget_style)
        effects_form.addRow("Deckkraft", self.opacity_spin)
        effects_form.addRow("Eckenradius", self.radius_spin)
        effects_form.addRow("Glow", self.glow_spin)
        effects_form.addRow(self.lock_check)
        style_layout.addWidget(effects_group)
        style_layout.addStretch(1)

        animation_group = QGroupBox("Motion & Regeln")
        self.animation_group = animation_group
        animation_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        animation_form = QFormLayout(animation_group)
        self._polish_form(animation_form)
        animation_form.setContentsMargins(10, 12, 10, 12)
        animation_form.setHorizontalSpacing(14)
        animation_form.setVerticalSpacing(10)
        animation_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.animation_combo = QComboBox()
        self.animation_combo.addItem("Keine", "none")
        self.animation_combo.addItem("Pulse", "pulse")
        self.animation_combo.addItem("Breathe", "breathe")
        self.animation_combo.addItem("Heartbeat", "heartbeat")
        self.animation_combo.addItem("Neon Flicker", "flicker")
        self.animation_combo.addItem("Scanner", "scanner")
        self.animation_combo.addItem("Shimmer", "shimmer")
        self.animation_combo.addItem("Color Flow", "colorflow")
        self.animation_combo.addItem("Radar Sweep", "radar")
        self._polish_field(self.animation_combo, compact=True)

        self.animation_speed_spin = FocusSafeSpinBox()
        self.animation_speed_spin.setRange(25, 300)
        self.animation_speed_spin.setValue(100)
        self.animation_speed_spin.setSuffix(" %")
        self.animation_strength_spin = FocusSafeSpinBox()
        self.animation_strength_spin.setRange(0, 100)
        self.animation_strength_spin.setValue(70)
        self.animation_strength_spin.setSuffix(" %")

        self.animation_trigger_combo = QComboBox()
        self.animation_trigger_combo.addItem("Immer", "always")
        self.animation_trigger_combo.addItem("Ab Warnwert", "warning")
        self.animation_trigger_combo.addItem("Nur kritisch", "critical")
        self.animation_trigger_combo.addItem("Über Schwellwert", "above")
        self.animation_trigger_combo.addItem("Unter Schwellwert", "below")
        self._polish_field(self.animation_trigger_combo, compact=True)
        self.animation_trigger_spin = FocusSafeDoubleSpinBox()
        self.animation_trigger_spin.setRange(-10000.0, 100000.0)
        self.animation_trigger_spin.setDecimals(1)
        self.animation_trigger_spin.setValue(80.0)

        self.animation_color = self._make_color_button("#ff3bd4", self._apply_widget_style)
        self.alert_colors_check = QCheckBox("Warnfarben weich einblenden")
        self.alert_colors_check.toggled.connect(self._apply_widget_style)

        animation_form.addRow("Animation", self.animation_combo)
        animation_form.addRow("Auslösen", self.animation_trigger_combo)
        animation_form.addRow("Schwellwert", self.animation_trigger_spin)
        animation_form.addRow("Tempo", self.animation_speed_spin)
        animation_form.addRow("Stärke", self.animation_strength_spin)
        animation_form.addRow("Effektfarbe", self.animation_color)
        animation_form.addRow(self.alert_colors_check)
        animation_layout.addWidget(animation_group)
        animation_layout.addStretch(1)

        self.data_group = QGroupBox("Datenquelle")
        self.data_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        data_form = QFormLayout(self.data_group)
        self._polish_form(data_form)
        data_form.setContentsMargins(10, 12, 10, 12)
        data_form.setHorizontalSpacing(14)
        data_form.setVerticalSpacing(10)
        self.metric_combo = QComboBox()
        for metric in METRICS:
            self.metric_combo.addItem(metric.label, metric.key)
        self.metric_combo.currentIndexChanged.connect(self._apply_widget_style)
        self._polish_field(self.metric_combo, compact=True)
        data_form.addRow("Sensor", self.metric_combo)
        self.data_group.setVisible(False)
        data_layout.addWidget(self.data_group)

        self.gauge_group = QGroupBox("Tacho-Einstellungen")
        self.gauge_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        gauge_form = QFormLayout(self.gauge_group)
        self._polish_form(gauge_form)
        gauge_form.setContentsMargins(10, 12, 10, 12)
        gauge_form.setHorizontalSpacing(14)
        gauge_form.setVerticalSpacing(10)
        gauge_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.gauge_min_spin = FocusSafeDoubleSpinBox()
        self.gauge_min_spin.setRange(-10000.0, 10000.0)
        self.gauge_max_spin = FocusSafeDoubleSpinBox()
        self.gauge_max_spin.setRange(-9999.0, 100000.0)
        self.gauge_warn_spin = FocusSafeDoubleSpinBox()
        self.gauge_warn_spin.setRange(-10000.0, 100000.0)
        self.gauge_critical_spin = FocusSafeDoubleSpinBox()
        self.gauge_critical_spin.setRange(-10000.0, 100000.0)
        self.gauge_unit_edit = QLineEdit()
        self.gauge_style_combo = QComboBox()
        self.gauge_style_combo.addItem("Bogen", "arc")
        self.gauge_style_combo.addItem("Ring", "ring")
        self.gauge_style_combo.addItem("Halbkreis", "semi")
        self.gauge_style_combo.addItem("Balken", "bar")
        self.gauge_style_combo.currentIndexChanged.connect(self._apply_widget_style)
        self._polish_field(self.gauge_style_combo, compact=True)
        for control in (self.gauge_min_spin, self.gauge_max_spin, self.gauge_warn_spin, self.gauge_critical_spin):
            self._configure_spinbox(control, decimals=1)
            control.valueChanged.connect(self._apply_widget_style)
        self.gauge_unit_edit.editingFinished.connect(self._apply_widget_style)
        gauge_form.addRow("Minimum", self.gauge_min_spin)
        gauge_form.addRow("Maximum", self.gauge_max_spin)
        gauge_form.addRow("Warnung ab", self.gauge_warn_spin)
        gauge_form.addRow("Kritisch ab", self.gauge_critical_spin)
        gauge_form.addRow("Einheit", self.gauge_unit_edit)
        gauge_form.addRow("Stil", self.gauge_style_combo)
        self.gauge_group.setVisible(False)
        data_layout.addWidget(self.gauge_group)

        self.chart_group = QGroupBox("Diagramm-Einstellungen")
        self.chart_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        chart_form = QFormLayout(self.chart_group)
        self._polish_form(chart_form)
        chart_form.setContentsMargins(10, 12, 10, 12)
        chart_form.setHorizontalSpacing(14)
        chart_form.setVerticalSpacing(10)
        self.chart_style_combo = QComboBox()
        self.chart_style_combo.addItem("Linie", "line")
        self.chart_style_combo.addItem("Fläche", "area")
        self._polish_field(self.chart_style_combo, compact=True)
        self.chart_history_spin = FocusSafeSpinBox()
        self.chart_history_spin.setRange(10, 300)
        self._configure_spinbox(self.chart_history_spin)
        self.chart_history_spin.setSuffix(" Werte")
        self.chart_style_combo.currentIndexChanged.connect(self._apply_widget_style)
        self.chart_history_spin.valueChanged.connect(self._apply_widget_style)
        chart_form.addRow("Darstellung", self.chart_style_combo)
        chart_form.addRow("Verlauf", self.chart_history_spin)
        self.chart_group.setVisible(False)
        data_layout.addWidget(self.chart_group)
        data_layout.addStretch(1)

        for control in (
            self.opacity_spin,
            self.radius_spin,
            self.title_size_spin,
            self.value_size_spin,
            self.glow_spin,
            self.animation_speed_spin,
            self.animation_strength_spin,
            self.animation_trigger_spin,
        ):
            self._configure_spinbox(control)
            control.valueChanged.connect(self._apply_widget_style)
        self.animation_combo.activated.connect(self._apply_widget_style)
        self.animation_trigger_combo.activated.connect(self._apply_widget_style)

        # Keep interactive fields comfortably readable even with KDE scaling.
        for control in (
            self.title_edit,
            self.widget_bg,
            self.widget_border,
            self.widget_accent,
            self.widget_title_color,
            self.widget_value_color,
            self.opacity_spin,
            self.radius_spin,
            self.title_size_spin,
            self.value_size_spin,
            self.glow_spin,
            self.animation_combo,
            self.animation_trigger_combo,
            self.animation_trigger_spin,
            self.animation_speed_spin,
            self.animation_strength_spin,
            self.animation_color,
            self.alert_colors_check,
            self.gauge_min_spin,
            self.gauge_max_spin,
            self.gauge_warn_spin,
            self.gauge_critical_spin,
            self.gauge_unit_edit,
            self.metric_combo,
            self.gauge_style_combo,
            self.chart_style_combo,
            self.chart_history_spin,
        ):
            control.setMinimumHeight(28)

        widget_layout.addWidget(widget_group)
        widget_layout.addStretch(1)
        self.widget_group = widget_group
        self.appearance_body = body
        self.appearance_layout = layout
        self.appearance_pages = (project_page, background_page, widget_page)

        self.widget_style_controls = (
            self.title_edit,
            self.widget_bg,
            self.widget_border,
            self.widget_accent,
            self.widget_title_color,
            self.widget_value_color,
            self.opacity_spin,
            self.radius_spin,
            self.title_size_spin,
            self.value_size_spin,
            self.glow_spin,
            self.animation_combo,
            self.animation_trigger_combo,
            self.animation_trigger_spin,
            self.animation_speed_spin,
            self.animation_strength_spin,
            self.animation_color,
            self.alert_colors_check,
            self.lock_check,
            self.gauge_min_spin,
            self.gauge_max_spin,
            self.gauge_warn_spin,
            self.gauge_critical_spin,
            self.gauge_unit_edit,
            self.metric_combo,
            self.gauge_style_combo,
            self.chart_style_combo,
            self.chart_history_spin,
        )
        self._set_widget_style_enabled(False)

        # Each tab scrolls independently. This keeps the inspector compact and
        # avoids a single wall of controls while preserving access on small screens.
        body.setMinimumSize(0, 0)
        body.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.appearance_scroll = widget_scroll
        self._refresh_appearance_minimums()
        dock.setMinimumSize(260, 120)
        dock.setWidget(body)
        self.appearance_dock = dock
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

    def _build_pages_dock(self) -> None:
        dock = QDockWidget("Dashboards", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.pages_list = QListWidget()
        self.pages_list.setAlternatingRowColors(True)
        self.pages_list.currentRowChanged.connect(self._switch_dashboard_page)

        row1 = QWidget()
        row1_layout = QHBoxLayout(row1)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(8)
        add_btn = QPushButton("Neu")
        duplicate_btn = QPushButton("Duplizieren")
        add_btn.setObjectName("dashboardActionButton")
        duplicate_btn.setObjectName("dashboardActionButton")
        add_btn.clicked.connect(self._add_dashboard_page)
        duplicate_btn.clicked.connect(self._duplicate_dashboard_page)
        row1_layout.addWidget(add_btn, 1)
        row1_layout.addWidget(duplicate_btn, 1)

        row2 = QWidget()
        row2_layout = QHBoxLayout(row2)
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(8)
        rename_btn = QPushButton("Umbenennen")
        delete_btn = QPushButton("Löschen")
        rename_btn.setObjectName("dashboardActionButton")
        delete_btn.setObjectName("dashboardActionButton")
        rename_btn.clicked.connect(self._rename_dashboard_page)
        delete_btn.clicked.connect(self._delete_dashboard_page)
        row2_layout.addWidget(rename_btn, 1)
        row2_layout.addWidget(delete_btn, 1)

        self.page_auto_cycle_check = QCheckBox("Automatisch wechseln")
        self.page_auto_cycle_check.toggled.connect(self._set_page_auto_cycle)
        self.page_cycle_seconds = FocusSafeSpinBox()
        self.page_cycle_seconds.setRange(3, 300)
        self.page_cycle_seconds.setValue(10)
        self.page_cycle_seconds.setSuffix(" s")
        self._configure_spinbox(self.page_cycle_seconds)
        self.page_cycle_seconds.valueChanged.connect(self._set_page_cycle_seconds)

        cycle_row = QWidget()
        cycle_layout = QHBoxLayout(cycle_row)
        cycle_layout.setContentsMargins(0, 0, 0, 0)
        cycle_layout.setSpacing(12)
        cycle_layout.addWidget(QLabel("Intervall"))
        cycle_layout.addWidget(self.page_cycle_seconds)

        layout.addWidget(QLabel("Mehrere Dashboard-Seiten in einem Profil"))
        layout.addWidget(self.pages_list)
        layout.addWidget(row1)
        layout.addWidget(row2)
        layout.addWidget(self.page_auto_cycle_check)
        layout.addWidget(cycle_row)

        dock.setWidget(body)
        dock.setMinimumSize(210, 160)
        self.pages_dock = dock
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

    def _page_from_canvas(self, name: str | None = None) -> DashboardPage:
        widgets = [
            WidgetConfig(
                kind=item.kind,
                x=round(item.x()),
                y=round(item.y()),
                width=round(item.rect().width()),
                height=round(item.rect().height()),
                title=item.label,
                z=float(item.zValue()),
                options=dict(item.options),
            )
            for item in reversed(self.canvas.widget_items())
        ]
        current_name = name or (
            self.dashboard_pages[self.active_page_index].name
            if 0 <= self.active_page_index < len(self.dashboard_pages)
            else "Dashboard"
        )
        return DashboardPage(
            name=current_name,
            theme=self.current_theme_name,
            background=self.canvas.current_background_config(),
            widgets=widgets,
        )

    def _capture_active_page(self) -> None:
        if self._switching_page:
            return
        if 0 <= self.active_page_index < len(self.dashboard_pages):
            name = self.dashboard_pages[self.active_page_index].name
            self.dashboard_pages[self.active_page_index] = self._page_from_canvas(name)

    def _apply_dashboard_page(self, page: DashboardPage, *, show_status: bool = True) -> None:
        self._switching_page = True
        try:
            self.canvas.clear_widgets()
            self.current_theme_name = page.theme if page.theme in ThemeManager.names() else DEFAULT_THEME_NAME
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentText(self.current_theme_name)
            self.theme_combo.blockSignals(False)
            self.canvas.set_background_config(page.background)
            self._sync_background_controls(page.background)
            default_options = ThemeManager.get(self.current_theme_name).widget_options()
            for widget in page.widgets:
                fixed = widget.normalized(self.canvas.canvas_size.width, self.canvas.canvas_size.height)
                options = {**default_options, **fixed.options}
                restored = self.canvas.add_widget(
                    fixed.kind,
                    fixed.title or fixed.kind,
                    options=options,
                    width=fixed.width,
                    height=fixed.height,
                )
                restored.setPos(fixed.x, fixed.y)
                restored.setZValue(fixed.z)
            self._refresh_layers()
            self._last_display_payload = None
            if show_status:
                self.statusBar().showMessage(f"Dashboard: {page.name}", 2500)
        finally:
            self._switching_page = False

    def _sync_pages_ui(self) -> None:
        if not hasattr(self, "pages_list"):
            return
        self.pages_list.blockSignals(True)
        self.pages_list.clear()
        for index, page in enumerate(self.dashboard_pages):
            label = f"{index + 1}. {page.name}"
            self.pages_list.addItem(QListWidgetItem(label))
        if self.dashboard_pages:
            self.pages_list.setCurrentRow(max(0, min(self.active_page_index, len(self.dashboard_pages) - 1)))
        self.pages_list.blockSignals(False)

    def _switch_dashboard_page(self, row: int) -> None:
        if self._switching_page or row < 0 or row >= len(self.dashboard_pages):
            return
        if row == self.active_page_index:
            return
        self._capture_active_page()
        self.active_page_index = row
        self._apply_dashboard_page(self.dashboard_pages[row])
        self._history_json = self._profile_from_canvas().to_json()

    def _add_dashboard_page(self) -> None:
        before = self._profile_from_canvas().to_json()
        self._capture_active_page()
        name = f"Dashboard {len(self.dashboard_pages) + 1}"
        page = DashboardPage(
            name=name,
            theme=self.current_theme_name,
            background=BackgroundConfig(
                mode="gradient",
                color=ThemeManager.get(self.current_theme_name).canvas,
                color2=ThemeManager.get(self.current_theme_name).canvas2,
            ),
            widgets=[],
        )
        self.dashboard_pages.append(page)
        self.active_page_index = len(self.dashboard_pages) - 1
        self._apply_dashboard_page(page)
        self._sync_pages_ui()
        self._commit_history(before, "Dashboard hinzufügen")

    def _duplicate_dashboard_page(self) -> None:
        if not self.dashboard_pages:
            return
        before = self._profile_from_canvas().to_json()
        self._capture_active_page()
        source = self.dashboard_pages[self.active_page_index]
        copy_page = DashboardPage.from_raw({
            "name": f"{source.name} Kopie",
            "theme": source.theme,
            "background": {
                "mode": source.background.mode,
                "color": source.background.color,
                "color2": source.background.color2,
                "image_path": source.background.image_path,
                "image_x": source.background.image_x,
                "image_y": source.background.image_y,
                "image_width": source.background.image_width,
                "image_height": source.background.image_height,
                "image_opacity": source.background.image_opacity,
                "image_fit": source.background.image_fit,
                "aurora_color1": source.background.aurora_color1,
                "aurora_color2": source.background.aurora_color2,
                "aurora_color3": source.background.aurora_color3,
                "aurora_speed": source.background.aurora_speed,
                "aurora_intensity": source.background.aurora_intensity,
            },
            "widgets": [
                {
                    "kind": w.kind, "x": w.x, "y": w.y, "width": w.width, "height": w.height,
                    "title": w.title, "enabled": w.enabled, "z": w.z, "options": dict(w.options),
                }
                for w in source.widgets
            ],
        })
        self.dashboard_pages.append(copy_page)
        self.active_page_index = len(self.dashboard_pages) - 1
        self._apply_dashboard_page(copy_page)
        self._sync_pages_ui()
        self._commit_history(before, "Dashboard duplizieren")

    def _rename_dashboard_page(self) -> None:
        if not self.dashboard_pages:
            return
        self._capture_active_page()
        page = self.dashboard_pages[self.active_page_index]
        name, ok = QInputDialog.getText(self, self._t("Dashboard umbenennen"), self._t("Name:"), text=page.name)
        if not ok or not name.strip():
            return
        before = self._profile_from_canvas().to_json()
        page.name = name.strip()
        self._sync_pages_ui()
        self._commit_history(before, "Dashboard umbenennen")

    def _delete_dashboard_page(self) -> None:
        if len(self.dashboard_pages) <= 1:
            self.statusBar().showMessage(self._t("Mindestens ein Dashboard muss erhalten bleiben."), 3000)
            return
        before = self._profile_from_canvas().to_json()
        del self.dashboard_pages[self.active_page_index]
        self.active_page_index = min(self.active_page_index, len(self.dashboard_pages) - 1)
        self._apply_dashboard_page(self.dashboard_pages[self.active_page_index])
        self._sync_pages_ui()
        self._commit_history(before, "Dashboard löschen")

    def _set_page_auto_cycle(self, enabled: bool) -> None:
        self._capture_active_page()
        self._sync_page_cycle_timer()
        self.statusBar().showMessage(
            "Automatischer Dashboard-Wechsel aktiviert." if enabled else "Automatischer Dashboard-Wechsel deaktiviert.",
            2500,
        )

    def _set_page_cycle_seconds(self, value: int) -> None:
        del value
        self._sync_page_cycle_timer()

    def _sync_page_cycle_timer(self) -> None:
        if not hasattr(self, "page_cycle_timer"):
            return
        enabled = bool(getattr(self, "page_auto_cycle_check", None) and self.page_auto_cycle_check.isChecked())
        seconds = int(self.page_cycle_seconds.value()) if hasattr(self, "page_cycle_seconds") else 10
        self.page_cycle_timer.setInterval(max(3, seconds) * 1000)
        if enabled and len(self.dashboard_pages) > 1:
            self.page_cycle_timer.start()
        else:
            self.page_cycle_timer.stop()

    def _next_dashboard_page(self) -> None:
        if len(self.dashboard_pages) <= 1:
            return
        next_index = (self.active_page_index + 1) % len(self.dashboard_pages)
        self._switch_dashboard_page(next_index)
        self._sync_pages_ui()

    def _build_layers_dock(self) -> None:
        dock = QDockWidget("Ebenen", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        body = QWidget()
        layout = QVBoxLayout(body)
        self.layers_list = QListWidget()
        self.layers_list.setAlternatingRowColors(True)
        self.layers_list.itemClicked.connect(self._select_layer_item)
        button_row = QWidget()
        row = QHBoxLayout(button_row)
        row.setContentsMargins(0, 0, 0, 0)
        up = QPushButton("Nach vorn")
        down = QPushButton("Nach hinten")
        up.clicked.connect(lambda: self._change_layer("front"))
        down.clicked.connect(lambda: self._change_layer("back"))
        row.addWidget(up)
        row.addWidget(down)
        layout.addWidget(QLabel("Oben = Vordergrund"))
        layout.addWidget(self.layers_list)
        layout.addWidget(button_row)
        dock.setWidget(body)
        dock.setMinimumSize(190, 120)
        self.layers_dock = dock
        self._layer_items: list[WidgetItem] = []
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        self._refresh_layers()

    def _refresh_layers(self) -> None:
        if not hasattr(self, "layers_list"):
            return
        selected = set(self.canvas.selected_widgets())
        self._layer_items = sorted(self.canvas.widget_items(), key=lambda item: (item.zValue(), item.y(), item.x()), reverse=True)
        self.layers_list.blockSignals(True)
        self.layers_list.clear()
        for item in self._layer_items:
            locked = " 🔒" if bool(item.options.get("locked", False)) else ""
            entry = QListWidgetItem(f"{item.label or item.kind}  ·  {item.kind}{locked}")
            self.layers_list.addItem(entry)
            if item in selected:
                entry.setSelected(True)
        self.layers_list.blockSignals(False)

    def _select_layer_item(self, clicked: QListWidgetItem) -> None:
        row = self.layers_list.row(clicked)
        if not (0 <= row < len(self._layer_items)):
            return
        self.canvas.scene().clearSelection()
        target = self._layer_items[row]
        target.setSelected(True)
        self.canvas.centerOn(target)

    def _refresh_appearance_minimums(self) -> None:
        """Keep inspector sections at their natural height inside the scroll area.

        KDE/Qt can otherwise compress nested QGroupBoxes when the dock is short.
        Besides looking broken, the next section may physically overlap the
        controls and intercept mouse clicks.  Giving each visible section its
        size-hint height makes the scroll area scroll instead of squashing it.
        """
        groups = (
            getattr(self, "base_group", None),
            getattr(self, "typography_group", None),
            getattr(self, "effects_group", None),
            getattr(self, "data_group", None),
            getattr(self, "gauge_group", None),
            getattr(self, "chart_group", None),
        )
        for group in groups:
            if group is None:
                continue
            optional = {getattr(self, "data_group", None), getattr(self, "gauge_group", None), getattr(self, "chart_group", None)}
            if group.isVisible() or group not in optional:
                group.setMinimumHeight(group.sizeHint().height())

        widget_group = getattr(self, "widget_group", None)
        if widget_group is not None:
            widget_group.layout().activate()
            widget_group.setMinimumHeight(widget_group.sizeHint().height())

        for page in getattr(self, "appearance_pages", ()):
            if page is not None and page.layout() is not None:
                page.layout().activate()
                page.setMinimumHeight(page.sizeHint().height())

    def _configure_docks(self) -> None:
        # Layout and Design share one inspector area as tabs instead of stacking
        # vertically. This keeps the minimum window height compact.
        self.tabifyDockWidget(self.properties_dock, self.appearance_dock)
        self.properties_dock.raise_()
        self.tabifyDockWidget(self.widget_dock, self.layers_dock)
        self.tabifyDockWidget(self.layers_dock, self.pages_dock)
        self.widget_dock.raise_()
        for dock in (self.widget_dock, self.layers_dock, self.pages_dock, self.properties_dock, self.appearance_dock):
            dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

    def _fit_to_available_screen(self) -> None:
        """Choose a comfortable initial size without filling the whole desktop."""
        screen = self.screen()
        if screen is None:
            return
        available = screen.availableGeometry()
        width = min(1280, max(760, int(available.width() * 0.82)))
        height = min(780, max(520, int(available.height() * 0.76)))
        width = min(width, max(320, available.width() - 24))
        height = min(height, max(320, available.height() - 24))
        self.resize(width, height)
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def constrain_to_screen(self) -> None:
        """Clamp the shown window to the current monitor's usable work area.

        Calling this after ``show()`` is important on KDE/Wayland because the
        final frame decoration size is only known once the native window exists.
        """
        screen = self.windowHandle().screen() if self.windowHandle() else self.screen()
        if screen is None:
            return
        available = screen.availableGeometry()
        frame = self.frameGeometry()
        target_width = min(frame.width(), max(320, available.width() - 16))
        target_height = min(frame.height(), max(320, available.height() - 16))
        if target_width != frame.width() or target_height != frame.height():
            self.resize(
                max(320, target_width - (frame.width() - self.width())),
                max(320, target_height - (frame.height() - self.height())),
            )
            frame = self.frameGeometry()
        x = min(max(frame.x(), available.left()), available.right() - frame.width() + 1)
        y = min(max(frame.y(), available.top()), available.bottom() - frame.height() + 1)
        self.move(x, y)

    def _configure_spinbox(self, spin, *, decimals: int | None = None) -> None:  # noqa: ANN001
        """Normalize numeric editing behavior and geometry across OwnDash."""
        spin.setKeyboardTracking(False)
        spin.setAccelerated(True)
        spin.setSingleStep(1)
        spin.setFocusPolicy(Qt.StrongFocus)
        spin.setFixedWidth(self.NUMERIC_FIELD_WIDTH)
        spin.setMinimumHeight(self.CONTROL_HEIGHT)
        if decimals is not None and isinstance(spin, QDoubleSpinBox):
            spin.setDecimals(decimals)

    @staticmethod
    def _polish_form(form: QFormLayout) -> None:
        """Use one spacing/alignment system for every inspector form."""
        form.setContentsMargins(12, 12, 12, 12)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setRowWrapPolicy(QFormLayout.DontWrapRows)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

    def _polish_field(self, widget: QWidget, *, compact: bool = False) -> None:
        widget.setMinimumHeight(self.CONTROL_HEIGHT)
        if compact:
            widget.setMinimumWidth(self.COMPACT_FIELD_WIDTH)

    def _apply_ui_polish(self) -> None:
        """Apply one clear, interactive visual language across OwnDash."""
        for tabbar in self.findChildren(QTabBar):
            tabbar.setExpanding(False)
            tabbar.setUsesScrollButtons(True)
            if not isinstance(tabbar.parent(), QTabWidget):
                tabbar.setObjectName("dockTabBar")
                tabbar.setDrawBase(False)
            else:
                tabbar.setDrawBase(True)
        for combo in self.findChildren(QComboBox):
            combo.setMinimumHeight(self.CONTROL_HEIGHT)
        for edit in self.findChildren(QLineEdit):
            edit.setMinimumHeight(self.CONTROL_HEIGHT)
        for button in self.findChildren(QPushButton):
            button.setMinimumHeight(self.CONTROL_HEIGHT)
            button.setCursor(Qt.PointingHandCursor)
        for check in self.findChildren(QCheckBox):
            check.setMinimumHeight(28)
            check.setCursor(Qt.PointingHandCursor)

        app = QApplication.instance()
        palette = QPalette(app.palette()) if app is not None else QPalette(self.palette())
        window = palette.window().color()
        base = palette.base().color()
        button = palette.button().color()
        text = palette.buttonText().color()
        mid = palette.mid().color()
        light = palette.light().color()
        highlight = palette.highlight().color()

        # KDE dark themes often make palette.button() almost identical to the
        # surrounding panel. Raise the resting button surface enough that a
        # button is recognizable before the pointer ever reaches it.
        button_surface = QColor(button)
        if button_surface.lightness() < 128:
            button_surface = button_surface.lighter(132)
        else:
            button_surface = button_surface.darker(108)
        button_border = QColor(light if button.lightness() < 128 else mid)

        tab_surface = QColor(button_surface)
        if window.lightness() >= 128:
            tab_surface = QColor("#e2e6ea")
        highlighted_text = palette.highlightedText().color()
        disabled = palette.placeholderText().color()

        # Derive a dedicated disabled field surface. Relying on the platform's
        # internal QAbstractSpinBox/QComboBox editor palette can leave dark
        # editor interiors behind after switching from a dark KDE theme to the
        # OwnDash light palette.
        disabled_field = QColor(base)
        if base.lightness() >= 128:
            disabled_field = disabled_field.darker(106)
        else:
            disabled_field = disabled_field.lighter(118)

        arrow_suffix = "dark" if base.lightness() >= 128 else "light"
        arrow_dir = Path(__file__).resolve().parents[1] / "assets"
        spin_up_arrow = (arrow_dir / f"spin-up-{arrow_suffix}.svg").as_posix()
        spin_down_arrow = (arrow_dir / f"spin-down-{arrow_suffix}.svg").as_posix()

        self.setStyleSheet(
            f"""
            QMenuBar {{
                background-color: {window.name()};
                color: {palette.windowText().color().name()};
                border-bottom: 1px solid {mid.name()};
            }}
            QMenuBar::item {{
                background: transparent;
                color: {palette.windowText().color().name()};
                padding: 6px 10px;
                border-radius: 5px;
            }}
            QMenuBar::item:selected {{
                background-color: {tab_surface.name()};
                color: {palette.windowText().color().name()};
            }}
            QMenuBar::item:pressed {{
                background-color: {highlight.name()};
                color: {highlighted_text.name()};
            }}

            QMenu {{
                background-color: {base.name()};
                color: {palette.text().color().name()};
                border: 1px solid {mid.name()};
                padding: 4px;
            }}
            QMenu::item {{
                background: transparent;
                color: {palette.text().color().name()};
                padding: 6px 24px 6px 10px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {highlight.name()};
                color: {highlighted_text.name()};
            }}
            QMenu::item:disabled {{
                color: {disabled.name()};
            }}
            QMenu::separator {{
                height: 1px;
                background: {mid.name()};
                margin: 4px 6px;
            }}

            QDockWidget::title {{
                padding: 8px 10px;
                text-align: left;
                border-bottom: 1px solid {mid.name()};
            }}

            QGroupBox {{
                margin-top: 12px;
                padding-top: 8px;
                border: 1px solid {mid.name()};
                border-radius: 7px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}

            QPushButton {{
                background-color: {button_surface.name()};
                color: {text.name()};
                border: 1px solid {button_border.name()};
                border-radius: 7px;
                padding: 5px 12px;
            }}
            QPushButton:hover {{
                background-color: {light.name()};
                border-color: {highlight.name()};
            }}
            QPushButton:pressed {{
                background-color: {highlight.name()};
                color: {highlighted_text.name()};
                border-color: {highlight.name()};
            }}
            QPushButton:focus {{
                border-color: {highlight.name()};
            }}
            QPushButton:disabled {{
                color: {disabled.name()};
                background-color: {window.name()};
                border-color: {mid.name()};
            }}

            QPushButton#dashboardActionButton {{
                min-height: 32px;
                font-weight: 600;
                background-color: {button_surface.name()};
                border: 1px solid {button_border.name()};
            }}
            QPushButton#dashboardActionButton:hover {{
                background-color: {light.name()};
                border-color: {highlight.name()};
            }}

            QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
                background-color: {base.name()};
                color: {palette.text().color().name()};
                selection-background-color: {highlight.name()};
                selection-color: {highlighted_text.name()};
                border: 1px solid {mid.name()};
                border-radius: 7px;
                padding-left: 8px;
                padding-right: 6px;
            }}
            QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
                border-color: {button_border.name()};
            }}
            QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border-color: {highlight.name()};
            }}
            QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
                background-color: {disabled_field.name()};
                color: {disabled.name()};
                border-color: {mid.name()};
            }}

            /* Keep the embedded editor and popup list in the same palette.
               This avoids black text fields/dropdowns in OwnDash Light on KDE. */
            QComboBox QAbstractItemView {{
                background-color: {base.name()};
                color: {palette.text().color().name()};
                selection-background-color: {highlight.name()};
                selection-color: {highlighted_text.name()};
                border: 1px solid {mid.name()};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 26px;
            }}

            QSpinBox::up-button, QDoubleSpinBox::up-button,
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                subcontrol-origin: border;
                width: 24px;
                background-color: {button_surface.name()};
                border-left: 1px solid {mid.name()};
            }}
            QSpinBox::up-button, QDoubleSpinBox::up-button {{
                subcontrol-position: top right;
                border-top-right-radius: 6px;
            }}
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                subcontrol-position: bottom right;
                border-bottom-right-radius: 6px;
            }}
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
                image: url("{spin_up_arrow}");
                width: 10px;
                height: 7px;
            }}
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
                image: url("{spin_down_arrow}");
                width: 10px;
                height: 7px;
            }}
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
                background-color: {light.name()};
                border-left-color: {highlight.name()};
            }}

            QListWidget {{
                background-color: {base.name()};
                color: {palette.text().color().name()};
                border: 1px solid {mid.name()};
                border-radius: 7px;
                padding: 2px;
            }}
            QListWidget::item {{
                color: {palette.text().color().name()};
                min-height: 26px;
                border-radius: 5px;
                padding: 2px 6px;
            }}
            QListWidget::item:hover {{
                background-color: {button_surface.name()};
            }}
            QListWidget::item:selected {{
                background-color: {highlight.name()};
                color: {highlighted_text.name()};
            }}

            QTabWidget::pane {{
                border: 1px solid {mid.name()};
                top: -1px;
                background-color: {window.name()};
            }}

            QTabBar::tab {{
                min-height: 28px;
                padding: 6px 15px;
                margin: 0;
                margin-right: -1px;
                background-color: {tab_surface.name()};
                color: {text.name()};
                border: 1px solid {mid.name()};
                border-bottom: 1px solid {mid.name()};
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
            QTabBar::tab:hover {{
                background-color: {light.name()};
                border-color: {button_border.name()};
            }}
            QTabBar::tab:selected {{
                background-color: {window.name()};
                border-color: {button_border.name()};
                border-bottom-color: {window.name()};
                font-weight: 600;
            }}
            QTabBar::tab:first {{
                margin-left: 0;
            }}

            /* QMainWindow's tabified docks sit at the bottom. Treat them as
               bottom registers so the selected tab visually grows out of the
               dock instead of looking like a detached button row. */
            QTabBar#dockTabBar {{
                background: transparent;
            }}
            QTabBar#dockTabBar::tab {{
                margin: 0;
                margin-right: -1px;
                padding: 7px 16px;
                background-color: {tab_surface.name()};
                color: {text.name()};
                border: 1px solid {mid.name()};
                border-top: 1px solid {mid.name()};
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
                border-top-left-radius: 0;
                border-top-right-radius: 0;
            }}
            QTabBar#dockTabBar::tab:hover {{
                background-color: {light.name()};
                border-color: {button_border.name()};
            }}
            QTabBar#dockTabBar::tab:selected {{
                background-color: {window.name()};
                border-color: {mid.name()};
                border-top-color: {window.name()};
                font-weight: 600;
            }}
            QTabBar#dockTabBar::tab:first {{
                margin-left: 0;
            }}
            QTabBar#dockTabBar::tab:first:selected {{
                border-left-color: {mid.name()};
                border-bottom-left-radius: 0;
            }}

            QCheckBox {{
                spacing: 8px;
            }}
            """
        )

    def _make_color_button(self, initial: str, callback) -> QPushButton:  # noqa: ANN001
        button = QPushButton()
        self._set_button_color(button, initial)

        def choose() -> None:
            color = QColorDialog.getColor(QColor(str(button.property("owndashColor"))), self, "Farbe wählen")
            if not color.isValid():
                return
            self._set_button_color(button, color.name())
            callback()

        button.clicked.connect(choose)
        return button

    @staticmethod
    def _set_button_color(button: QPushButton, color: str) -> None:
        valid = QColor(color)
        value = valid.name() if valid.isValid() else "#000000"
        button.setProperty("owndashColor", value)
        button.setText(value.upper())
        foreground = "#000000" if valid.lightness() > 150 else "#ffffff"
        button.setStyleSheet(f"QPushButton {{ background: {value}; color: {foreground}; font-weight: 600; }}")

    @staticmethod
    def _button_color(button: QPushButton) -> str:
        return str(button.property("owndashColor") or "#000000")

    def _set_widget_style_enabled(self, enabled: bool) -> None:
        for control in self.widget_style_controls:
            control.setEnabled(enabled)

    def _refresh_live_data(self) -> None:
        try:
            snapshot = self.sensor_provider.snapshot()
        except Exception as exc:  # editor remains usable if a platform metric fails
            self.statusBar().showMessage(f"Live-Daten teilweise nicht verfügbar: {exc}", 3000)
            return
        self.canvas.set_snapshot(snapshot)

    def _toggle_display_stream(self, enabled: bool) -> None:
        if enabled:
            self._start_display_stream()
        else:
            self._stop_display_stream()

    def _start_display_stream(self) -> None:
        if self.display_streamer is not None and self.display_streamer.running:
            return
        profile = self._profile_from_canvas()
        if profile.display_backend == "screen":
            selected = next((d for d in self._available_screen_devices() if d[0] == profile.display_device_id), None)
            if selected is None:
                QMessageBox.warning(self, self._t("Display konnte nicht gestartet werden"), self._t("Der ausgewählte Monitor ist nicht verfügbar."))
                self.display_action.blockSignals(True)
                self.display_action.setChecked(False)
                self.display_action.setEnabled(True)
                self.display_action.blockSignals(False)
                return
            _id, name, width, height, geometry = selected
            app = QApplication.instance()
            primary = app.primaryScreen() if app is not None else None
            selected_screen = next(
                (
                    screen
                    for index, screen in enumerate(app.screens() if app is not None else [])
                    if f"screen:{index}:{screen.name()}" == profile.display_device_id
                ),
                None,
            )
            is_primary = selected_screen is not None and selected_screen is primary

            warning = self._t(
                "Das Dashboard wird auf dem ausgewählten Monitor als randloses Vollbild angezeigt. "
                "Mit Esc oder F11 kannst du die Anzeige jederzeit beenden."
            )
            if is_primary:
                warning += "\n\n" + self._t("Achtung: Du hast deinen Hauptmonitor ausgewählt.")

            answer = QMessageBox.question(
                self,
                self._t("Standard-Monitor starten?"),
                warning,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                self.display_action.blockSignals(True)
                self.display_action.setChecked(False)
                self.display_action.setText(self._t("Display starten"))
                self.display_action.setEnabled(True)
                self.display_action.blockSignals(False)
                return

            self._screen_presenter = ScreenPresenter(geometry, self)
            self._screen_presenter.close_requested.connect(self._stop_display_stream)
            backend = ScreenDisplayBackend(
                self._screen_presenter,
                ScreenBackendSettings(
                    name=name,
                    width=width,
                    height=height,
                    geometry=geometry,
                    rotation=profile.rotation,
                ),
            )
        else:
            backend = AicUsbDisplayBackend(
                UsbBackendSettings(rotation=profile.rotation, jpeg_quality=84, check_conflicting_service=True)
            )
        self.display_streamer = DisplayStreamer(
            backend,
            on_status=self.display_bridge.status.emit,
            on_connected=self.display_bridge.connected.emit,
            on_error=self.display_bridge.error.emit,
        )
        self.display_connected = False
        self._last_display_payload = None
        self.display_action.setText("Display wird verbunden …")
        self.display_action.setEnabled(False)
        self.display_streamer.start()

    def _stop_display_stream(self) -> None:
        self.display_timer.stop()
        self.display_connected = False
        self._last_display_payload = None
        streamer = self.display_streamer
        self.display_streamer = None
        presenter = self._screen_presenter
        self._screen_presenter = None
        if presenter is not None:
            try:
                presenter.close_requested.disconnect(self._stop_display_stream)
            except (RuntimeError, TypeError):
                pass
        if streamer is not None:
            streamer.stop()
        self.display_action.blockSignals(True)
        self.display_action.setChecked(False)
        self.display_action.setText("Display starten")
        self.display_action.setEnabled(True)
        self.display_action.blockSignals(False)
        if hasattr(self, "tray_display_action"):
            self.tray_display_action.setEnabled(False)
            self.tray_display_action.setText("Display ist gestoppt")
        self.statusBar().showMessage(self._t("Display-Ausgabe beendet"), 3000)

    def _display_status(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def _display_connected(self, info: object) -> None:
        self.display_connected = True
        self.display_action.blockSignals(True)
        self.display_action.setChecked(True)
        self.display_action.setText("Display stoppen")
        self.display_action.setEnabled(True)
        if hasattr(self, "tray_display_action"):
            self.tray_display_action.setEnabled(True)
            self.tray_display_action.setText("Display stoppen")
        self.display_action.blockSignals(False)
        width = getattr(info, "width", "?")
        height = getattr(info, "height", "?")
        if isinstance(width, int) and isinstance(height, int):
            profile = self._profile_from_canvas()
            logical_w, logical_h = logical_size(width, height, profile.rotation)
            if (logical_w, logical_h) != (self.canvas.canvas_size.width, self.canvas.canvas_size.height):
                self._resize_dashboard_canvas(logical_w, logical_h, scale_widgets=True)
        self._update_display_cadence(force=True)
        fps = round(1000 / max(1, self.display_timer.interval()))
        self.statusBar().showMessage(f"Display verbunden · {width}×{height} · Smooth-Ausgabe bis {fps} FPS")
        self.display_timer.start()
        self._push_display_frame()

    def _display_error(self, error: object) -> None:
        self.display_timer.stop()
        self.display_connected = False
        streamer = self.display_streamer
        self.display_streamer = None
        if streamer is not None:
            streamer.stop(timeout=0.2)
        self.display_action.blockSignals(True)
        self.display_action.setChecked(False)
        self.display_action.setText("Display starten")
        self.display_action.setEnabled(True)
        self.display_action.blockSignals(False)
        QMessageBox.warning(self, self._t("Display konnte nicht gestartet werden"), str(error))
        self.statusBar().showMessage(self._t("Display nicht verbunden"), 5000)

    def _apply_performance_mode(self, mode: str, *, announce: bool = True) -> None:
        if mode not in self._performance_profiles:
            mode = "Balanced"
        self._performance_mode = mode
        profile = self._performance_profiles[mode]
        self._display_widget_interval_ms = int(profile["widget_ms"])
        self._display_aurora_interval_ms = int(profile["aurora_ms"])
        self._display_motion_quality = int(profile["quality"])
        self.canvas.set_aurora_export_interval(self._display_aurora_interval_ms)
        if hasattr(self, "performance_actions"):
            for name, action in self.performance_actions.items():
                action.blockSignals(True)
                action.setChecked(name == mode)
                action.blockSignals(False)
        self._update_display_cadence(force=True)
        if announce:
            self.statusBar().showMessage(
                f"Performance: {mode} · Widgets {1000 / self._display_widget_interval_ms:.0f} FPS · Aurora {1000 / self._display_aurora_interval_ms:.0f} FPS",
                4500,
            )

    def _update_display_cadence(self, *, force: bool = False) -> None:
        """Run widgets, Aurora and static dashboards at independent useful rates."""
        if self.canvas.has_widget_motion():
            target = self._display_widget_interval_ms
        elif self.canvas.has_aurora_motion():
            target = self._display_aurora_interval_ms
        else:
            target = self._display_idle_interval_ms
        if force or self.display_timer.interval() != target:
            self.display_timer.setInterval(target)

    def _push_display_frame(self) -> None:
        streamer = self.display_streamer
        if not self.display_connected or streamer is None or not streamer.running:
            return
        self._update_display_cadence()
        try:
            # Motion uses a slightly lighter JPEG. Static frames are cached by
            # the canvas, and byte-identical frames are not resent over USB.
            quality = self._display_motion_quality if self.canvas.has_active_motion() else 78
            payload = self.canvas.render_jpeg(quality=quality)
        except Exception as exc:
            self.statusBar().showMessage(f"Frame konnte nicht gerendert werden: {exc}", 5000)
            return
        if payload == self._last_display_payload:
            return
        self._last_display_payload = payload
        streamer.submit(payload)

    def closeEvent(self, event) -> None:  # noqa: ANN001
        # The close button hides OwnDash to the system tray whenever the
        # "Beim Schließen im Hintergrund weiterlaufen" option is enabled.
        # This is intentionally independent of the USB display state: users
        # expect the editor to remain available in the tray even when output
        # is currently stopped.
        if (
            not self._force_quit
            and self.keep_display_running_on_close
            and QSystemTrayIcon.isSystemTrayAvailable()
        ):
            event.ignore()
            self.hide()
            if not self._tray_hint_shown:
                display_active = bool(
                    self.display_connected
                    or (self.display_streamer is not None and self.display_streamer.running)
                )
                detail = (
                    self._t("Das Display und seine Animationen laufen im Hintergrund weiter.")
                    if display_active
                    else self._t("OwnDash bleibt im Hintergrund geöffnet.")
                )
                self.tray_icon.showMessage(
                    self._t("OwnDash läuft weiter"),
                    detail + " " + self._t("Über das Tray-Symbol kannst du OwnDash wieder öffnen oder vollständig beenden."),
                    QSystemTrayIcon.Information,
                    4500,
                )
                self._tray_hint_shown = True
            return

        self.display_timer.stop()
        streamer = self.display_streamer
        self.display_streamer = None
        if streamer is not None:
            streamer.stop(timeout=1.5)
        self.tray_icon.hide()
        event.accept()
        QTimer.singleShot(0, QApplication.quit)

    def _load_template(self) -> None:
        name = self.template_combo.currentText()
        if not name:
            return

        before = self._profile_from_canvas().to_json()
        self._capture_active_page()

        template = make_template(name)
        if template.pages:
            source = template.pages[
                max(0, min(int(template.active_page), len(template.pages) - 1))
            ]
            template_page = DashboardPage(
                name=self.dashboard_pages[self.active_page_index].name,
                theme=source.theme,
                background=source.background,
                widgets=source.widgets,
            )
        else:
            template_page = DashboardPage(
                name=self.dashboard_pages[self.active_page_index].name,
                theme=template.theme,
                background=template.background,
                widgets=template.widgets,
            )

        # A template changes only the currently selected dashboard.
        # The surrounding multi-dashboard project must remain intact.
        self.dashboard_pages[self.active_page_index] = template_page
        self._apply_dashboard_page(template_page, show_status=False)
        self._sync_pages_ui()
        self._commit_history(before, f"Vorlage laden: {name}")
        self.statusBar().showMessage(
            f"Vorlage '{name}' auf {template_page.name} geladen", 2500
        )

    def _add_selected_widget(self) -> None:
        item = self.widget_list.currentItem()
        if item is None:
            return
        before = self._profile_from_canvas().to_json()
        theme = ThemeManager.get(self.current_theme_name)
        kind = str(item.data(Qt.UserRole))
        preset = widget_type(kind)
        options = {**theme.widget_options(), **(dict(preset.options or {}) if preset else {})}
        self.canvas.add_widget(
            kind, item.text(), options=options,
            width=preset.width if preset else 400,
            height=preset.height if preset else 180,
        )
        self._commit_history(before, "Widget hinzufügen")
        self._refresh_layers()

    def _copy_selected(self) -> None:
        if self.canvas.copy_selected_widgets():
            self.statusBar().showMessage(self._t("Widget(s) kopiert"), 1800)

    def _paste_widgets(self) -> None:
        before = self._profile_from_canvas().to_json()
        created = self.canvas.paste_widgets()
        if not created:
            self.statusBar().showMessage(self._t("Zwischenablage ist leer"), 1800)
            return
        self._commit_history(before, "Widget(s) einfügen")
        self._refresh_layers()

    def _duplicate_selected(self) -> None:
        selected = self.canvas.selected_widgets()
        if not selected:
            return
        before = self._profile_from_canvas().to_json()
        self.canvas.scene().clearSelection()
        for source in selected:
            clone = self.canvas.add_widget(
                source.kind, source.label,
                options=dict(source.options),
                width=round(source.rect().width()), height=round(source.rect().height()),
            )
            clone.setPos(min(self.canvas.canvas_size.width - clone.rect().width(), source.x() + 20), min(self.canvas.canvas_size.height - clone.rect().height(), source.y() + 20))
        self._commit_history(before, "Widget duplizieren")
        self._refresh_layers()

    def _change_layer(self, direction: str) -> None:
        selected = self.canvas.selected_widgets()
        if not selected:
            return
        before = self._profile_from_canvas().to_json()
        all_items = self.canvas.widget_items()
        if direction == "front":
            target = max((item.zValue() for item in all_items), default=0) + 1
        else:
            target = min((item.zValue() for item in all_items), default=0) - 1
        for item in selected:
            item.setZValue(target)
        self._commit_history(before, "Widget-Ebene ändern")
        self._refresh_layers()

    def _zoom_canvas(self, factor: float) -> None:
        current = self.canvas.transform().m11()
        target = max(0.2, min(3.0, current * factor))
        self.canvas.resetTransform()
        self.canvas.scale(target, target)
        self.statusBar().showMessage(f"Vorschau: {target * 100:.0f} %", 1500)

    def _reset_zoom(self) -> None:
        self.canvas.resetTransform()
        self.statusBar().showMessage("Vorschau: 100 %", 1500)

    def _selected_widget(self) -> WidgetItem | None:
        return self.canvas.selected_widget()

    def _sync_properties(self, item: object) -> None:
        single = item if isinstance(item, WidgetItem) else None
        enabled = single is not None
        for spin in (self.x_spin, self.y_spin, self.w_spin, self.h_spin):
            spin.setEnabled(enabled)
        self._set_widget_style_enabled(enabled)
        if single is None:
            return

        controls = (self.x_spin, self.y_spin, self.w_spin, self.h_spin)
        for widget in controls:
            widget.blockSignals(True)
        self.x_spin.setValue(round(single.x()))
        self.y_spin.setValue(round(single.y()))
        self.w_spin.setValue(round(single.rect().width()))
        self.h_spin.setValue(round(single.rect().height()))
        for widget in controls:
            widget.blockSignals(False)

        options = {**ThemeManager.get(self.current_theme_name).widget_options(), **single.options}
        style_controls = self.widget_style_controls
        for control in style_controls:
            control.blockSignals(True)
        self.title_edit.setText(single.label)
        self._set_button_color(self.widget_bg, str(options["background"]))
        self._set_button_color(self.widget_border, str(options["border"]))
        self._set_button_color(self.widget_accent, str(options["accent"]))
        self._set_button_color(self.widget_title_color, str(options["title_color"]))
        self._set_button_color(self.widget_value_color, str(options["value_color"]))
        self.opacity_spin.setValue(int(options["opacity"]))
        self.radius_spin.setValue(int(options["radius"]))
        self.title_size_spin.setValue(int(options["title_size"]))
        self.value_size_spin.setValue(int(options["value_size"]))
        self.glow_spin.setValue(int(options["glow"]))
        animation_index = self.animation_combo.findData(str(options.get("animation", "none")))
        self.animation_combo.setCurrentIndex(max(0, animation_index))
        trigger_index = self.animation_trigger_combo.findData(str(options.get("animation_trigger", "always")))
        self.animation_trigger_combo.setCurrentIndex(max(0, trigger_index))
        self.animation_trigger_spin.setValue(float(options.get("animation_trigger_value", 80.0)))
        self.animation_speed_spin.setValue(int(options.get("animation_speed", 100)))
        self.animation_strength_spin.setValue(int(options.get("animation_strength", 70)))
        self._set_button_color(self.animation_color, str(options.get("animation_color", "#ff3bd4")))
        self.alert_colors_check.setChecked(bool(options.get("alert_colors", False)))
        self.lock_check.setChecked(bool(options.get("locked", False)))
        is_gauge = single.kind.startswith("gauge_")
        is_chart = single.kind in {"chart", "sparkline"}
        legacy_metric = {"cpu": "cpu.usage", "gpu": "gpu.usage", "temperature": "temperature.value", "power": "power.total_w", "memory": "memory.percent"}.get(str(options.get("gauge_metric", "")), "cpu.usage")
        metric_key = str(options.get("metric_key", legacy_metric))
        metric_index = self.metric_combo.findData(metric_key)
        self.metric_combo.setCurrentIndex(max(0, metric_index))
        self.data_group.setVisible(is_gauge or is_chart)
        self.gauge_min_spin.setValue(float(options.get("gauge_min", 0)))
        self.gauge_max_spin.setValue(float(options.get("gauge_max", 100)))
        self.gauge_warn_spin.setValue(float(options.get("warn", 75)))
        self.gauge_critical_spin.setValue(float(options.get("critical", 90)))
        self.gauge_unit_edit.setText(str(options.get("gauge_unit", "%")))
        gauge_style_index = self.gauge_style_combo.findData(str(options.get("gauge_style", "arc")))
        self.gauge_style_combo.setCurrentIndex(max(0, gauge_style_index))
        chart_style_index = self.chart_style_combo.findData(str(options.get("chart_style", "line")))
        self.chart_style_combo.setCurrentIndex(max(0, chart_style_index))
        self.chart_history_spin.setValue(int(options.get("history_points", 60)))
        self.gauge_group.setVisible(is_gauge)
        self.chart_group.setVisible(is_chart)
        QTimer.singleShot(0, self._refresh_appearance_minimums)
        for control in style_controls:
            control.blockSignals(False)

    def _apply_geometry_properties(self) -> None:
        item = self._selected_widget()
        if item is None or self._restoring:
            return
        before = self._profile_from_canvas().to_json()
        x = min(self.x_spin.value(), self.canvas.canvas_size.width - 40)
        y = min(self.y_spin.value(), self.canvas.canvas_size.height - 40)
        width = max(40, min(self.w_spin.value(), self.canvas.canvas_size.width - x))
        height = max(40, min(self.h_spin.value(), self.canvas.canvas_size.height - y))
        item.setPos(x, y)
        item.setRect(0, 0, width, height)
        self._sync_properties(item)
        self._commit_history(before, "Widget-Geometrie ändern")

    def _apply_widget_style(self) -> None:
        item = self._selected_widget()
        if item is None or self._restoring:
            return
        before = self._profile_from_canvas().to_json()
        item.label = self.title_edit.text().strip() or item.kind
        options = dict(item.options)
        options.update(
            {
                "background": self._button_color(self.widget_bg),
                "border": self._button_color(self.widget_border),
                "accent": self._button_color(self.widget_accent),
                "title_color": self._button_color(self.widget_title_color),
                "value_color": self._button_color(self.widget_value_color),
                "opacity": self.opacity_spin.value(),
                "radius": self.radius_spin.value(),
                "title_size": self.title_size_spin.value(),
                "value_size": self.value_size_spin.value(),
                "glow": self.glow_spin.value(),
                "animation": str(self.animation_combo.currentData()),
                "animation_trigger": str(self.animation_trigger_combo.currentData() or "always"),
                "animation_trigger_value": self.animation_trigger_spin.value(),
                "animation_speed": self.animation_speed_spin.value(),
                "animation_strength": self.animation_strength_spin.value(),
                "animation_color": self._button_color(self.animation_color),
                "alert_colors": self.alert_colors_check.isChecked(),
                "locked": self.lock_check.isChecked(),
                "gauge_min": self.gauge_min_spin.value(),
                "gauge_max": self.gauge_max_spin.value(),
                "warn": self.gauge_warn_spin.value(),
                "critical": self.gauge_critical_spin.value(),
                "gauge_unit": self.gauge_unit_edit.text().strip(),
                "metric_key": str(self.metric_combo.currentData() or "cpu.usage"),
                "gauge_style": str(self.gauge_style_combo.currentData() or "arc"),
                "chart_style": str(self.chart_style_combo.currentData() or "line"),
                "history_points": self.chart_history_spin.value(),
            }
        )
        item.set_style_options(options)
        self._commit_history(before, "Widget-Design ändern")

    def _apply_theme(self, name: str, *, commit: bool) -> None:
        if self._restoring:
            return
        before = self._profile_from_canvas().to_json() if commit and self._history_json else ""
        self.current_theme_name = name if name in ThemeManager.names() else DEFAULT_THEME_NAME
        theme = ThemeManager.get(self.current_theme_name)
        self.canvas.apply_theme(theme, apply_to_widgets=True)
        self._sync_background_controls(self.canvas.background_config)
        selected = self._selected_widget()
        if selected is not None:
            self._sync_properties(selected)
        if commit and before:
            self._commit_history(before, f"Theme: {self.current_theme_name}")

    def _apply_background_controls(self) -> None:
        if self._restoring:
            return
        before = self._profile_from_canvas().to_json()
        current = self.canvas.current_background_config()
        config = BackgroundConfig(
            mode=str(self.bg_mode_combo.currentData()),
            color=self._button_color(self.bg_color1),
            color2=self._button_color(self.bg_color2),
            image_path=self.bg_image.text(),
            image_x=current.image_x,
            image_y=current.image_y,
            image_width=current.image_width,
            image_height=current.image_height,
            image_opacity=self.bg_opacity_spin.value(),
            image_fit=current.image_fit,
            aurora_color1=self._button_color(self.aurora_color1),
            aurora_color2=self._button_color(self.aurora_color2),
            aurora_color3=self._button_color(self.aurora_color3),
            aurora_speed=self.aurora_speed_spin.value(),
            aurora_intensity=self.aurora_intensity_spin.value(),
        )
        self.canvas.set_background_config(config)
        self.canvas.set_background_edit_enabled(self.bg_edit_check.isChecked())
        self._sync_background_controls(self.canvas.current_background_config())
        self._commit_history(before, "Hintergrund ändern")

    def _apply_background_transform_controls(self) -> None:
        if self._restoring or self.canvas._background_item is None:
            return
        item = self.canvas._background_item
        pixmap = self.canvas._background_pixmap
        if pixmap.isNull():
            return
        before = self._profile_from_canvas().to_json()
        scale = self.bg_scale_spin.value() / 100.0
        width = max(1.0, pixmap.width() * scale)
        height = max(1.0, pixmap.height() * scale)
        item.setRect(0.0, 0.0, width, height)
        item.setPos(self.bg_x_spin.value(), self.bg_y_spin.value())
        self.canvas._background_item_committed()
        self._sync_background_controls(self.canvas.current_background_config())
        self._commit_history(before, "Hintergrund exakt positionieren")

    def _choose_background_image(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            self._t("Hintergrundbild wählen"),
            str(Path.home()),
            "Bilder (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if filename:
            self._set_background_image(filename)

    def _set_dropped_background_image(self, filename: str) -> None:
        self._set_background_image(filename)

    def _set_background_image(self, filename: str) -> None:
        path = Path(filename).expanduser()
        if not path.is_file():
            return
        before = self._profile_from_canvas().to_json()
        config = BackgroundConfig(
            mode="image",
            color=self._button_color(self.bg_color1),
            color2=self._button_color(self.bg_color2),
            image_path=str(path),
            image_opacity=self.bg_opacity_spin.value() or 100,
            image_fit="cover",
            aurora_color1=self._button_color(self.aurora_color1),
            aurora_color2=self._button_color(self.aurora_color2),
            aurora_color3=self._button_color(self.aurora_color3),
            aurora_speed=self.aurora_speed_spin.value(),
            aurora_intensity=self.aurora_intensity_spin.value(),
        )
        self.canvas.set_background_config(config)
        self.bg_edit_check.blockSignals(True)
        self.bg_edit_check.setChecked(True)
        self.bg_edit_check.blockSignals(False)
        self.canvas.set_background_edit_enabled(True)
        self._sync_background_controls(self.canvas.current_background_config())
        self._commit_history(before, "Hintergrundbild setzen")
        self.statusBar().showMessage("Hintergrundbild aktiv · Ziehen zum Verschieben, Griff unten rechts zum Skalieren", 5000)

    def _sync_background_controls(self, config: BackgroundConfig) -> None:
        controls = (
            self.bg_mode_combo, self.bg_color1, self.bg_color2, self.bg_image, self.bg_opacity_spin,
            self.bg_x_spin, self.bg_y_spin, self.bg_scale_spin, self.aurora_color1, self.aurora_color2,
            self.aurora_color3, self.aurora_speed_spin, self.aurora_intensity_spin,
        )
        for control in controls:
            control.blockSignals(True)
        index = self.bg_mode_combo.findData(config.mode)
        self.bg_mode_combo.setCurrentIndex(max(0, index))
        self._set_button_color(self.bg_color1, config.color)
        self._set_button_color(self.bg_color2, config.color2)
        self.bg_image.setText(config.image_path)
        self.bg_opacity_spin.setValue(max(0, min(100, int(config.image_opacity))))
        self._set_button_color(self.aurora_color1, config.aurora_color1)
        self._set_button_color(self.aurora_color2, config.aurora_color2)
        self._set_button_color(self.aurora_color3, config.aurora_color3)
        self.aurora_speed_spin.setValue(max(25, min(300, int(config.aurora_speed))))
        self.aurora_intensity_spin.setValue(max(0, min(100, int(config.aurora_intensity))))
        self.aurora_group.setVisible(config.mode == "aurora")
        self.bg_x_spin.setValue(float(config.image_x))
        self.bg_y_spin.setValue(float(config.image_y))
        pixmap = self.canvas._background_pixmap
        if not pixmap.isNull() and pixmap.width() > 0 and config.image_width > 0:
            self.bg_scale_spin.setValue(max(10, min(500, round(config.image_width / pixmap.width() * 100))))
        else:
            self.bg_scale_spin.setValue(100)
        image_enabled = config.mode == "image" and bool(config.image_path)
        for transform_control in (self.bg_x_spin, self.bg_y_spin, self.bg_scale_spin):
            transform_control.setEnabled(image_enabled)
        self.bg_edit_check.setEnabled(image_enabled)
        if not image_enabled and self.bg_edit_check.isChecked():
            self.bg_edit_check.setChecked(False)
        for control in controls:
            control.blockSignals(False)

    def _background_geometry_committed(self) -> None:
        if self._restoring:
            return
        current = self._profile_from_canvas().to_json()
        if current != self._history_json:
            self.undo_stack.push(ProfileCommand(self, self._history_json, current, "Hintergrund verschieben/skalieren"))
            self._history_json = current

    def _geometry_committed(self, _item: object) -> None:
        if self._restoring:
            return
        current = self._profile_from_canvas().to_json()
        if current != self._history_json:
            self.undo_stack.push(ProfileCommand(self, self._history_json, current, "Widget verschieben/skalieren"))
            self._history_json = current
        self._sync_properties(self._selected_widget())

    def _delete_selected(self) -> None:
        selected = self.canvas.selected_widgets()
        if not selected:
            return
        before = self._profile_from_canvas().to_json()
        for item in selected:
            self.canvas.scene().removeItem(item)
        self._commit_history(before, "Widget löschen")
        self._refresh_layers()

    def _align_selected(self, mode: str) -> None:
        selected = self.canvas.selected_widgets()
        if len(selected) < 2:
            self.statusBar().showMessage(self._t("Zum Ausrichten mindestens zwei Widgets auswählen (Strg+Klick)"), 3000)
            return
        before = self._profile_from_canvas().to_json()
        if mode == "left":
            target = min(item.x() for item in selected)
            for item in selected:
                item.setX(target)
        elif mode == "top":
            target = min(item.y() for item in selected)
            for item in selected:
                item.setY(target)
        elif mode == "hcenter":
            target = sum(item.x() + item.rect().width() / 2.0 for item in selected) / len(selected)
            for item in selected:
                item.setX(target - item.rect().width() / 2.0)
        elif mode == "vcenter":
            target = sum(item.y() + item.rect().height() / 2.0 for item in selected) / len(selected)
            for item in selected:
                item.setY(target - item.rect().height() / 2.0)
        self._commit_history(before, "Widgets ausrichten")
        self._refresh_layers()

    def _commit_history(self, before: str, text: str) -> None:
        if self._restoring:
            return
        after = self._profile_from_canvas().to_json()
        if before == after:
            return
        self.undo_stack.push(ProfileCommand(self, before, after, text))
        self._history_json = after

    def _profile_from_canvas(self) -> Profile:
        current_page = self._page_from_canvas()
        pages = list(self.dashboard_pages)
        if 0 <= self.active_page_index < len(pages):
            pages[self.active_page_index] = current_page
        elif not pages:
            pages = [current_page]
            self.active_page_index = 0

        return Profile(
            name="Default",
            canvas_width=self.canvas.canvas_size.width,
            canvas_height=self.canvas.canvas_size.height,
            rotation=getattr(self, "_display_rotation", 270),
            display_backend=self.display_backend_key,
            display_device_id=self.display_device_id,
            theme=current_page.theme,
            background=current_page.background,
            widgets=current_page.widgets,
            pages=pages,
            active_page=self.active_page_index,
            auto_cycle=bool(
                hasattr(self, "page_auto_cycle_check")
                and self.page_auto_cycle_check.isChecked()
            ),
            auto_cycle_seconds=int(
                self.page_cycle_seconds.value()
                if hasattr(self, "page_cycle_seconds")
                else 10
            ),
        )

    def _restore_profile_json(self, text: str) -> None:
        self._restoring = True
        try:
            self._apply_profile(Profile.from_json(text), show_status=False)
            self._history_json = text
        finally:
            self._restoring = False

    def _apply_profile(self, profile: Profile, show_status: bool = True) -> None:
        if profile.pages:
            self.dashboard_pages = [
                DashboardPage.from_raw({
                    "name": page.name,
                    "theme": page.theme,
                    "background": {
                        "mode": page.background.mode,
                        "color": page.background.color,
                        "color2": page.background.color2,
                        "image_path": page.background.image_path,
                        "image_x": page.background.image_x,
                        "image_y": page.background.image_y,
                        "image_width": page.background.image_width,
                        "image_height": page.background.image_height,
                        "image_opacity": page.background.image_opacity,
                        "image_fit": page.background.image_fit,
                        "aurora_color1": page.background.aurora_color1,
                        "aurora_color2": page.background.aurora_color2,
                        "aurora_color3": page.background.aurora_color3,
                        "aurora_speed": page.background.aurora_speed,
                        "aurora_intensity": page.background.aurora_intensity,
                    },
                    "widgets": [
                        {
                            "kind": w.kind, "x": w.x, "y": w.y, "width": w.width, "height": w.height,
                            "title": w.title, "enabled": w.enabled, "z": w.z, "options": dict(w.options),
                        }
                        for w in page.widgets
                    ],
                })
                for page in profile.pages
            ]
        else:
            self.dashboard_pages = [
                DashboardPage(
                    name=profile.name or "Dashboard 1",
                    theme=profile.theme,
                    background=profile.background,
                    widgets=profile.widgets,
                )
            ]

        self.display_backend_key = str(profile.display_backend or "aic_usb")
        self.display_device_id = str(profile.display_device_id or "auto")
        self._display_rotation = int(profile.rotation)
        self._resize_dashboard_canvas(int(profile.canvas_width), int(profile.canvas_height), scale_widgets=False)

        self.active_page_index = max(0, min(int(profile.active_page), len(self.dashboard_pages) - 1))
        self._apply_dashboard_page(self.dashboard_pages[self.active_page_index], show_status=False)

        if hasattr(self, "page_auto_cycle_check"):
            self.page_auto_cycle_check.blockSignals(True)
            self.page_auto_cycle_check.setChecked(bool(profile.auto_cycle))
            self.page_auto_cycle_check.blockSignals(False)
            self.page_cycle_seconds.blockSignals(True)
            self.page_cycle_seconds.setValue(max(3, min(300, int(profile.auto_cycle_seconds))))
            self.page_cycle_seconds.blockSignals(False)

        self._sync_pages_ui()
        self._sync_page_cycle_timer()
        if show_status:
            self.statusBar().showMessage(
                f"Profil geladen: {profile.name} · {len(self.dashboard_pages)} Dashboard(s)",
                3000,
            )

    def _save(self) -> None:
        profile = self._profile_from_canvas()
        try:
            save_profile(profile, self.profile_path)
        except OSError as exc:
            QMessageBox.critical(self, self._t("Profil konnte nicht gespeichert werden"), str(exc))
            return
        self.statusBar().showMessage(f"Gespeichert: {self.profile_path}", 3000)

    def _open(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            self._t("OwnDash-Profil öffnen"),
            str(self.profile_path.parent),
            "OwnDash Profile (*.json)",
        )
        if not filename:
            return
        try:
            profile = load_profile(Path(filename))
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.critical(self, self._t("Profil konnte nicht geladen werden"), str(exc))
            return
        before = self._profile_from_canvas().to_json()
        self.profile_path = Path(filename)
        self._apply_profile(profile)
        self._commit_history(before, "Profil öffnen")

    def _load_default_if_present(self) -> None:
        if not self.profile_path.exists():
            return
        try:
            self._apply_profile(load_profile(self.profile_path))
        except (OSError, ValueError, TypeError) as exc:
            self.statusBar().showMessage(f"Standardprofil konnte nicht geladen werden: {exc}", 5000)
