from __future__ import annotations

import os

from owndash.core.subprocess_env import system_subprocess_env


def test_system_subprocess_env_restores_original_library_path(monkeypatch):
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/owndash-appimage-libs")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/usr/lib64:/usr/lib")

    env = system_subprocess_env()

    assert env["LD_LIBRARY_PATH"] == "/usr/lib64:/usr/lib"
    assert env["LD_LIBRARY_PATH_ORIG"] == "/usr/lib64:/usr/lib"


def test_system_subprocess_env_removes_appimage_library_path_without_original(
    monkeypatch,
):
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/owndash-appimage-libs")
    monkeypatch.delenv("LD_LIBRARY_PATH_ORIG", raising=False)

    env = system_subprocess_env()

    assert "LD_LIBRARY_PATH" not in env


def test_system_subprocess_env_does_not_modify_parent_environment(monkeypatch):
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/owndash-appimage-libs")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/usr/lib64")

    system_subprocess_env()

    assert os.environ["LD_LIBRARY_PATH"] == "/tmp/owndash-appimage-libs"
    assert os.environ["LD_LIBRARY_PATH_ORIG"] == "/usr/lib64"


def test_system_subprocess_env_accepts_extra_variables(monkeypatch):
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)
    monkeypatch.delenv("LD_LIBRARY_PATH_ORIG", raising=False)

    env = system_subprocess_env({"OWNDASH_TEST": "1"})

    assert env["OWNDASH_TEST"] == "1"
