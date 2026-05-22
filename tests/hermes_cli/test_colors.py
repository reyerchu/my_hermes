"""Coverage for hermes_cli/colors.py — the ANSI color helpers."""
from __future__ import annotations

import io
import sys
from contextlib import contextmanager

import pytest

from hermes_cli.colors import Colors, color, should_use_color


@contextmanager
def _patched_stdout(stdout: io.TextIOBase):
    original = sys.stdout
    sys.stdout = stdout
    try:
        yield
    finally:
        sys.stdout = original


class _FakeTty(io.StringIO):
    """A StringIO that lies about being a TTY so should_use_color() = True."""

    def isatty(self) -> bool:  # type: ignore[override]
        return True


class _FakeNonTty(io.StringIO):
    def isatty(self) -> bool:  # type: ignore[override]
        return False


class TestShouldUseColor:
    def test_no_color_env_disables(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        with _patched_stdout(_FakeTty()):
            assert should_use_color() is False

    def test_no_color_set_empty_still_disables(self, monkeypatch):
        # Per https://no-color.org the variable being set (any value) disables.
        monkeypatch.setenv("NO_COLOR", "")
        with _patched_stdout(_FakeTty()):
            assert should_use_color() is False

    def test_term_dumb_disables(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "dumb")
        with _patched_stdout(_FakeTty()):
            assert should_use_color() is False

    def test_non_tty_disables(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")
        with _patched_stdout(_FakeNonTty()):
            assert should_use_color() is False

    def test_tty_enables(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")
        with _patched_stdout(_FakeTty()):
            assert should_use_color() is True


class TestColor:
    def test_returns_text_unchanged_when_color_disabled(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        with _patched_stdout(_FakeTty()):
            assert color("hello", Colors.RED) == "hello"

    def test_wraps_text_with_codes_and_reset_when_enabled(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")
        with _patched_stdout(_FakeTty()):
            out = color("ok", Colors.GREEN)
        assert out == f"{Colors.GREEN}ok{Colors.RESET}"

    def test_multiple_codes_concatenated_in_order(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")
        with _patched_stdout(_FakeTty()):
            out = color("bold-red", Colors.BOLD, Colors.RED)
        assert out == f"{Colors.BOLD}{Colors.RED}bold-red{Colors.RESET}"


class TestColorsTable:
    @pytest.mark.parametrize(
        "attr",
        ["RESET", "BOLD", "DIM", "RED", "GREEN", "YELLOW", "BLUE", "MAGENTA", "CYAN"],
    )
    def test_attribute_is_ansi_escape(self, attr):
        value = getattr(Colors, attr)
        assert isinstance(value, str)
        assert value.startswith("\033[")
        assert value.endswith("m")
