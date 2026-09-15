from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/appimage.yml").read_text(encoding="utf-8")


def test_beta3_appimage_is_built_on_debian_12_baseline():
    """Official AppImages must be built against the Debian 12 compatibility baseline."""
    assert "debian:12-slim" in WORKFLOW
    assert "libpython3.11" in WORKFLOW
    assert "packaging/appimage/build-appimage.sh" in WORKFLOW


def test_beta3_workflow_rejects_newer_glibc_requirements():
    """The release workflow must reject AppImages requiring newer than GLIBC 2.36."""
    assert "Verify GLIBC compatibility" in WORKFLOW
    assert "readelf --version-info" in WORKFLOW
    assert "GLIBC_2.36" in WORKFLOW


def test_beta3_workflow_runs_debian_12_smoke_test():
    """The finished AppImage must actually be launched on Debian 12."""
    assert "Test AppImage on Debian 12" in WORKFLOW
    assert "QT_QPA_PLATFORM=offscreen" in WORKFLOW
    assert "APPIMAGE_EXTRACT_AND_RUN=1" in WORKFLOW
    assert "timeout 10s" in WORKFLOW
    assert 'RC" -ne 124' in WORKFLOW
