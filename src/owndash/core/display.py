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
class DisplayCapabilities:
    hardware_brightness: bool = False
    device_version: bool = False
    panel_info: bool = False
    expansion_mode: bool = False
    startup_image: bool = False
    startup_video: bool = False
    hardware_screen_off: bool = False
    firmware_upgrade: bool = False


@dataclass(frozen=True, slots=True)
class DisplayInfo:
    name: str
    width: int
    height: int
    refresh_hz: int | None = None
    device_version: str | None = None
    expansion_mode: bool | None = None


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

    def get_capabilities(self) -> DisplayCapabilities:
        """Return optional controls supported by this backend."""
        return DisplayCapabilities()

    def get_device_version(self) -> str | None:
        return None

    def set_brightness(self, percent: int) -> None:
        raise DisplayProtocolError("Hardware-Helligkeit wird von diesem Display nicht unterstützt.")

    def get_expansion_mode(self) -> bool | None:
        return None

    def set_expansion_mode(self, enabled: bool) -> None:
        raise DisplayProtocolError("Expansion Screen Mode wird von diesem Display nicht unterstützt.")
