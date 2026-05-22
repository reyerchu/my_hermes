"""Coverage for the pure helpers in ``tools.browser_tool`` — Homebrew
discovery and PATH merge logic that runs on every agent-browser invocation."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.browser_tool import (
    _discover_homebrew_node_dirs,
    _merge_browser_path,
)


class TestDiscoverHomebrewNodeDirs:
    def test_returns_tuple(self):
        out = _discover_homebrew_node_dirs()
        assert isinstance(out, tuple)

    def test_returns_empty_when_homebrew_dir_missing(self):
        # Patch os.path.isdir to claim /opt/homebrew/opt doesn't exist.
        with patch(
            "tools.browser_tool.os.path.isdir",
            side_effect=lambda p: False,
        ):
            assert _discover_homebrew_node_dirs() == ()

    def test_on_real_host_returns_only_homebrew_paths_or_empty(self):
        # On Linux CI hosts /opt/homebrew/opt doesn't exist and the result
        # is empty.  On macOS Homebrew hosts it may yield paths under
        # /opt/homebrew/opt/node@.../bin.  Either way the output is a
        # tuple of strings (the contract).
        out = _discover_homebrew_node_dirs()
        assert isinstance(out, tuple)
        for entry in out:
            assert isinstance(entry, str)
            assert "/opt/homebrew/opt/" in entry
            assert entry.endswith("/bin")


class TestMergeBrowserPath:
    def test_empty_existing_returns_only_candidates(self):
        out = _merge_browser_path("")
        # No exception; output is a string with platform separator.
        assert isinstance(out, str)

    def test_existing_entries_preserved_at_tail(self):
        out = _merge_browser_path("/usr/bin:/usr/local/bin")
        # The two original entries appear, in order.
        parts = out.split(os.pathsep)
        assert "/usr/bin" in parts
        assert "/usr/local/bin" in parts
        idx_a = parts.index("/usr/bin")
        idx_b = parts.index("/usr/local/bin")
        assert idx_a < idx_b

    def test_does_not_duplicate_existing_entry(self):
        # If a candidate dir is already on PATH it should not be prepended.
        with patch(
            "tools.browser_tool._browser_candidate_path_dirs",
            return_value=["/usr/bin"],
        ):
            out = _merge_browser_path("/usr/bin")
            assert out.count("/usr/bin") == 1

    def test_only_prepends_existing_directories(self, tmp_path):
        # A candidate that doesn't exist on disk should be filtered out.
        with patch(
            "tools.browser_tool._browser_candidate_path_dirs",
            return_value=[str(tmp_path / "does-not-exist")],
        ):
            out = _merge_browser_path("/usr/bin")
            assert "does-not-exist" not in out

    def test_returns_string_in_path_separator_form(self):
        out = _merge_browser_path("/a:/b")
        # On Linux, separator is ":"; on Windows it's ";".
        # Just verify we get back a string.
        assert isinstance(out, str)
        assert out
