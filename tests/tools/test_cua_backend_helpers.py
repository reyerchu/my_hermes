"""Coverage for pure helpers in tools.computer_use.cua_backend:
platform checks, regex parsers, key-combo split."""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from tools.computer_use.cua_backend import (
    _is_macos,
    _is_arm_mac,
    cua_driver_binary_available,
    cua_driver_install_hint,
    _parse_windows_from_text,
    _parse_elements_from_tree,
    _split_tree_text,
    _parse_key_combo,
)


class TestPlatformChecks:
    def test_is_macos_true_when_darwin(self):
        with patch.object(sys, "platform", "darwin"):
            assert _is_macos() is True

    def test_is_macos_false_when_linux(self):
        with patch.object(sys, "platform", "linux"):
            assert _is_macos() is False

    def test_is_arm_mac_requires_darwin_and_arm64(self):
        with patch.object(sys, "platform", "darwin"):
            with patch("tools.computer_use.cua_backend.platform.machine", return_value="arm64"):
                assert _is_arm_mac() is True
            with patch("tools.computer_use.cua_backend.platform.machine", return_value="x86_64"):
                assert _is_arm_mac() is False

    def test_is_arm_mac_false_on_linux(self):
        with patch.object(sys, "platform", "linux"):
            with patch("tools.computer_use.cua_backend.platform.machine", return_value="arm64"):
                assert _is_arm_mac() is False


class TestDriverBinary:
    def test_present_when_shutil_which_returns_path(self):
        with patch("tools.computer_use.cua_backend.shutil.which", return_value="/usr/local/bin/cua-driver"):
            assert cua_driver_binary_available() is True

    def test_missing_when_shutil_which_returns_none(self):
        with patch("tools.computer_use.cua_backend.shutil.which", return_value=None):
            assert cua_driver_binary_available() is False


class TestInstallHint:
    def test_hint_contains_install_commands(self):
        out = cua_driver_install_hint()
        assert "hermes computer-use install" in out
        assert "cua-driver" in out


class TestParseWindowsFromText:
    def test_basic_window(self):
        text = "- Safari (pid 12345) /Foo/Bar [window_id: 99]"
        out = _parse_windows_from_text(text)
        assert len(out) == 1
        w = out[0]
        assert w["app_name"] == "Safari"
        assert w["pid"] == 12345
        assert w["window_id"] == 99
        assert w["off_screen"] is False

    def test_off_screen_marker(self):
        text = "- Finder (pid 99) [off-screen] [window_id: 1]"
        out = _parse_windows_from_text(text)
        assert out[0]["off_screen"] is True

    def test_multiple_windows(self):
        text = (
            "- A (pid 1) [window_id: 1]\n"
            "- B (pid 2) [window_id: 2]\n"
        )
        out = _parse_windows_from_text(text)
        assert [w["app_name"] for w in out] == ["A", "B"]

    def test_no_match_returns_empty(self):
        assert _parse_windows_from_text("nothing here") == []


class TestParseElementsFromTree:
    def test_basic_element(self):
        md = '  - [0] AXButton "Submit"'
        out = _parse_elements_from_tree(md)
        assert len(out) == 1
        assert out[0].index == 0
        assert out[0].role == "AXButton"
        assert out[0].label == "Submit"

    def test_no_label(self):
        md = '  - [1] AXWindow'
        out = _parse_elements_from_tree(md)
        assert out[0].index == 1
        assert out[0].role == "AXWindow"
        assert out[0].label == ""

    def test_multiple_elements(self):
        md = (
            '  - [0] AXButton "A"\n'
            '    - [1] AXTextField "name"\n'
        )
        out = _parse_elements_from_tree(md)
        indices = [e.index for e in out]
        assert indices == [0, 1]

    def test_no_match_returns_empty(self):
        assert _parse_elements_from_tree("no elements") == []


class TestSplitTreeText:
    def test_summary_and_tree(self):
        full = "Window: Safari\n- [0] AXWindow\n  - [1] AXButton"
        summary, tree = _split_tree_text(full)
        assert summary == "Window: Safari"
        assert tree.startswith("- [0]")

    def test_single_line_no_tree(self):
        summary, tree = _split_tree_text("only summary")
        assert summary == "only summary"
        assert tree == ""

    def test_empty(self):
        summary, tree = _split_tree_text("")
        assert summary == ""
        assert tree == ""


class TestParseKeyCombo:
    def test_simple_key(self):
        key, mods = _parse_key_combo("a")
        assert key == "a"
        assert mods == []

    def test_cmd_s(self):
        key, mods = _parse_key_combo("cmd+s")
        assert key == "s"
        assert mods == ["cmd"]

    def test_aliases_normalized(self):
        # "command" → "cmd", "alt" → "option", "control" → "ctrl"
        key, mods = _parse_key_combo("command+option+control+x")
        assert key == "x"
        assert "cmd" in mods
        assert "option" in mods
        assert "ctrl" in mods

    def test_dash_separator(self):
        key, mods = _parse_key_combo("ctrl-c")
        assert key == "c"
        assert mods == ["ctrl"]

    def test_case_insensitive(self):
        key, mods = _parse_key_combo("CMD+SHIFT+a")
        assert key == "a"
        assert "cmd" in mods
        assert "shift" in mods

    def test_empty_returns_none(self):
        key, mods = _parse_key_combo("")
        assert key is None
        assert mods == []

    def test_only_modifiers(self):
        key, mods = _parse_key_combo("cmd+shift")
        assert key is None
        assert sorted(mods) == ["cmd", "shift"]

    def test_last_non_modifier_wins(self):
        # Two non-modifier keys — last one wins.
        key, mods = _parse_key_combo("a+b")
        assert key == "b"
