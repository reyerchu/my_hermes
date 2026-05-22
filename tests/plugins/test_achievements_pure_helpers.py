"""Gap coverage for the pure helpers in hermes-achievements/dashboard/plugin_api.

The existing tests target integration concerns (the 200-session cap removal
and background-scan behavior).  This file focuses on the small pure helpers
that compute display state — easy to test in isolation and the most
likely to regress on a copy-paste edit.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

PLUGIN_MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "plugins"
    / "hermes-achievements"
    / "dashboard"
    / "plugin_api.py"
)


@pytest.fixture(scope="module")
def m():
    spec = importlib.util.spec_from_file_location(
        "achievements_plugin_pure_test", PLUGIN_MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


class TestSimpleHelpers:
    def test_tiers_zips_names_and_thresholds(self, m):
        result = m.tiers([10, 20, 30, 40, 50])
        assert result == [
            {"name": "Copper", "threshold": 10},
            {"name": "Silver", "threshold": 20},
            {"name": "Gold", "threshold": 30},
            {"name": "Diamond", "threshold": 40},
            {"name": "Olympian", "threshold": 50},
        ]

    def test_tiers_short_list_truncates_to_names_available(self, m):
        # zip() truncates to the shorter input, so the helper is forgiving.
        result = m.tiers([1, 2])
        assert len(result) == 2
        assert result[0]["name"] == "Copper"
        assert result[1]["threshold"] == 2

    def test_req_builds_metric_record(self, m):
        assert m.req("foo", 5) == {"metric": "foo", "gte": 5}


class TestToolNameExtraction:
    def test_top_level_name_wins(self, m):
        assert m._tool_name_from_call({"name": "Bash"}) == "Bash"

    def test_falls_back_to_function_name(self, m):
        assert (
            m._tool_name_from_call({"function": {"name": "Read"}}) == "Read"
        )

    def test_top_level_name_preferred_over_function(self, m):
        call = {"name": "Edit", "function": {"name": "Ignored"}}
        assert m._tool_name_from_call(call) == "Edit"

    def test_none_for_non_dict(self, m):
        assert m._tool_name_from_call(None) is None
        assert m._tool_name_from_call("Bash") is None
        assert m._tool_name_from_call(["Bash"]) is None

    def test_none_when_no_name_anywhere(self, m):
        assert m._tool_name_from_call({"function": {}}) is None
        assert m._tool_name_from_call({}) is None


class TestCountTool:
    def test_case_insensitive_substring(self, m):
        assert m._count_tool(["Bash", "Read", "Edit", "Write", "Grep"], "read", "write") == 2

    def test_returns_zero_when_no_match(self, m):
        assert m._count_tool(["Bash", "Edit"], "notatool") == 0

    def test_empty_list_returns_zero(self, m):
        assert m._count_tool([], "anything") == 0

    def test_multiple_needles_or_match(self, m):
        # Any needle matching counts the tool, but it's only counted once.
        assert m._count_tool(["Read"], "rea", "read") == 1


class TestModelProvider:
    def test_provider_slash_form(self, m):
        assert m.model_provider("openai/gpt-4o") == "openai"
        assert m.model_provider("anthropic/claude-sonnet-4-6") == "anthropic"

    def test_bare_known_provider_keyword(self, m):
        # "anthropic" appears as a substring → returns "anthropic"
        assert m.model_provider("anthropic-claude-sonnet") == "anthropic"
        # "gemini" maps explicitly to "google"
        assert m.model_provider("gemini-2.0-flash") == "google"

    def test_none_for_empty_or_literal_none(self, m):
        assert m.model_provider("") is None
        assert m.model_provider("   ") is None
        assert m.model_provider("none") is None
        assert m.model_provider("NONE") is None

    def test_unknown_falls_back_to_first_dash_segment(self, m):
        # Final fallback: split on ':' then '-' to return first segment.
        assert m.model_provider("some-totally-unknown-model") == "some"
        assert m.model_provider("custom:weird:thing") == "custom"


class TestIsLocalModelName:
    def test_true_for_obvious_local_markers(self, m):
        assert m.is_local_model_name("ollama/llama3")
        assert m.is_local_model_name("local/foo")
        assert m.is_local_model_name("model.gguf")
        assert m.is_local_model_name("http://localhost:8000/v1")
        assert m.is_local_model_name("http://127.0.0.1:1234")

    def test_false_for_cloud_providers(self, m):
        assert not m.is_local_model_name("anthropic/claude-sonnet-4-6")
        assert not m.is_local_model_name("openai/gpt-4o")

    def test_false_for_empty_or_none(self, m):
        assert not m.is_local_model_name("")
        assert not m.is_local_model_name("none")
        assert not m.is_local_model_name(None)  # type: ignore[arg-type]


class TestSnapshotStale:
    def test_none_or_non_dict_is_stale(self, m):
        assert m._is_snapshot_stale(None) is True
        assert m._is_snapshot_stale("nope") is True  # type: ignore[arg-type]

    def test_missing_generated_at_is_stale(self, m):
        assert m._is_snapshot_stale({}) is True

    def test_zero_generated_at_is_stale(self, m):
        assert m._is_snapshot_stale({"generated_at": 0}) is True

    def test_fresh_snapshot_within_ttl_is_not_stale(self, m):
        # ttl=120s; build a snapshot generated 30s ago.
        assert m._is_snapshot_stale(
            {"generated_at": 1_000_000}, now=1_000_030
        ) is False

    def test_old_snapshot_beyond_ttl_is_stale(self, m):
        # 200s > 120s ttl
        assert m._is_snapshot_stale(
            {"generated_at": 1_000_000}, now=1_000_200
        ) is True


class TestEvaluateTiered:
    def _def(self):
        return {
            "threshold_metric": "x",
            "tiers": [
                {"name": "A", "threshold": 10},
                {"name": "B", "threshold": 50},
                {"name": "C", "threshold": 100},
            ],
        }

    def test_no_progress_returns_no_tier(self, m):
        result = m.evaluate_tiered(self._def(), {"x": 0})
        assert result["tier"] is None
        assert result["progress"] == 0

    def test_first_tier_unlocked(self, m):
        result = m.evaluate_tiered(self._def(), {"x": 25})
        assert result["tier"] == "A"

    def test_top_tier_unlocked(self, m):
        result = m.evaluate_tiered(self._def(), {"x": 200})
        assert result["tier"] == "C"

    def test_unsorted_tiers_still_resolve_correctly(self, m):
        unsorted = {
            "threshold_metric": "x",
            "tiers": [
                {"name": "C", "threshold": 100},
                {"name": "A", "threshold": 10},
                {"name": "B", "threshold": 50},
            ],
        }
        result = m.evaluate_tiered(unsorted, {"x": 75})
        assert result["tier"] == "B"

    def test_missing_metric_treated_as_zero(self, m):
        result = m.evaluate_tiered(self._def(), {})
        assert result["progress"] == 0
        assert result["tier"] is None


class TestEvaluateBoolean:
    def test_unlocked_when_metric_truthy(self, m):
        result = m.evaluate_boolean({"metric": "flag"}, {"flag": True})
        assert result["unlocked"] is True
        assert result["progress_pct"] == 100

    def test_locked_when_metric_falsy(self, m):
        result = m.evaluate_boolean({"metric": "flag"}, {"flag": 0})
        assert result["unlocked"] is False
        assert result["progress_pct"] == 0


class TestMetricLabel:
    def test_known_label_uses_table(self, m):
        # METRIC_LABELS is a module-level dict; any entry should round-trip
        # through metric_label.  Use one we know is defined.
        assert isinstance(m.METRIC_LABELS, dict)
        # Pick an arbitrary key from the table for the round-trip test
        if m.METRIC_LABELS:
            key, expected = next(iter(m.METRIC_LABELS.items()))
            assert m.metric_label(key) == expected

    def test_unknown_falls_back_to_humanised_metric(self, m):
        assert m.metric_label("some_unknown_metric_name") == "some unknown metric name"

    def test_no_underscore_metric_returns_self(self, m):
        # If the metric has no underscores, the humanised fallback is identity.
        assert m.metric_label("plain") == "plain"
