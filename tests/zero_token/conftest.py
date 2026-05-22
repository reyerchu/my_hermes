"""Test fixtures for the zero-token claude_code_proxy script.

The proxy module lives in ``zero-token/claude_code_proxy.py`` — a directory
name that can't be imported normally because of the hyphen.  And the module
performs filesystem side effects at import time (creating ~/.hermes/zero-token
and writing empty-mcp.json), so each test wants a fresh import against an
isolated HOME.

This conftest provides a ``proxy`` fixture that:
  * points HOME at a tmp_path
  * sets the CLAUDE_PROXY_* env knobs we care about
  * loads the module fresh via importlib.util
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

# Resolve once at import time so we don't depend on the test cwd.
_PROXY_PATH = (
    Path(__file__).resolve().parents[2] / "zero-token" / "claude_code_proxy.py"
)


def _load_proxy(home: Path) -> ModuleType:
    """Load a fresh copy of claude_code_proxy with HOME pinned to *home*."""
    spec = importlib.util.spec_from_file_location(
        "claude_code_proxy_under_test", _PROXY_PATH
    )
    assert spec and spec.loader, f"could not load proxy module from {_PROXY_PATH}"
    module = importlib.util.module_from_spec(spec)
    # Important: assign the *fresh* module to sys.modules before exec so that
    # later imports inside the module resolve to this instance (e.g. for the
    # signal handler registration block that runs at import time).
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def proxy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Fresh proxy module isolated to a tmp HOME."""
    monkeypatch.setenv("HOME", str(tmp_path))
    # Pin a stable port so accidental web.run_app calls would fail loudly.
    monkeypatch.setenv("CLAUDE_PROXY_PORT", "0")
    # Make sure no inherited env biases the timeout/age tests.
    monkeypatch.delenv("CLAUDE_PROXY_TIMEOUT", raising=False)
    monkeypatch.delenv("CLAUDE_PROXY_SESSION_MAX_AGE", raising=False)
    monkeypatch.delenv("CLAUDE_PROXY_SESSION_UUID", raising=False)
    return _load_proxy(tmp_path)
