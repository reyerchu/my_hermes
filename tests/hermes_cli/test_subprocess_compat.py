"""Coverage for ``hermes_cli._subprocess_compat`` — Windows subprocess
helpers that are no-ops on POSIX.  The platform branches are easy to get
wrong; pin every branch so a refactor on macOS doesn't silently break
Windows users."""
from __future__ import annotations

import sys

import pytest

from hermes_cli import _subprocess_compat as compat


class TestIsWindows:
    def test_flag_matches_current_platform(self):
        assert compat.IS_WINDOWS == (sys.platform == "win32")


class TestResolveNodeCommand:
    def test_resolves_an_installed_command_to_absolute_path(self, monkeypatch):
        monkeypatch.setattr(compat.shutil, "which", lambda _: "/usr/bin/node")
        assert compat.resolve_node_command("node", ["-v"]) == [
            "/usr/bin/node",
            "-v",
        ]

    def test_returns_bare_name_when_command_missing(self, monkeypatch):
        monkeypatch.setattr(compat.shutil, "which", lambda _: None)
        assert compat.resolve_node_command("npm", ["install"]) == [
            "npm",
            "install",
        ]

    def test_argv_is_preserved_in_order(self, monkeypatch):
        monkeypatch.setattr(compat.shutil, "which", lambda _: "/x/npx")
        assert compat.resolve_node_command(
            "npx", ["create-vite", "--", "--ts"]
        ) == ["/x/npx", "create-vite", "--", "--ts"]

    def test_empty_argv_works(self, monkeypatch):
        monkeypatch.setattr(compat.shutil, "which", lambda _: "/bin/node")
        assert compat.resolve_node_command("node", []) == ["/bin/node"]


class TestWindowsDetachFlags:
    def test_returns_zero_on_posix(self, monkeypatch):
        monkeypatch.setattr(compat, "IS_WINDOWS", False)
        assert compat.windows_detach_flags() == 0

    def test_returns_or_of_three_constants_on_windows(self, monkeypatch):
        monkeypatch.setattr(compat, "IS_WINDOWS", True)
        flags = compat.windows_detach_flags()
        expected = (
            compat._CREATE_NEW_PROCESS_GROUP
            | compat._DETACHED_PROCESS
            | compat._CREATE_NO_WINDOW
        )
        assert flags == expected


class TestWindowsHideFlags:
    def test_returns_zero_on_posix(self, monkeypatch):
        monkeypatch.setattr(compat, "IS_WINDOWS", False)
        assert compat.windows_hide_flags() == 0

    def test_returns_only_create_no_window_on_windows(self, monkeypatch):
        monkeypatch.setattr(compat, "IS_WINDOWS", True)
        assert compat.windows_hide_flags() == compat._CREATE_NO_WINDOW


class TestWindowsDetachPopenKwargs:
    def test_returns_start_new_session_on_posix(self, monkeypatch):
        monkeypatch.setattr(compat, "IS_WINDOWS", False)
        kwargs = compat.windows_detach_popen_kwargs()
        assert kwargs == {"start_new_session": True}

    def test_returns_creationflags_on_windows(self, monkeypatch):
        monkeypatch.setattr(compat, "IS_WINDOWS", True)
        kwargs = compat.windows_detach_popen_kwargs()
        assert kwargs == {"creationflags": compat.windows_detach_flags()}
        # The flags themselves are non-zero on Windows.
        assert kwargs["creationflags"] != 0
