from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class DisplayError(RuntimeError):
    """Base exception for display transport errors."""


class DisplayNotFoundError(DisplayError):
    """Raised when no compatible device is present."""


class DisplayBusyError(DisplayError):
    """Raised when another service currently owns the display."""


class DisplayProtocolError(DisplayError):
    """Raised for authentication or USB protocol failures."""


@dataclass(frozen=True, slots=True)
class DisplayInfo:
    name: str
    width: int
    height: int
    refresh_hz: int | None = None


class DisplayBackend(ABC):
    """Hardware-independent display transport interface."""

    @abstractmethod
    def connect(self) -> DisplayInfo:
        raise NotImplementedError

    @abstractmethod
    def send_jpeg(self, payload: bytes) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError
