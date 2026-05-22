"""Coverage for ``hermes_cli.curses_ui.flush_stdin`` — the safe stdin
drain after curses.endwin()."""
from __future__ import annotations

import io
import sys

from hermes_cli.curses_ui import flush_stdin


class _FakeNonTty(io.StringIO):
    def isatty(self) -> bool:  # type: ignore[override]
        return False


class _FakeTtyMissingFd(io.StringIO):
    """A TTY-claiming stream whose underlying fd raises on flush."""

    def isatty(self) -> bool:  # type: ignore[override]
        return True


class TestFlushStdin:
    def test_no_op_on_non_tty_stdin(self, monkeypatch):
        monkeypatch.setattr(sys, "stdin", _FakeNonTty())
        # Should return without raising.
        assert flush_stdin() is None

    def test_no_op_on_tty_when_termios_not_importable(self, monkeypatch):
        # Patch sys.stdin to claim TTY, then break termios import to
        # exercise the except branch.
        monkeypatch.setattr(sys, "stdin", _FakeTtyMissingFd())
        original_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __import__

        def fake_import(name, *args, **kwargs):
            if name == "termios":
                raise ImportError("simulated")
            return original_import(name, *args, **kwargs)

        # The helper imports termios lazily inside its try/except, so even
        # forcing the import to fail must not propagate the error.
        monkeypatch.setattr("builtins.__import__", fake_import)
        assert flush_stdin() is None

    def test_safe_to_call_repeatedly(self, monkeypatch):
        monkeypatch.setattr(sys, "stdin", _FakeNonTty())
        for _ in range(5):
            flush_stdin()
