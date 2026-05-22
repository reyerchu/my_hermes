"""Coverage for pure helpers in tools.code_execution_tool:
_scrub_child_env, _get_execution_mode."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from tools.code_execution_tool import (
    _scrub_child_env,
    _get_execution_mode,
    EXECUTION_MODES,
    DEFAULT_EXECUTION_MODE,
    _SAFE_ENV_PREFIXES,
    _SECRET_SUBSTRINGS,
    _WINDOWS_ESSENTIAL_ENV_VARS,
)


class TestScrubChildEnv:
    def test_passthrough_always_allowed(self):
        out = _scrub_child_env(
            {"MY_API_KEY": "secret", "OTHER": "x"},
            is_passthrough=lambda k: k == "MY_API_KEY",
            is_windows=False,
        )
        # MY_API_KEY would normally be blocked (KEY substring) but
        # passthrough wins.
        assert out["MY_API_KEY"] == "secret"

    def test_secret_substring_blocked(self):
        out = _scrub_child_env(
            {"OPENAI_API_KEY": "x", "PATH": "/usr/bin"},
            is_passthrough=lambda k: False,
            is_windows=False,
        )
        assert "OPENAI_API_KEY" not in out
        assert out["PATH"] == "/usr/bin"

    def test_safe_prefix_allowed(self):
        # PATH is one of the safe prefixes.
        out = _scrub_child_env(
            {"PATH": "/x", "LANG": "en_US", "HOME": "/h"},
            is_passthrough=lambda k: False,
            is_windows=False,
        )
        assert out == {"PATH": "/x", "LANG": "en_US", "HOME": "/h"}

    def test_unsafe_unprefixed_blocked(self):
        out = _scrub_child_env(
            {"RANDOM_VAR": "x"},
            is_passthrough=lambda k: False,
            is_windows=False,
        )
        assert "RANDOM_VAR" not in out

    def test_windows_essential_passes(self):
        # Pick any var from the windows essentials set.
        essential = next(iter(_WINDOWS_ESSENTIAL_ENV_VARS))
        out = _scrub_child_env(
            {essential: "x"},
            is_passthrough=lambda k: False,
            is_windows=True,
        )
        assert out[essential] == "x"

    def test_windows_essential_not_allowed_on_posix(self):
        essential = next(iter(_WINDOWS_ESSENTIAL_ENV_VARS))
        # Must not be auto-passed when is_windows=False.
        out = _scrub_child_env(
            {essential: "x"},
            is_passthrough=lambda k: False,
            is_windows=False,
        )
        # Unless it happens to start with a safe prefix or to be passthrough.
        is_safe_prefix = any(essential.startswith(p) for p in _SAFE_ENV_PREFIXES)
        if is_safe_prefix:
            assert essential in out
        else:
            assert essential not in out

    def test_secret_case_insensitive(self):
        out = _scrub_child_env(
            {"my_api_key": "x"},  # lowercase
            is_passthrough=lambda k: False,
            is_windows=False,
        )
        assert "my_api_key" not in out


class TestExecutionMode:
    def test_default_when_no_config(self, monkeypatch):
        import sys, types
        # Make read_raw_config raise → falls back to {}.
        fake = types.ModuleType("hermes_cli.config")
        fake.read_raw_config = lambda: {}
        monkeypatch.setitem(sys.modules, "hermes_cli.config", fake)
        assert _get_execution_mode() == DEFAULT_EXECUTION_MODE

    def test_strict_from_config(self, monkeypatch):
        import sys, types
        fake = types.ModuleType("hermes_cli.config")
        fake.read_raw_config = lambda: {"code_execution": {"mode": "strict"}}
        monkeypatch.setitem(sys.modules, "hermes_cli.config", fake)
        assert _get_execution_mode() == "strict"

    def test_unknown_value_falls_back(self, monkeypatch):
        import sys, types
        fake = types.ModuleType("hermes_cli.config")
        fake.read_raw_config = lambda: {"code_execution": {"mode": "weird"}}
        monkeypatch.setitem(sys.modules, "hermes_cli.config", fake)
        assert _get_execution_mode() == DEFAULT_EXECUTION_MODE

    def test_case_insensitive_and_trimmed(self, monkeypatch):
        import sys, types
        fake = types.ModuleType("hermes_cli.config")
        fake.read_raw_config = lambda: {"code_execution": {"mode": " STRICT "}}
        monkeypatch.setitem(sys.modules, "hermes_cli.config", fake)
        assert _get_execution_mode() == "strict"

    def test_execution_modes_constant(self):
        assert "project" in EXECUTION_MODES
        assert "strict" in EXECUTION_MODES
        assert DEFAULT_EXECUTION_MODE in EXECUTION_MODES
