from __future__ import annotations

from PySide6.QtCore import QLocale, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDockWidget, QGroupBox, QLabel, QLineEdit, QMenu,
    QPushButton, QTabWidget, QToolBar, QWidget,
)

EN: dict[str, str] = {
    "Ausgabe umgestellt": "Output switched",
    "Dashboard pausiert": "Dashboard paused",
    "OwnDash beendet": "OwnDash closed",
    "Ausgabe auf anderen Bildschirm umgestellt": "Output switched to another display",
    "Bis gleich.": "See you soon.",
    "GPU · VRAM-Auslastung": "GPU · VRAM usage",
    "GPU · VRAM belegt": "GPU · VRAM used",
    "GPU · VRAM gesamt": "GPU · VRAM total",
    "Hilfe": "Help", "Über OwnDash …": "About OwnDash …", "Über OwnDash": "About OwnDash",
    "Schließen": "Close",
    "OwnDash auf GitHub": "OwnDash on GitHub", "Projektseite": "Project page",
    "OwnDash-Hilfe …": "OwnDash Help …", "OwnDash-Hilfe": "OwnDash Help",
    "System- und Sensorinformationen …": "System and sensor information …",
    "Systemprüfung …": "System check …", "OwnDash-Systemprüfung": "OwnDash system check",
    "Willkommen bei OwnDash": "Welcome to OwnDash",
    "OwnDash prüft automatisch, ob dein Linux-System bereit ist. Du musst dafür keine technischen Einstellungen kennen.":
        "OwnDash automatically checks whether your Linux system is ready. You do not need to know any technical settings.",
    "Grundvoraussetzungen": "Basic requirements", "Hardware und Sensoren": "Hardware and sensors",
    "Optionale Erweiterungen": "Optional enhancements",
    "Display-Ausgabe": "Display output",
    "Standard-Monitor-Ausgabe": "Standard monitor output",
    "ArtInChip / VSDISPLAY verbunden": "ArtInChip / VSDISPLAY connected",
    "USB-Zugriffsberechtigung": "USB access permission",
    "Das USB-Display wurde erkannt, OwnDash benötigt aber noch Zugriffsrechte.":
        "The USB display was detected, but OwnDash still needs access permission.",
    "USB-Zugriff einrichten": "Set up USB access", "USB-Zugriff": "USB access",
    "Die grafische Administratorfreigabe (pkexec) ist auf diesem System nicht verfügbar.":
        "Graphical administrator authorization (pkexec) is not available on this system.",
    "Die OwnDash-USB-Regel konnte im Programmpaket nicht gefunden werden.":
        "The OwnDash USB rule could not be found in the application package.",
    "Die Administratorfreigabe wurde abgebrochen.": "Administrator authorization was cancelled.",
    "Die USB-Regel konnte nicht installiert werden.": "The OwnDash USB rule could not be installed.",
    "USB-Zugriff wurde eingerichtet. Falls das Display noch nicht erkannt wird, trenne es kurz und verbinde es erneut.":
        "USB access was set up. If the display is still not detected, disconnect it briefly and reconnect it.",
    "Linux-System": "Linux system",
    "Grafische Oberfläche (Wayland / X11)": "Graphical session (Wayland / X11)",
    "Linux-Systeminformationen (/proc)": "Linux system information (/proc)",
    "Linux-Hardwareinformationen (/sys)": "Linux hardware information (/sys)",
    "CPU-Auslastung": "CPU usage", "CPU-Temperatur": "CPU temperature", "CPU-Leistung": "CPU power",
    "GPU-Auslastung": "GPU usage", "GPU-Temperatur": "GPU temperature", "GPU-Leistung": "GPU power",
    "Sensor-Schnittstelle (hwmon)": "Sensor interface (hwmon)",
    "Leistungs-Schnittstelle (powercap)": "Power interface (powercap)",
    "Lesbare PCI-Hardwarenamen (lspci)": "Readable PCI hardware names (lspci)",
    "NVIDIA-Sensordaten (nvidia-smi)": "NVIDIA sensor data (nvidia-smi)",
    "Bereit": "Ready", "Optional / nicht verfügbar": "Optional / unavailable",
    "Aufmerksamkeit erforderlich": "Attention required",
    "OwnDash ist auf diesem System grundsätzlich einsatzbereit. Nicht verfügbare optionale Sensoren schränken nur einzelne Messwerte ein.":
        "OwnDash is ready to run on this system. Unavailable optional sensors only limit individual readings.",
    "Mindestens eine Grundvoraussetzung fehlt. OwnDash kann auf diesem System möglicherweise nicht vollständig ausgeführt werden.":
        "At least one basic requirement is missing. OwnDash may not run fully on this system.",
    "OwnDash starten": "Start OwnDash",
    "System- und Sensorinformationen": "System and sensor information",
    "Distribution": "Distribution", "Kernel": "Kernel", "Desktop": "Desktop", "Sitzung": "Session",
    "Treiber": "Driver", "Weitere Systemwerte": "Additional system values",
    "Verfügbar": "Available", "Nicht verfügbar": "Not available",
    "OwnDash erkennt Sensoren dynamisch. Ein grünes Häkchen bedeutet, dass der Wert auf diesem System verfügbar ist.":
        "OwnDash detects sensors dynamically. A green check mark means that the value is available on this system.",
    "Fehlende Sensoren sind kein Fehler: Welche Werte verfügbar sind, hängt von Hardware, Kernel und Treiber ab.":
        "Missing sensors are not an error: available values depend on the hardware, kernel and driver.",
    "OwnDash erkennt Sensoren dynamisch. Ein Strich bedeutet, dass dieser Wert auf dem aktuellen System nicht verfügbar ist.":
        "OwnDash detects sensors dynamically. A dash means that this value is not available on the current system.",
    "Änderungsprotokoll …": "Changelog …", "Änderungsprotokoll": "Changelog",
    "Fehler melden …": "Report a bug …", "Fehler melden": "Report a bug",
    "Entwickler": "Developer", "Entwickler / Copyright": "Developer / Copyright", "Lizenz": "License", "Projektstatus": "Project status",
    "Ein freier Dashboard-Editor für PC-Gehäusedisplays unter Linux.":
        "An open-source dashboard editor for PC case displays on Linux.",
    "Hinweise zu verwendeten Open-Source-Komponenten befinden sich in THIRD_PARTY.md.":
        "Notices for third-party open-source components are available in THIRD_PARTY.md.",
    "Das Änderungsprotokoll konnte nicht geladen werden.": "The changelog could not be loaded.",
    "Der Browser konnte nicht geöffnet werden. Öffne bitte den GitHub-Issue-Tracker des Projekts.":
        "The browser could not be opened. Please open the project's GitHub issue tracker.",
    "Der Browser konnte nicht geöffnet werden. Öffne bitte die OwnDash-Projektseite auf GitHub.":
        "The browser could not be opened. Please open the OwnDash project page on GitHub.",
    "Projekt": "Project", "Bearbeiten": "Edit", "Anordnen": "Arrange", "Ansicht": "View",
    "Speichern": "Save", "Öffnen": "Open", "Löschen": "Delete", "Duplizieren": "Duplicate",
    "Kopieren": "Copy", "Einfügen": "Paste", "Nach vorn": "Bring forward",
    "Nach hinten": "Send backward", "Rückgängig": "Undo", "Wiederholen": "Redo",
    "Links ausrichten": "Align left", "Oben ausrichten": "Align top",
    "Horizontal zentrieren": "Center horizontally", "Vertikal zentrieren": "Center vertically",
    "Display starten": "Start display", "Display stoppen": "Stop display",
    "Beim Schließen im Hintergrund weiterlaufen": "Keep running in background when closing",
    "Performance": "Performance", "Einstellungen …": "Settings …",
    "Vorschau verkleinern": "Zoom out", "Vorschau vergrößern": "Zoom in",
    "Widgets": "Widgets", "Ebenen": "Layers", "Dashboards": "Dashboards",
    "Widget": "Widget", "Layout": "Layout", "Design": "Design",
    "Projekt": "Project", "Hintergrund": "Background", "Daten": "Data",
    "Animation": "Animation", "Stil": "Style", "Ausgewähltes Widget": "Selected widget",
    "Theme": "Theme", "Preset": "Preset", "Dashboard-Vorlagen": "Dashboard templates",
    "Vorlage laden": "Load template", "Zum Dashboard hinzufügen": "Add to dashboard",
    "Widget ziehen oder doppelklicken": "Drag widget or double-click",
    "Mehrere Dashboard-Seiten in einem Profil": "Multiple dashboard pages in a profile",
    "Neu": "New", "Umbenennen": "Rename", "Automatisch wechseln": "Cycle automatically",
    "Intervall": "Interval", "Raster anzeigen": "Show grid", "Am Raster einrasten": "Snap to grid",
    "Breite": "Width", "Höhe": "Height", "Darstellung": "Appearance",
    "Titel": "Title", "Fläche": "Surface", "Rahmen": "Border", "Akzent": "Accent",
    "Titel-Farbe": "Title color", "Wert-Farbe": "Value color", "Typografie": "Typography",
    "Titelgröße": "Title size", "Wertgröße": "Value size", "Effekte": "Effects",
    "Datenquelle": "Data source", "Sensor": "Sensor", "Werte": "Values",
    "Auslösen": "Trigger", "Schwellwert": "Threshold", "Über Schwellwert": "Above threshold",
    "Unter Schwellwert": "Below threshold", "Stärke": "Strength",
    "Farbe 1": "Color 1", "Farbe 2": "Color 2", "Intensität": "Intensity",
    "Bild wählen …": "Choose image …", "Füllen": "Fill", "Einpassen": "Fit",
    "Original": "Original", "Zentrieren": "Center", "Keine": "None",
    "Hintergrund exakt positionieren": "Position background precisely",
    "OwnDash öffnen": "Open OwnDash", "OwnDash vollständig beenden": "Quit OwnDash completely",
    "Bereit · Live-Vorschau aktiv": "Ready · Live preview active",
    "Display ist gestoppt": "Display is stopped", "Display-Ausgabe beendet": "Display output stopped",
    "Display nicht verbunden": "Display not connected",
    "Display konnte nicht gestartet werden": "Display could not be started",
    "OwnDash läuft weiter": "OwnDash keeps running",
    "OwnDash bleibt im Hintergrund geöffnet.": "OwnDash remains open in the background.",
    "Das Display und seine Animationen laufen im Hintergrund weiter.":
        "The display and its animations keep running in the background.",
    "Über das Tray-Symbol kannst du OwnDash wieder öffnen oder vollständig beenden.":
        "Use the tray icon to reopen OwnDash or quit it completely.",
    "Mindestens ein Dashboard muss erhalten bleiben.": "At least one dashboard must remain.",
    "Dashboard umbenennen": "Rename dashboard", "Name:": "Name:",
    "Widget(s) kopiert": "Widget(s) copied", "Zwischenablage ist leer": "Clipboard is empty",
    "Zum Ausrichten mindestens zwei Widgets auswählen (Strg+Klick)":
        "Select at least two widgets to align them (Ctrl+click)",
    "Hintergrundbild wählen": "Choose background image",
    "OwnDash-Profil öffnen": "Open OwnDash profile",
    "Profil konnte nicht gespeichert werden": "Profile could not be saved",
    "Profil konnte nicht geladen werden": "Profile could not be loaded",
    "Einstellungen": "Settings", "Sprache": "Language", "Erscheinungsbild": "Appearance",
    "Systemsprache": "System language", "Deutsch": "German", "Englisch": "English",
    "System": "System", "Dunkel": "Dark", "Hell": "Light",
    "Abbrechen": "Cancel", "Übernehmen": "Apply",
    "Allgemein": "General",
    "Sprache und Erscheinungsbild werden sofort angewendet.":
        "Language and appearance are applied immediately.",
    "Systemeinstellung": "System setting",
    "Systemzustandsanzeigen": "System state screens",
    "Systemzustände auf dem Display anzeigen": "Show system states on the display",
    "Bazzite-inspiriert": "Bazzite-inspired",
    "Ruhemodus": "Idle mode",
    "Zeit bis Ruhemodus": "Idle timeout",
    "Minuten": "Minutes",
    "Sperrbildschirm berücksichtigen": "Lock screen handling",
    "Standby": "Standby",
    "Standby wird vorbereitet": "Entering standby",
    "System gesperrt": "System locked",
    "Herunterfahren": "Shutting down",
    "Neustart": "Restarting",
    "Display auswählen": "Select display", "Display auswählen …": "Select display …",
    "Display-Steuerung …": "Display controls …", "Display-Steuerung": "Display controls",
    "Geräteversion": "Device version", "Helligkeit": "Brightness",
    "Display-Steuerung nicht verfügbar": "Display controls unavailable",
    "Die Display-Steuerung ist erst nach erfolgreicher Verbindung verfügbar.":
        "Display controls are available only after a successful connection.",
    "Standard-Monitor (HDMI/DP/USB-C)": "Standard monitor (HDMI/DP/USB-C)",
    "Automatisch erkennen": "Detect automatically", "Ausgabe": "Output",
    "Gerät": "Device", "Rotation": "Rotation",
    "Normale Linux-Monitore funktionieren direkt. Proprietäre USB-Displays benötigen ein passendes OwnDash-Backend.":
        "Standard Linux monitors work directly. Proprietary USB displays require a compatible OwnDash backend.",
    "Display-Konfiguration aktualisiert": "Display configuration updated",
    "Display wird auf die neue Ausgabe umgeschaltet …": "Switching display to the new output …",
    "Standard-Monitor starten?": "Start standard monitor?",
    "Das Dashboard wird auf dem ausgewählten Monitor als randloses Vollbild angezeigt. Mit Esc oder F11 kannst du die Anzeige jederzeit beenden.":
        "The dashboard will be shown on the selected monitor as a borderless fullscreen view. Press Esc or F11 to stop the display at any time.",
    "Achtung: Du hast deinen Hauptmonitor ausgewählt.": "Warning: You selected your primary monitor.",
    "Der ausgewählte Monitor ist nicht verfügbar.": "The selected monitor is not available.",
    "Einfarbig": "Solid", "Verlauf": "Gradient", "Bild": "Image",
    "Immer": "Always", "Ab Warnwert": "From warning", "Nur kritisch": "Critical only",
    "Bogen": "Arc", "Halbkreis": "Semicircle", "Balken": "Bar", "Linie": "Line",
    "Anordnung": "Arrangement", "Deckkraft": "Opacity", "Eckenradius": "Corner radius",
    "Effektfarbe": "Effect color", "Einheit": "Unit", "Kritisch ab": "Critical from",
    "Licht 1": "Light 1", "Licht 2": "Light 2", "Licht 3": "Light 3",
    "Position X": "Position X", "Position Y": "Position Y", "Skalierung": "Scale",
    "Tempo": "Speed", "Typ": "Type", "Warnung ab": "Warning from",
    "Diagramm-Einstellungen": "Chart settings", "Motion & Regeln": "Motion & rules",
    "Tacho-Einstellungen": "Gauge settings", "Live Aurora": "Live Aurora",
    "Oben = Vordergrund": "Top = foreground",
    "Warnfarben weich einblenden": "Blend warning colors smoothly",
    "Bild direkt auf dem Display bearbeiten": "Edit image directly on the display",
    "Widget sperren": "Lock widget",
    "Tipp: Bilddatei direkt auf die Vorschau ziehen. Dann aktivieren, verschieben und unten rechts skalieren.":
        "Tip: Drag an image file directly onto the preview. Then enable, move and resize it from the lower-right handle.",
    "Arbeitsspeicher": "Memory", "Speicher": "Storage", "Netzwerk": "Network",
    "Temperatur": "Temperature", "Leistung": "Power", "Uhr": "Clock",
    "Tacho · CPU": "Gauge · CPU", "Tacho · GPU": "Gauge · GPU",
    "Tacho · Temperatur": "Gauge · Temperature", "Tacho · Leistung": "Gauge · Power",
    "Diagramm": "Chart", "Text": "Text",
}

