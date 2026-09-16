from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "packaging" / "appimage" / "build-appimage.sh"


def _build_script() -> str:
    return BUILD_SCRIPT.read_text(encoding="utf-8")


def test_appimage_build_bundles_native_libusb():
    text = _build_script()

    assert "libusb-1.0.so.0" in text
    assert 'cp -L "$LIBUSB"' in text
    assert '"$APPDIR/usr/bin/owndash/_internal/libusb-1.0.so.0"' in text


def test_appimage_build_fails_if_libusb_is_missing():
    text = _build_script()

    assert 'if [[ -z "$LIBUSB" || ! -e "$LIBUSB" ]]' in text
    assert "ERROR: libusb-1.0.so.0 was not found" in text
    assert "exit 3" in text


def test_appimage_build_verifies_bundled_libusb():
    text = _build_script()

    assert 'if [[ ! -f "$APPDIR/usr/bin/owndash/_internal/libusb-1.0.so.0" ]]' in text
    assert "ERROR: libusb-1.0.so.0 was not bundled into the AppImage." in text
