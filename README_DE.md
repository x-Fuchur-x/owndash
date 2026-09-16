<p align="center">
  <img src="docs/images/owndash-hero.svg" alt="OwnDash — Your display. Your design." width="100%">
</p>

<p align="center">
  <a href="README.md">English</a> · <strong>Deutsch</strong>
</p>

<p align="center">
  <a href="https://github.com/x-Fuchur-x/owndash/releases/tag/v0.14.0-beta.3"><img alt="Release" src="https://img.shields.io/badge/release-0.14.0%20Beta%203-5577FF?style=for-the-badge"></a>
  <img alt="Linux" src="https://img.shields.io/badge/Linux-x86__64-0B0E15?style=for-the-badge&logo=linux&logoColor=white">
  <img alt="AppImage" src="https://img.shields.io/badge/AppImage-ready-1593FF?style=for-the-badge&logo=appimage&logoColor=white">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <a href="LICENSE"><img alt="MIT-Lizenz" src="https://img.shields.io/badge/Lizenz-MIT-A05CFF?style=for-the-badge"></a>
</p>

# OwnDash

**Erstellen. Anpassen. Anzeigen.**

OwnDash ist ein visueller Open-Source-Dashboard-Editor für Linux. Erstelle Hardware-Monitoring-Dashboards per Drag & Drop, verbinde Live-Systemsensoren und gib das Ergebnis auf einem kompatiblen USB-Display oder jedem von Linux erkannten Monitor aus — ohne dich mit Python, `hwmon`, USB-Protokollen oder Linux-Interna beschäftigen zu müssen.

> **Aktuelle Version: OwnDash 0.14.0 Beta 3**  
> Startfertiges x86-64-AppImage · Debian-12-/GLIBC-2.36-Kompatibilitätsbasis · direkte ArtInChip-/VSDISPLAY-USB-Ausgabe auf echter Hardware verifiziert.

<p align="center">
  <a href="https://github.com/x-Fuchur-x/owndash/releases/tag/v0.14.0-beta.3"><strong>OwnDash 0.14.0 Beta 3 herunterladen</strong></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/x-Fuchur-x/owndash/releases">Alle Releases</a>
  &nbsp;·&nbsp;
  <a href="ROADMAP.md">Roadmap</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/x-Fuchur-x/owndash/issues">Issues</a>
</p>

## Warum OwnDash?

OwnDash richtet sich an alle, die ein eigenes Systemdisplay möchten, ohne dass die Einrichtung zum Terminal-Projekt wird.

- **Visueller Editor** — Dashboards per Drag & Drop mit direkter Vorschau gestalten.
- **Echte Linux-Telemetrie** — CPU, GPU, RAM, Speicher, Netzwerk, Temperaturen, Leistung und weitere Werte, sofern die Hardware sie bereitstellt.
- **Flexible Widgets** — Anzeigen, Diagramme, Sparklines, Uhren, Text, Bilder, Hintergründe, Themes und animierte Elemente.
- **Mehrere Dashboard-Seiten** — verschiedene Layouts organisieren und automatisch wechseln.
- **Sensorabhängiges Verhalten** — Animationen, Regeln und Warnzustände können auf Live-Werte reagieren.
- **Zwei Ausgabewege** — normale Linux-Monitore und kompatible direkte USB-Displays.
- **Einsteigerfreundliche Einrichtung** — Ersteinrichtungs-Assistent, Kompatibilitätsprüfung, Diagnosen und grafische USB-Rechte-Einrichtung.
- **Linux-nativer Ansatz** — basiert auf verbreiteten Linux-Schnittstellen statt auf einer einzelnen Distribution.
- **Deutsche und englische Oberfläche** — inklusive System-, Hell- und Dunkelmodus.
- **Open Source** — MIT-lizenziert und langfristig für zusätzliche Hardware-Backends ausgelegt.

## OwnDash in Aktion

<table>
  <tr>
    <td width="50%" valign="top">
      <img src="docs/images/owndash-editor.png" alt="Visueller OwnDash-Dashboard-Editor">
      <br><strong>Visueller Dashboard-Editor</strong><br>
      Dashboards erstellen und anpassen, ohne Konfigurationsdateien von Hand bearbeiten zu müssen.
    </td>
    <td width="50%" valign="top">
      <img src="docs/images/owndash-hardware.jpg" alt="OwnDash auf einem echten USB-Sensordisplay">
      <br><strong>Ausgabe auf echter Hardware</strong><br>
      OwnDash auf einem kompatiblen ArtInChip-/VSDISPLAY-USB-Sensordisplay.
    </td>
  </tr>
</table>

## Display-Unterstützung

OwnDash bietet aktuell zwei Ausgabewege:

### Normale Linux-Monitore

Displays, die Linux bereits als normalen Bildschirm erkennt, können über HDMI, DisplayPort, USB-C und andere Standard-Ausgänge verwendet werden. OwnDash kann das Dashboard in einem eigenen Ausgabefenster mit Fullscreen-Sicherheitsfunktionen darstellen.

### Direkte ArtInChip-/VSDISPLAY-USB-Ausgabe

