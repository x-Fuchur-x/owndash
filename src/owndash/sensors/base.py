from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SensorProvider(ABC):
    @abstractmethod
    def snapshot(self) -> dict[str, Any]:
        raise NotImplementedError