def resolved_language(preference: str) -> str:
    if preference in {"de", "en"}:
        return preference
    system = QLocale.system().name().lower()
    return "de" if system.startswith("de") else "en"

def tr(text: str, language: str) -> str:
    if language == "en":
        return EN.get(text, text)
    return text

_SOURCE_ROLE = 0x0100 + 73

def _source(obj, key: str, current: str) -> str:
    prop = obj.property(key)
    if isinstance(prop, str) and prop:
        return prop
    obj.setProperty(key, current)
    return current

def retranslate_tree(root: QWidget, language: str) -> None:
    """Translate existing Qt controls while preserving canonical German source text."""
    for action in root.findChildren(QAction):
        source = _source(action, "_owndash_source_text", action.text())
        action.setText(tr(source, language))
        tip = action.toolTip()
        if tip:
            source_tip = _source(action, "_owndash_source_tip", tip)
            action.setToolTip(tr(source_tip, language))

    for widget in [root, *root.findChildren(QWidget)]:
        if isinstance(widget, (QLabel, QPushButton, QCheckBox, QGroupBox)):
            source = _source(widget, "_owndash_source_text", widget.text() if hasattr(widget, "text") else widget.title())
            if isinstance(widget, QGroupBox):
                widget.setTitle(tr(source, language))
            else:
                widget.setText(tr(source, language))
        elif isinstance(widget, QDockWidget):
            source = _source(widget, "_owndash_source_title", widget.windowTitle())
            widget.setWindowTitle(tr(source, language))
        elif isinstance(widget, QMenu):
            source = _source(widget, "_owndash_source_title", widget.title())
            widget.setTitle(tr(source, language))
        elif isinstance(widget, QToolBar):
            source = _source(widget, "_owndash_source_title", widget.windowTitle())
            widget.setWindowTitle(tr(source, language))
        elif isinstance(widget, QLineEdit):
            if widget.placeholderText():
                source = _source(widget, "_owndash_source_placeholder", widget.placeholderText())
                widget.setPlaceholderText(tr(source, language))
        elif isinstance(widget, QComboBox):
            for index in range(widget.count()):
                source = widget.itemData(index, _SOURCE_ROLE)
                if not isinstance(source, str):
                    source = widget.itemText(index)
                    widget.setItemData(index, source, _SOURCE_ROLE)
                widget.setItemText(index, tr(source, language))
        elif isinstance(widget, QTabWidget):
            sources = widget.property("_owndash_tab_sources")
            if not isinstance(sources, list) or len(sources) != widget.count():
                sources = [widget.tabText(i) for i in range(widget.count())]
                widget.setProperty("_owndash_tab_sources", sources)
            for index, source in enumerate(sources):
                widget.setTabText(index, tr(source, language))
