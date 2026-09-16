from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

README = (ROOT / "README.md").read_text(encoding="utf-8")
PACKAGING_README = (ROOT / "packaging/README.md").read_text(encoding="utf-8")
DESKTOP = (ROOT / "packaging/org.owndash.OwnDash.desktop").read_text(encoding="utf-8")
BUILD_SCRIPT = (ROOT / "packaging/appimage/build-appimage.sh").read_text(encoding="utf-8")
RELEASE_CHECKLIST = (ROOT / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_beta3_readme_documents_appimage_minimum_baseline():
    assert "GLIBC 2.36" in README
    assert "x86-64" in README
    assert "Python or PySide6" in README


def test_beta3_readme_distinguishes_real_hardware_and_ci_testing():
    assert "Bazzite" in README
    assert "Debian 12" in README
    assert "CI" in README


def test_beta3_packaging_docs_explain_release_compatibility_baseline():
    assert "Debian 12" in PACKAGING_README
    assert "GLIBC 2.36" in PACKAGING_README
    assert "smoke test" in PACKAGING_README.lower()


def test_beta3_desktop_uses_single_main_category():
    assert "Categories=System;Qt;" in DESKTOP
    assert "Categories=Utility;System;Qt;" not in DESKTOP


def test_beta3_appstream_metadata_exists_and_is_packaged():
    metainfo = ROOT / "packaging/org.owndash.OwnDash.metainfo.xml"

    assert metainfo.is_file()
    assert "org.owndash.OwnDash" in metainfo.read_text(encoding="utf-8")

    # Keep the canonical AppStream source file as .metainfo.xml.
    assert "packaging/org.owndash.OwnDash.metainfo.xml" in BUILD_SCRIPT

    # appimagetool currently expects the legacy .appdata.xml filename
    # inside usr/share/metainfo.
    assert "usr/share/metainfo" in BUILD_SCRIPT
    assert "org.owndash.OwnDash.appdata.xml" in BUILD_SCRIPT


def test_beta3_release_checklist_protects_appimage_compatibility():
    assert "GLIBC 2.36" in RELEASE_CHECKLIST
    assert "Debian 12" in RELEASE_CHECKLIST
    assert "GitHub" in RELEASE_CHECKLIST


def test_project_description_is_not_usb_only():
    assert (
        'description = "Visual Linux editor and runtime for customizable hardware dashboards"'
        in PYPROJECT
    )