Kompatible ArtInChip-basierte Sensordisplays können direkt über USB angesteuert werden, ohne als normaler Monitor im System erscheinen zu müssen. Das offizielle AppImage bringt die benötigte `libusb-1.0.so.0`-Laufzeitbibliothek mit.

Andere proprietäre USB-only-Displays benötigen ein eigenes Backend und Protokollunterstützung. Eine breitere Hardware-Unterstützung ist Teil der langfristigen Projektrichtung — siehe [Roadmap](ROADMAP.md).

## Download & Schnellstart

Die offizielle Version wird als eigenständiges **x86-64-AppImage** bereitgestellt.

**Aktuelle Datei:** `OwnDash-0.14.0-Beta-3-x86_64.AppImage`

1. AppImage vom [OwnDash-0.14.0-Beta-3-Release](https://github.com/x-Fuchur-x/owndash/releases/tag/v0.14.0-beta.3) herunterladen.
2. Falls erforderlich, die Datei ausführbar machen.
3. OwnDash per Doppelklick starten.
4. Den Ersteinrichtungs- und Kompatibilitäts-Assistenten durchlaufen.
5. Dashboard erstellen und Ausgabedisplay auswählen.

Bei Verwendung des offiziellen AppImages ist keine separate Installation von Python oder PySide6 erforderlich.

Für kompatible direkte USB-Displays kann OwnDash die benötigte USB-Berechtigungsregel grafisch über die normale Administrator-Authentifizierung des Desktops installieren. Beim Programmstart wird kein privilegierter Befehl automatisch ausgeführt.

## Sensoren & Kompatibilität

OwnDash verwendet verbreitete Linux-Schnittstellen wie `/proc`, `sysfs`, `hwmon`, DRM und `powercap`. Welche Sensoren verfügbar sind, hängt deshalb von Kernel, Treiber und Hardware ab — nicht von einer bestimmten Linux-Distribution.

Ein fehlender optionaler Messwert gilt **nicht** als Programmfehler. Eine GPU kann zum Beispiel Auslastung und Temperatur liefern, aber keine Leistungsaufnahme; OwnDash funktioniert weiter und kennzeichnet lediglich diesen einzelnen Wert als nicht verfügbar.

Zusätzliche NVIDIA-Telemetrie kann über `nvidia-smi` genutzt werden, sofern vorhanden. AMDGPU-VRAM-Auslastung sowie belegter und gesamter VRAM in GiB werden unterstützt, wenn die benötigten sysfs-Zähler verfügbar sind.

Unter **Hilfe → System- und Sensorinformationen** zeigt OwnDash detailliert an, welche Funktionen erkannt wurden.

### Aktuelle AppImage-Basis

- Linux auf **x86-64**
- **GLIBC 2.36 oder neuer**
- Grafische Linux-Desktopumgebung
- Offizielle Releases werden auf einer **Debian-12-Kompatibilitätsbasis** gebaut

Beta 3 enthält eine automatisierte GLIBC-Kompatibilitätsprüfung sowie einen AppImage-Starttest in einer sauberen Debian-12-Umgebung. Hardware-, Sensor-, Grafik- und USB-Funktionen können sich trotzdem je nach System unterscheiden.

## Getestete Hardware & Plattform

Beta 3 wurde praktisch getestet mit:

- Bazzite Linux
- KDE Plasma
- AMD-CPU-/GPU-Hardware
- x86-64
- kompatibler direkter ArtInChip-/VSDISPLAY-USB-Hardware
- normaler Linux-Monitorausgabe

OwnDash benötigt **weder Bazzite noch KDE**. Rückmeldungen zu anderen Distributionen, Desktopumgebungen, GPUs und Displays sind ausdrücklich willkommen.

## Aus dem Quellcode starten

Für den Start aus dem Quellcode wird Python **3.11 oder neuer** benötigt.

```bash
python -m pip install -e .
owndash
```

Die zentralen Abhängigkeiten sind in `pyproject.toml` definiert und umfassen PySide6, Pillow, PyUSB und cryptography.

## Projektlinks

- **[Roadmap](ROADMAP.md)** — geplante Entwicklung Richtung 1.0 und weitere Display-Unterstützung
- **[Changelog](CHANGELOG.md)** — veröffentlichte Funktionen und Versionshistorie
- **[Contributing](CONTRIBUTING.md)** — Hinweise zum Mitmachen
- **[Issues](https://github.com/x-Fuchur-x/owndash/issues)** — Fehler und Funktionswünsche
- **[Releases](https://github.com/x-Fuchur-x/owndash/releases)** — AppImages und Release Notes

## Beta-Status

OwnDash befindet sich weiterhin in der Beta-Phase. Fehler und Kompatibilitätsprobleme sind möglich. Rückmeldungen aus unterschiedlichen Linux-Distributionen, Hardware-Konfigurationen und Display-Typen sind während dieser Phase besonders wertvoll.

## Lizenz

OwnDash wird unter der **MIT-Lizenz** veröffentlicht. Drittanbieter-Komponenten und Danksagungen sind in [`THIRD_PARTY.md`](THIRD_PARTY.md) dokumentiert.

<p align="center">
  <strong>Your display. Your design.</strong><br>
  Für Linux · Open Source · Dein Dashboard
</p>

Copyright © 2026 **Markus Rosinski**
