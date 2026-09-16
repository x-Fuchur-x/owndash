from __future__ import annotations

import os
from collections.abc import Mapping


def system_subprocess_env(
    extra: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return an environment suitable for launching host system programs.

    PyInstaller/AppImage may modify LD_LIBRARY_PATH so bundled libraries take
    precedence over libraries provided by the host system.  Passing that
    modified environment to programs such as systemctl, pkexec, lspci or
    nvidia-smi can make those programs load incompatible libraries from the
    OwnDash AppImage.

    PyInstaller preserves the original value in LD_LIBRARY_PATH_ORIG when it
    changes LD_LIBRARY_PATH.  Restore that value for external host programs.
    If there was no original value, remove LD_LIBRARY_PATH completely.
    """

    env = os.environ.copy()

    original_library_path = env.get("LD_LIBRARY_PATH_ORIG")

    if original_library_path is not None:
        env["LD_LIBRARY_PATH"] = original_library_path
    else:
        env.pop("LD_LIBRARY_PATH", None)

    if extra:
        env.update(extra)

    return env
