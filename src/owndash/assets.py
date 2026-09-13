from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path
from contextlib import contextmanager
from collections.abc import Iterator


@contextmanager
def app_icon_path() -> Iterator[Path]:
    """Yield a filesystem path to the packaged OwnDash application icon."""
    resource = files("owndash").joinpath("assets", "owndash.svg")
    with as_file(resource) as path:
        yield path
