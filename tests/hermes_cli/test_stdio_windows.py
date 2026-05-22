"""Coverage for ``hermes_cli.stdio`` — the Windows UTF-8 stdio shim.

The module is mostly no-op on POSIX, but the platform-branching itself
is the worth-pinning invariant: if the POSIX no-op silently runs the
ctypes path, every Linux developer's CLI breaks."""
from __future__ import annotations

import sys

import pytest

import hermes_cli.stdio as stdio_mod


class TestIsWindows:
    def test_matches_sys_platform(self):
        assert stdio_mod.is_windows() == (sys.platform == "win32")


class TestConfigureWindowsStdio:
    def test_returns_false_on_posix(self):
        # The whole module body is a no-op on non-Windows; verify the
        # public function honours that contract.
        if not stdio_mod.is_windows():
            assert stdio_mod.configure_windows_stdio() is False

    def test_idempotent(self, monkeypatch):
        # Setting the flag once means a second call must return False.
        monkeypatch.setattr(stdio_mod, "_CONFIGURED", True, raising=True)
        assert stdio_mod.configure_windows_stdio() is False

    def test_disable_env_var_blocks_configuration(self, monkeypatch):
        monkeypatch.setattr(stdio_mod, "_CONFIGURED", False, raising=True)
        monkeypatch.setenv("HERMES_DISABLE_WINDOWS_UTF8", "1")
        # On POSIX or with the opt-out set, the function exits early.
        result = stdio_mod.configure_windows_stdio()
        # No state change should follow.
        if stdio_mod.is_windows():
            assert result is False
        else:
            assert result is False


class TestDefaultWindowsEditor:
    def test_returns_a_string(self):
        # On POSIX hosts shutil.which("notepad") is None so the helper
        # returns "" (documented graceful fallback).  Either branch must
        # produce a string.
        editor = stdio_mod._default_windows_editor()
        assert isinstance(editor, str)

    def test_returns_notepad_when_present(self, monkeypatch):
        import shutil
        monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/notepad")
        assert stdio_mod._default_windows_editor() == "notepad"

    def test_returns_empty_when_notepad_missing(self, monkeypatch):
        import shutil
        monkeypatch.setattr(shutil, "which", lambda name: None)
        assert stdio_mod._default_windows_editor() == ""
