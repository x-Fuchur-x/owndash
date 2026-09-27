import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from owndash.core.models import BackgroundConfig
from owndash.gui.canvas import DashboardCanvas


ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_canvas_can_remove_selected_background_image(app, tmp_path):
    image_path = tmp_path / "background.png"
    image = QImage(32, 24, QImage.Format_RGB32)
    image.fill(QColor("#224466"))
    assert image.save(str(image_path))

    canvas = DashboardCanvas()
    canvas.set_background_config(
        BackgroundConfig(
            mode="image",
            color="#101217",
            color2="#1b2433",
            image_path=str(image_path),
        )
    )
    canvas.set_background_edit_enabled(True)

    assert canvas.background_image_is_selected()
    assert canvas.remove_background_image()

    config = canvas.current_background_config()
    assert config.mode == "gradient"
    assert config.image_path == ""
    assert config.color == "#101217"
    assert config.color2 == "#1b2433"
    assert not canvas.background_image_is_selected()


def test_main_window_exposes_button_and_delete_key_path_for_background_image():
    assert 'self.remove_background_button = QPushButton("Bild entfernen")' in WINDOW
    assert "self.remove_background_button.clicked.connect(self._remove_background_image)" in WINDOW
    assert "if self.canvas.background_image_is_selected():" in WINDOW
    assert "self._remove_background_image()" in WINDOW
