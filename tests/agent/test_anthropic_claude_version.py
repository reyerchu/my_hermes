"""Coverage for Claude Code version detection in agent.anthropic_adapter."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

import agent.anthropic_adapter as aa
from agent.anthropic_adapter import (
    _detect_claude_code_version,
    _get_claude_code_version,
    _CLAUDE_CODE_VERSION_FALLBACK,
)


@pytest.fixture(autouse=True)
def _reset_cache():
    aa._claude_code_version_cache = None
    yield
    aa._claude_code_version_cache = None


class TestDetectClaudeCodeVersion:
    def test_happy_path_claude(self, monkeypatch):
        result = MagicMock(returncode=0, stdout="2.1.74 (Claude Code)\n")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        assert _detect_claude_code_version() == "2.1.74"

    def test_happy_path_bare_version(self, monkeypatch):
        result = MagicMock(returncode=0, stdout="3.0.0")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        assert _detect_claude_code_version() == "3.0.0"

    def test_non_zero_returncode_fallback(self, monkeypatch):
        result = MagicMock(returncode=1, stdout="error")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        assert _detect_claude_code_version() == _CLAUDE_CODE_VERSION_FALLBACK

    def test_subprocess_raises_fallback(self, monkeypatch):
        def _raise(*a, **kw):
            raise FileNotFoundError("no binary")
        monkeypatch.setattr(subprocess, "run", _raise)
        assert _detect_claude_code_version() == _CLAUDE_CODE_VERSION_FALLBACK

    def test_timeout_fallback(self, monkeypatch):
        def _raise(*a, **kw):
            raise subprocess.TimeoutExpired(cmd="x", timeout=5)
        monkeypatch.setattr(subprocess, "run", _raise)
        assert _detect_claude_code_version() == _CLAUDE_CODE_VERSION_FALLBACK

    def test_empty_stdout_fallback(self, monkeypatch):
        result = MagicMock(returncode=0, stdout="   \n")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        assert _detect_claude_code_version() == _CLAUDE_CODE_VERSION_FALLBACK

    def test_non_digit_start_fallback(self, monkeypatch):
        # Result that doesn't start with a digit → fallback.
        result = MagicMock(returncode=0, stdout="anthropic/2.1.74")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        assert _detect_claude_code_version() == _CLAUDE_CODE_VERSION_FALLBACK


class TestGetClaudeCodeVersion:
    def test_uses_cache_after_first_call(self, monkeypatch):
        calls = []
        def _run(*a, **kw):
            calls.append(1)
            return MagicMock(returncode=0, stdout="5.0.0")
        monkeypatch.setattr(subprocess, "run", _run)
        v1 = _get_claude_code_version()
        v2 = _get_claude_code_version()
        assert v1 == v2 == "5.0.0"
        # Detector only invoked once thanks to caching.
        assert len(calls) == 1

    def test_returns_fallback_when_unavailable(self, monkeypatch):
        def _raise(*a, **kw):
            raise FileNotFoundError
        monkeypatch.setattr(subprocess, "run", _raise)
        assert _get_claude_code_version() == _CLAUDE_CODE_VERSION_FALLBACK
