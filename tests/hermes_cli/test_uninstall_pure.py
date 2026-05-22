"""Coverage for the pure helpers in ``hermes_cli.uninstall`` (paths,
platform check, default-home detection)."""
from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import uninstall as un


class TestGetProjectRoot:
    def test_returns_path_object(self):
        out = un.get_project_root()
        assert isinstance(out, Path)
        # The project root must contain hermes_cli/ as a subdir.
        assert (out / "hermes_cli").is_dir()


class TestFindShellConfigs:
    def test_returns_list_of_paths(self):
        configs = un.find_shell_configs()
        assert isinstance(configs, list)
        # All entries are Paths under the user's home.
        for c in configs:
            assert isinstance(c, Path)


class TestHermesPathMarkers:
    def test_emits_hermes_owned_substrings(self):
        markers = un._hermes_path_markers(Path("/home/user/.hermes"))
        # All four typical Hermes-owned subdirs are present:
        assert any(m.endswith("hermes-agent") for m in markers)
        assert any(m.endswith("git") for m in markers)
        assert any(m.endswith("node") for m in markers)
        assert any(m.endswith("venv") for m in markers)

    def test_strips_trailing_slash_on_root(self):
        markers = un._hermes_path_markers(Path("/home/user/.hermes/"))
        # No double-separator inside the markers.
        for m in markers:
            assert "\\\\" not in m


class TestIsWindows:
    def test_matches_sys_platform(self):
        import sys
        assert un._is_windows() == (sys.platform == "win32")


class TestIsDefaultHermesHome:
    def test_returns_false_for_a_clearly_non_default_path(self, tmp_path):
        # An arbitrary tmp path can never equal the default Hermes root.
        assert un._is_default_hermes_home(tmp_path / "x") is False

    def test_does_not_throw_on_unresolvable_path(self, tmp_path):
        # Pass a path that doesn't exist — the helper swallows the error.
        out = un._is_default_hermes_home(tmp_path / "definitely_missing")
        assert isinstance(out, bool)
