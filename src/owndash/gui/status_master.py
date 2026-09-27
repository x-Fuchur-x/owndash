"""Embedded portrait master artwork used by the system-state renderer."""
from __future__ import annotations

import base64
from functools import lru_cache

from PySide6.QtGui import QImage

from ._status_master_data_00 import DATA as DATA_00
from ._status_master_data_01 import DATA as DATA_01
from ._status_master_data_02 import DATA as DATA_02
from ._status_master_data_03 import DATA as DATA_03
from ._status_master_data_04 import DATA as DATA_04
from ._status_master_data_05 import DATA as DATA_05


@lru_cache(maxsize=1)
def _master_image() -> QImage:
    """Return the single embedded 480x1920 portrait master image."""
    payload = base64.b64decode(DATA_00 + DATA_01 + DATA_02 + DATA_03 + DATA_04 + DATA_05)
    image = QImage.fromData(payload, "JPG")
    if image.isNull() or image.width() != 480 or image.height() != 1920:
        raise RuntimeError("invalid OwnDash system-state portrait master artwork")
    return image.convertToFormat(QImage.Format_RGB32)
