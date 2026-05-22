"""Coverage for hermes_cli.callbacks.approval_callback — selection
UI state setup and timeout behaviour."""
from __future__ import annotations

import queue
import sys
import time
import types
from unittest.mock import MagicMock, patch

import pytest

from hermes_cli import callbacks


@pytest.fixture(autouse=True)
def _stub_cli_config(monkeypatch):
    # Stub cli.CLI_CONFIG to avoid importing the heavy CLI module.
    fake_cli = types.ModuleType("cli")
    fake_cli.CLI_CONFIG = {"approvals": {"timeout": 60}}
    monkeypatch.setitem(sys.modules, "cli", fake_cli)


def _make_cli():
    cli = MagicMock(spec=[])
    return cli


class TestApprovalCallback:
    def test_returns_value_from_response_queue(self):
        cli = _make_cli()
        # Pre-populate response_queue once approval_callback installs it.
        # We'll inspect the cli._approval_state after it's set in a thread.
        import threading

        result_box = {}

        def caller():
            # Block until the callback has installed _approval_state.
            for _ in range(50):
                if getattr(cli, "_approval_state", None):
                    cli._approval_state["response_queue"].put("once")
                    return
                time.sleep(0.01)

        t = threading.Thread(target=caller)
        t.start()
        result = callbacks.approval_callback(cli, "ls", "list files")
        t.join()
        assert result == "once"
        # State cleared after return.
        assert cli._approval_state is None

    def test_state_includes_choices_short_command(self):
        cli = _make_cli()
        import threading

        def caller():
            for _ in range(50):
                if getattr(cli, "_approval_state", None):
                    # Capture the state, then unblock.
                    captured["state"] = dict(cli._approval_state)
                    cli._approval_state["response_queue"].put("deny")
                    return
                time.sleep(0.01)

        captured = {}
        t = threading.Thread(target=caller)
        t.start()
        callbacks.approval_callback(cli, "ls", "list files")
        t.join()
        assert "view" not in captured["state"]["choices"]
        assert "once" in captured["state"]["choices"]
        assert "session" in captured["state"]["choices"]
        assert "always" in captured["state"]["choices"]
        assert "deny" in captured["state"]["choices"]

    def test_view_choice_added_for_long_command(self):
        cli = _make_cli()
        import threading

        captured = {}

        def caller():
            for _ in range(50):
                if getattr(cli, "_approval_state", None):
                    captured["state"] = dict(cli._approval_state)
                    cli._approval_state["response_queue"].put("deny")
                    return
                time.sleep(0.01)

        long_cmd = "echo " + "x" * 100
        t = threading.Thread(target=caller)
        t.start()
        callbacks.approval_callback(cli, long_cmd, "desc")
        t.join()
        assert "view" in captured["state"]["choices"]

    def test_lock_initialized_on_first_call(self):
        cli = MagicMock(spec=[])
        # Pre-populate that no lock exists, just so we can verify it gets set.
        import threading
        import queue as _queue

        def caller():
            for _ in range(50):
                if getattr(cli, "_approval_state", None):
                    cli._approval_state["response_queue"].put("session")
                    return
                time.sleep(0.01)

        t = threading.Thread(target=caller)
        t.start()
        callbacks.approval_callback(cli, "cmd", "desc")
        t.join()
        assert isinstance(cli._approval_lock, type(threading.Lock()))

    def test_timeout_returns_deny(self, monkeypatch):
        # Patch monotonic so timeout fires immediately.
        cli = _make_cli()
        # Patch CLI_CONFIG to 0 second timeout.
        sys.modules["cli"].CLI_CONFIG = {"approvals": {"timeout": 0}}
        # No one puts to the response_queue → after deadline expires return "deny".
        result = callbacks.approval_callback(cli, "ls", "x")
        assert result == "deny"
        assert cli._approval_state is None
