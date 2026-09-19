import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication
from owndash.gui.canvas import CanvasSize, DashboardCanvas, WidgetItem
from owndash.core.models import WidgetConfig


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def paint(item, width, height, factor=1):
    image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    painter.scale(factor, factor)
    item.set_export_mode(True)
    item.paint(painter, None)
    painter.end()
    return image


@pytest.mark.parametrize('kind', ['text', 'gauge_cpu', 'chart'])
@pytest.mark.parametrize('factor', [0.5, 2.0])
def test_widget_contents_scale_together(app, kind, factor):
    canvas = DashboardCanvas(size=CanvasSize(400, 200))
    canvas.snap_enabled = False
    item = canvas.add_widget(kind, 'CPU', position=QPointF(0,0), width=320, height=160,
                             options={'text':'42 %', 'animation':'scanner'})
    item._history = [10,70,30,90]
    expected = paint(item, int(320*factor), int(160*factor), factor)
    canvas.set_canvas_size(int(400*factor), int(200*factor))
    actual = paint(item, int(320*factor), int(160*factor))
    assert actual == expected
    canvas._animation_timer.stop()
    canvas.deleteLater()


def test_small_widgets_keep_proportions_on_fit_and_profile_normalization(app):
    canvas = DashboardCanvas(size=CanvasSize(480,1920))
    item = canvas.add_widget('text','x',position=QPointF(0,0),width=80,height=40)
    canvas.set_canvas_size(240,960)
    assert (item.rect().width(),item.rect().height()) == (40,20)
    saved = WidgetConfig('text', item.x(), item.y(), item.rect().width(),item.rect().height(),options=dict(item.options))
    restored = saved.normalized(240,960)
    assert (restored.width,restored.height) == (40,20)
    canvas.set_canvas_size(480,1920)
    assert (item.rect().width(),item.rect().height()) == (80,40)
    canvas._animation_timer.stop()
    canvas.deleteLater()

@pytest.mark.parametrize('rotation', [0, 90, 180, 270])
@pytest.mark.parametrize('size', [(1920, 480), (480, 1920), (240, 320)])
def test_shutdown_uses_exact_frame_size_and_upright_layout(app, rotation, size):
    from PySide6.QtGui import QIcon, QTransform
    from owndash.gui.shutdown_frame import render_shutdown_image
    width, height = size
    encoded = render_shutdown_image(width, height, rotation, QIcon())
    assert (encoded.width(), encoded.height()) == size
    visible = encoded.transformed(QTransform().rotate(rotation))
    expected_size = (height, width) if rotation in (90, 270) else size
    assert (visible.width(), visible.height()) == expected_size
    # Shutdown must follow the dashboard canvas through the same backend rotation.
    expected = render_shutdown_image(width, height, 0, QIcon()).transformed(QTransform().rotate(rotation))
    # Font-cache rasterization can differ slightly between first and later draws.
    from PIL import Image, ImageChops, ImageStat
    def pil(image):
        rgba = image.convertToFormat(QImage.Format_RGBA8888)
        return Image.frombytes('RGBA', (rgba.width(), rgba.height()), bytes(rgba.bits()))
    assert max(ImageStat.Stat(ImageChops.difference(pil(visible), pil(expected))).mean) < 1



def test_fractional_geometry_survives_profile_roundtrip(app):
    from owndash.core.models import Profile
    widget = WidgetConfig('text', 1.25, 2.75, 40.5, 20.25, options={'_content_scale': .5})
    profile = Profile(widgets=[widget])
    restored = Profile.from_json(profile.to_json()).widgets[0].normalized(240, 960)
    assert (restored.x, restored.y, restored.width, restored.height) == (1.25, 2.75, 40.5, 20.25)


def test_theme_change_preserves_fitted_widget_scale(app):
    from owndash.themes import ThemeManager
    canvas = DashboardCanvas(size=CanvasSize(480, 1920))
    item = canvas.add_widget('text', 'x', position=QPointF(0, 0), width=80, height=40)
    canvas.set_canvas_size(240, 960)
    canvas.apply_theme(ThemeManager.get('Neon Cyan'))
    assert item.options['_content_scale'] == .5
    saved = WidgetConfig('text', item.x(), item.y(), item.rect().width(), item.rect().height(), options=dict(item.options))
    restored = saved.normalized(240, 960)
    assert (restored.width, restored.height) == (40, 20)
    canvas._animation_timer.stop()
    canvas.deleteLater()
