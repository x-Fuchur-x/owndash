from pathlib import Path

from owndash import APP_ID


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_desktop_icon_matches_app_id():
    text = (project_root() / "packaging" / f"{APP_ID}.desktop").read_text(encoding="utf-8")
    assert f"Icon={APP_ID}" in text
    assert f"StartupWMClass={APP_ID}" in text


def test_launcher_installs_app_id_icon_and_removes_legacy_name():
    text = (project_root() / "run-owndash.sh").read_text(encoding="utf-8")
    assert f"{APP_ID}.svg" in text
    assert 'rm -f "$ICON_DIR/owndash.svg"' in text
    assert "kbuildsycoca6" in text
