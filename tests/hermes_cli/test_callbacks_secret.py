"""Coverage for hermes_cli.callbacks.prompt_for_secret in the
non-TUI (no _app) code path — the path executed in headless tests."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hermes_cli import callbacks


class _FakeCli:
    """Minimal cli stand-in: no _app attribute so the headless branch is used."""

    def __init__(self):
        self._secret_state = None
        self._secret_deadline = 0


class TestPromptForSecretHeadless:
    def test_skipped_on_empty_input(self, monkeypatch):
        # getpass.getpass returns empty → "skipped" branch.
        monkeypatch.setattr(callbacks.getpass, "getpass", lambda *a, **kw: "")
        out = callbacks.prompt_for_secret(_FakeCli(), "MY_KEY", "Enter:")
        assert out["success"] is True
        assert out["skipped"] is True
        assert out["reason"] == "cancelled"
        assert out["stored_as"] == "MY_KEY"
        assert out["validated"] is False

    def test_skipped_on_eof(self, monkeypatch):
        def _raise(*a, **kw):
            raise EOFError
        monkeypatch.setattr(callbacks.getpass, "getpass", _raise)
        out = callbacks.prompt_for_secret(_FakeCli(), "X", "p")
        assert out["skipped"] is True

    def test_skipped_on_keyboard_interrupt(self, monkeypatch):
        def _raise(*a, **kw):
            raise KeyboardInterrupt
        monkeypatch.setattr(callbacks.getpass, "getpass", _raise)
        out = callbacks.prompt_for_secret(_FakeCli(), "X", "p")
        assert out["skipped"] is True

    def test_value_saved(self, monkeypatch):
        monkeypatch.setattr(callbacks.getpass, "getpass", lambda *a, **kw: "secret-value")
        stub_save = MagicMock(return_value={
            "success": True,
            "stored_as": "MY_KEY",
            "validated": True,
        })
        monkeypatch.setattr(callbacks, "save_env_value_secure", stub_save)
        out = callbacks.prompt_for_secret(_FakeCli(), "MY_KEY", "p")
        stub_save.assert_called_once_with("MY_KEY", "secret-value")
        assert out["success"] is True
        assert out["skipped"] is False
        assert "stored securely" in out["message"]

    def test_initializes_state_attrs(self, monkeypatch):
        monkeypatch.setattr(callbacks.getpass, "getpass", lambda *a, **kw: "")
        # Use bare object — should add _secret_state / _secret_deadline.
        cli = MagicMock(spec=[])  # No attributes at all.
        # spec=[] means no _app — exercises the headless path.
        callbacks.prompt_for_secret(cli, "K", "p")
        assert cli._secret_state is None
        assert cli._secret_deadline == 0
