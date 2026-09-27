from pathlib import Path


def test_appimage_workflow_builds_all_feature_branches():
    workflow = Path(".github/workflows/appimage.yml").read_text(encoding="utf-8")

    assert '- "feat/**"' in workflow
    assert '- "feat/device-center-diagnostics"' not in workflow
