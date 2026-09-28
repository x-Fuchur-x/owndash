from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session", autouse=True)
def qapplication():
    """Keep one Qt application alive for all GUI/rendering tests."""
    app = QApplication.instance() or QApplication(sys.argv[:1])
    yield app
