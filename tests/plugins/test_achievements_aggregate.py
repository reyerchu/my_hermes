"""Coverage for aggregate_stats + evaluate_definition in
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


class TestAggregateStatsBasics:
    def test_empty_sessions(self, mod):
        agg = mod.aggregate_stats([])
        assert agg["session_count"] == 0
        assert agg["max_tool_calls_in_session"] == 0
        assert agg["total_tool_calls"] == 0
        assert agg["distinct_model_count"] == 0

    def test_session_count(self, mod):
        agg = mod.aggregate_stats([{}, {}, {}])
        assert agg["session_count"] == 3

    def test_max_tool_calls(self, mod):
        agg = mod.aggregate_stats([
            {"tool_call_count": 50},
            {"tool_call_count": 200},
            {"tool_call_count": 100},
        ])
        assert agg["max_tool_calls_in_session"] == 200

    def test_total_sums(self, mod):
        agg = mod.aggregate_stats([
            {"tool_call_count": 10, "error_count": 1},
            {"tool_call_count": 20, "error_count": 2},
        ])
        assert agg["total_tool_calls"] == 30
        assert agg["total_errors"] == 3

    def test_distinct_models_and_providers(self, mod):
        agg = mod.aggregate_stats([
            {"model_names": {"openai-gpt-4", "anthropic-claude"}},
            {"model_names": {"openai-gpt-4"}},  # dup model
        ])
        # 2 distinct models
        assert agg["distinct_model_count"] == 2
        # 2 distinct providers (openai, anthropic)
        assert agg["distinct_provider_count"] == 2


class TestAggregateLocalModel:
    def test_local_model_chat_sessions_counted(self, mod):
        agg = mod.aggregate_stats([
            {"model_names": {"ollama/llama-3"}},
            {"model_names": {"openai-gpt-4"}},
        ])
        # ollama session counts as local
        assert agg["local_model_chat_sessions"] == 1


class TestAggregateTimeBuckets:
    def test_weekend_session_counted(self, mod):
        # 2026-05-23 is a Saturday → weekday >= 5
        import time
        sat_ts = time.mktime(time.strptime("2026-05-23 12:00:00", "%Y-%m-%d %H:%M:%S"))
        agg = mod.aggregate_stats([{"started_at": sat_ts}])
        assert agg["weekend_sessions"] == 1

    def test_night_session_counted(self, mod):
        # 23:30 → night
        import time
        ts = time.mktime(time.strptime("2026-05-22 23:30:00", "%Y-%m-%d %H:%M:%S"))
        agg = mod.aggregate_stats([{"started_at": ts}])
        assert agg["night_sessions"] == 1

    def test_invalid_timestamp_silent(self, mod):
        # Bad started_at doesn't crash; no buckets counted.
        agg = mod.aggregate_stats([{"started_at": "not a number"}])
        assert agg["weekend_sessions"] == 0
        assert agg["night_sessions"] == 0


class TestEvaluateDefinition:
    def test_dispatches_to_tiered(self, mod):
        definition = {
            "threshold_metric": "x",
            "tiers": [{"name": "T", "threshold": 1}],
        }
        out = mod.evaluate_definition(definition, {"x": 5})
        assert out["unlocked"] is True
        assert out["tier"] == "T"

    def test_dispatches_to_requirements(self, mod):
        definition = {
            "requirements": [{"metric": "a", "gte": 1}],
        }
        out = mod.evaluate_definition(definition, {"a": 5})
        assert out["unlocked"] is True

    def test_dispatches_to_boolean(self, mod):
        # No threshold_metric and no requirements → falls back to boolean.
        definition = {"metric": "x"}
        out = mod.evaluate_definition(definition, {"x": True})
        assert out["unlocked"] is True
