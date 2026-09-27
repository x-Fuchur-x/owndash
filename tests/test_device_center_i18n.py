from owndash.gui.device_center_window import DeviceCenterWindow


class EnglishContext:
    language = "en"

    @staticmethod
    def _t(text: str) -> str:
        return text


def test_device_center_english_copy_covers_primary_ui_terms():
    context = EnglishContext()
    expected = {
        "Geräteinformationen …": "Device Information …",
        "Geräteinformationen": "Device Information",
        "USB & Zugriff": "USB & Access",
        "Funktionen": "Capabilities",
        "Letzte Aktivität": "Last activity",
        "Verbunden": "Connected",
        "Nicht verbunden": "Not connected",
        "Nicht unterstützt": "Unsupported",
        "Noch nicht verifiziert": "Not yet verified",
        "Aktualisieren": "Refresh",
        "Diagnosebericht kopieren": "Copy diagnostic report",
    }
    for source, translated in expected.items():
        assert DeviceCenterWindow._device_t(context, source) == translated
