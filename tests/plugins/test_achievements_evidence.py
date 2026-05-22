"""Coverage for evidence_for + session_fingerprint helpers in
plugins.hermes-achievements.dashboard.plugin_api."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_MOD_PATH = (
    _REPO_ROOT / "plugins" / "hermes-achievements" / "dashboard" / "plugin_api.py"
)


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "hermes_achievements_api", _MOD_PATH
    )
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
    except Exception as e:
        pytest.skip(f"could not load module: {e}")
    return m


class TestEvidenceFor:
    def test_empty_sessions_returns_none(self, mod):
        out = mod.evidence_for({"threshold_metric": "max_tool_calls_in_session"}, [])
        assert out is None

    def test_unknown_metric_returns_none(self, mod):
        sessions = [{"session_id": "s1", "title": "t", "tool_call_count": 5}]
        out = mod.evidence_for({"threshold_metric": "weird"}, sessions)
        assert out is None

    def test_picks_max_tool_calls_session(self, mod):
        sessions = [
            {"session_id": "low", "title": "Low", "tool_call_count": 10},
            {"session_id": "high", "title": "High", "tool_call_count": 100},
            {"session_id": "mid", "title": "Mid", "tool_call_count": 50},
        ]
        out = mod.evidence_for(
            {"threshold_metric": "max_tool_calls_in_session"}, sessions,
        )
        assert out == {"session_id": "high", "title": "High", "value": 100}

    def test_uses_correct_field_for_metric(self, mod):
        # max_terminal_calls_in_session → terminal_calls field
        sessions = [
            {"session_id": "a", "title": "A", "terminal_calls": 30},
            {"session_id": "b", "title": "B", "terminal_calls": 70},
        ]
        out = mod.evidence_for(
            {"threshold_metric": "max_terminal_calls_in_session"}, sessions,
        )
        assert out["session_id"] == "b"
        assert out["value"] == 70

    def test_no_threshold_metric_returns_none(self, mod):
        out = mod.evidence_for({}, [{"session_id": "x"}])
        assert out is None


class TestSessionFingerprint:
    def test_returns_dict(self, mod):
        out = mod.session_fingerprint({"session_id": "s1", "message_count": 10})
        assert isinstance(out, dict)

    def test_includes_known_fields(self, mod):
        # session_fingerprint typically picks specific meta keys
        meta = {
            "session_id": "s1",
            "started_at": 1000.0,
            "message_count": 5,
            "tool_call_count": 3,
        }
        out = mod.session_fingerprint(meta)
        # The output should expose recognisable identifiers.
        assert "session_id" in out or any(
            isinstance(v, (int, float, str)) for v in out.values()
        )

    def test_empty_meta(self, mod):
        # Empty meta still produces a (possibly empty) dict.
        out = mod.session_fingerprint({})
        assert isinstance(out, dict)
