"""Coverage for the pure helpers in ``hermes_cli.browser_connect``."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from hermes_cli.browser_connect import (
    DEFAULT_BROWSER_CDP_PORT,
    DEFAULT_BROWSER_CDP_URL,
    _chrome_debug_args,
    chrome_debug_data_dir,
    get_chrome_debug_candidates,
    manual_chrome_debug_command,
)


class TestConstants:
    def test_default_port_is_9222(self):
        assert DEFAULT_BROWSER_CDP_PORT == 9222

    def test_default_url_uses_loopback(self):
        assert DEFAULT_BROWSER_CDP_URL.startswith("http://127.0.0.1:")


class TestChromeDebugDataDir:
    def test_returns_path_under_hermes_home(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        assert chrome_debug_data_dir() == str(tmp_path / "chrome-debug")


class TestChromeDebugArgs:
    def test_includes_remote_debugging_port_and_user_data_dir(self):
        args = _chrome_debug_args(9333)
        assert "--remote-debugging-port=9333" in args
        assert any(a.startswith("--user-data-dir=") for a in args)
        assert "--no-first-run" in args
        assert "--no-default-browser-check" in args


class TestGetChromeDebugCandidates:
    def test_returns_only_existing_files(self):
        # Use a known-existing path (/bin/sh on Linux) as a fake candidate.
        with patch(
            "hermes_cli.browser_connect._LINUX_BIN_NAMES", ("sh",),
        ), patch(
            "hermes_cli.browser_connect._DARWIN_APPS", (),
        ), patch(
            "hermes_cli.browser_connect.shutil.which", return_value="/bin/sh",
        ):
            candidates = get_chrome_debug_candidates("Linux")
        # /bin/sh exists on every Linux test host.
        assert all(c for c in candidates)

    def test_deduplicates_paths(self):
        with patch(
            "hermes_cli.browser_connect.shutil.which", return_value="/bin/sh",
        ), patch(
            "hermes_cli.browser_connect._LINUX_BIN_NAMES", ("sh", "bash"),
        ), patch(
            "hermes_cli.browser_connect._DARWIN_APPS", (),
        ):
            candidates = get_chrome_debug_candidates("Linux")
            # Two distinct candidates from shutil.which would both equal
            # "/bin/sh" → after the dedup loop only one should remain.
            assert len(candidates) == 1


class TestManualChromeDebugCommand:
    def test_returns_a_command_when_candidate_exists(self):
        with patch(
            "hermes_cli.browser_connect.get_chrome_debug_candidates",
            return_value=["/usr/bin/google-chrome"],
        ):
            cmd = manual_chrome_debug_command(port=9999, system="Linux")
        assert cmd is not None
        assert "9999" in cmd
        assert "google-chrome" in cmd

    def test_darwin_returns_open_command_when_no_candidate(self):
        with patch(
            "hermes_cli.browser_connect.get_chrome_debug_candidates",
            return_value=[],
        ):
            cmd = manual_chrome_debug_command(port=9222, system="Darwin")
        assert cmd is not None
        assert "open -a" in cmd
        assert "9222" in cmd
