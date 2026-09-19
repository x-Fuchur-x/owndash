"""Resolution-independent shutdown artwork in the display's visible orientation."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QIcon, QImage, QLinearGradient, QPainter, QPen, QRadialGradient

from owndash import APP_NAME, __version__


def render_shutdown_image(
    width: int, height: int, rotation: int, icon: QIcon, *,
    status: str = "Dashboard paused", detail: str = "OwnDash closed",
    farewell: str = "See you soon.",
) -> QImage:
    # The canvas already describes the user-facing orientation. Resolution from
    # the controller alone cannot tell us how the panel is physically mounted.
    # Let the backend rotate this frame exactly like ordinary dashboard frames.
    del rotation
    w, h = width, height
    image = QImage(w, h, QImage.Format_RGB32)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    gradient = QLinearGradient(0, 0, w, h)
    gradient.setColorAt(0, QColor('#10253f'))
    gradient.setColorAt(1, QColor('#060c18'))
    painter.fillRect(image.rect(), gradient)
    short = min(w, h)
    margin = short * .045
    card = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)
    painter.setBrush(QColor('#0b1526'))
    painter.setPen(QPen(QColor('#387dd1'), max(1, short * .004)))
    painter.drawRoundedRect(card, short * .055, short * .055)
    if h >= w * 1.5:
        # Use the height of bar displays deliberately, instead of centering a
        # compact landscape composition within a tall canvas.
        size = min(w * .82, h * .28)
        icon_rect = QRectF((w - size) / 2, h * .055, size, size)
        halo = QRadialGradient(icon_rect.center(), size * .78)
        halo.setColorAt(0, QColor(55, 133, 255, 110))
        halo.setColorAt(.55, QColor(40, 104, 220, 45))
        halo.setColorAt(1, QColor(40, 104, 220, 0))
        painter.save()
        painter.setClipRect(card.adjusted(2, 2, -2, -2))
        painter.fillRect(card, halo)
        painter.restore()
        painter.drawPixmap(icon_rect.toRect(), icon.pixmap(round(size), round(size)))

        def text_line(text, top, height, pixels, color, bold=False):
            area = QRectF(w * .085, top, w * .83, height)
            font = QFont("DejaVu Sans")
            font.setBold(bold)
            font.setPixelSize(max(1, round(pixels)))
            flags = Qt.AlignCenter | Qt.TextWordWrap
            while font.pixelSize() > 1:
                bounds = QFontMetricsF(font, image).boundingRect(area, flags, text)
                if bounds.width() <= area.width() and bounds.height() <= area.height():
                    break
                font.setPixelSize(font.pixelSize() - 1)
            painter.setFont(font)
            painter.setPen(QColor(color))
            painter.drawText(area, flags, text)

        title_top = icon_rect.bottom() + h * .015
        text_line(APP_NAME, title_top, h * .075, w * .17, '#f4f8ff', True)
        divider_y = max(h * .35, title_top + h * .09)
        painter.setPen(QPen(QColor('#438de6'), max(1, w * .004)))
        painter.drawLine(round(w * .19), round(divider_y), round(w * .81), round(divider_y))
        # The status is intentionally two lines on tall panels, in either UI language.
        portrait_status = status.replace(' ', '\n', 1)
        text_line(portrait_status, divider_y + h * .045, h * .18, w * .145, '#c3dcff', True)
        text_line(detail, divider_y + h * .24, h * .12, w * .09, '#b5c5dc')
        text_line(farewell, h * .82, h * .07, w * .09, '#c3dcff')
        text_line(f"Version {__version__}", h * .935, h * .035, w * .045, '#8ea4c2')
        painter.end()
        return image

    if w >= h * 1.5:
        size = h * .72
        icon_rect = QRectF(margin * 2, (h - size) / 2, size, size)
        left = icon_rect.right() + short * .09
        text_area = QRectF(left, h * .15, w - left - margin * 2, h * .70)
        alignment = Qt.AlignLeft
    else:
        size = min(w * .70, h * .40)
        gap = short * .12
        text_height = min(w * .85, h * .38)
        top = (h - size - gap - text_height) / 2
        icon_rect = QRectF((w - size) / 2, top, size, size)
        text_area = QRectF(margin * 2, icon_rect.bottom() + gap,
                           w - margin * 4, text_height)
        alignment = Qt.AlignHCenter
    painter.drawPixmap(icon_rect.toRect(), icon.pixmap(round(size), round(size)))
    for text, offset, fraction, color, bold in (
        (APP_NAME, 0, .35, '#f4f8ff', True),
        (status, .37, .23, '#a6c7ff', False),
        (detail, .62, .23, '#94a8c4', False),
        (farewell, .87, .13, '#778dab', False),
    ):
        area = QRectF(text_area.x(), text_area.y() + text_area.height() * offset,
                      text_area.width(), text_area.height() * fraction)
        font = QFont("DejaVu Sans")
        font.setBold(bold)
        pixels = max(1, round(min(area.height() * .78, short * (.30 if bold else .15))))
        font.setPixelSize(pixels)
        metrics = QFontMetricsF(font, image)
        wrap = text == detail and metrics.horizontalAdvance(text) > area.width()
        lines = 2 if wrap else 1
        fit = min(1.0, area.width() * lines / max(1, metrics.horizontalAdvance(text)),
                  area.height() / (lines * max(1, metrics.height())))
        font.setPixelSize(max(1, int(pixels * fit)))
        flags = alignment | Qt.AlignVCenter
        if wrap:
            flags |= Qt.TextWordWrap
            while font.pixelSize() > 1 and QFontMetricsF(font, image).boundingRect(area, flags, text).height() > area.height():
                font.setPixelSize(font.pixelSize() - 1)
        painter.setFont(font)
        painter.setPen(QColor(color))
        painter.drawText(area, flags, text)
    footer = QRectF(margin * 2, h - margin - short * .065,
                    w - margin * 4, short * .05)
    font = QFont("DejaVu Sans")
    font.setPixelSize(max(1, round(short * .035)))
    painter.setFont(font)
    painter.setPen(QColor('#778dab'))
    painter.drawText(footer, Qt.AlignRight | Qt.AlignVCenter, f"Version {__version__}")
    painter.end()
    return image
