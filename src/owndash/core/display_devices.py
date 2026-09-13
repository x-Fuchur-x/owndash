from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DisplayDevice:
    backend: str
    device_id: str
    name: str
    native_width: int
    native_height: int
    transport: str
    rotation: int = 0

    @property
    def logical_size(self) -> tuple[int, int]:
        if self.rotation % 180:
            return self.native_height, self.native_width
        return self.native_width, self.native_height


def logical_size(width: int, height: int, rotation: int) -> tuple[int, int]:
    if rotation % 180:
        return int(height), int(width)
    return int(width), int(height)
