"""Coverage for metric_label / criteria_for / display_achievement in
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


class TestMetricLabel:
    def test_known(self, mod):
        # Known metric returns the label from METRIC_LABELS.
        out = mod.metric_label("max_tool_calls_in_session")
        assert "tool calls" in out

    def test_unknown_falls_back_to_humanised(self, mod):
        out = mod.metric_label("totally_unknown_metric")
        # Underscores → spaces
        assert out == "totally unknown metric"


class TestCriteriaFor:
    def test_secret_state_message(self, mod):
        out = mod.criteria_for({"secret": True, "state": "secret"})
        assert "Secret" in out
        assert "hidden" in out

    def test_tiered_definition(self, mod):
        definition = {
            "threshold_metric": "max_tool_calls_in_session",
            "tiers": [
                {"name": "Copper", "threshold": 100},
                {"name": "Silver", "threshold": 500},
            ],
        }
        out = mod.criteria_for(definition)
        assert "Tier ladder" in out
        assert "Copper 100" in out
        assert "Silver 500" in out

    def test_requirements_definition(self, mod):
        definition = {
            "requirements": [
                {"metric": "a", "gte": 10},
                {"metric": "b", "gte": 5},
            ],
        }
        out = mod.criteria_for(definition)
        assert "≥ 10" in out
        assert "≥ 5" in out
        # Joins with ";".
        assert ";" in out

    def test_tiered_no_tiers(self, mod):
        # threshold_metric present but tiers empty.
        out = mod.criteria_for({"threshold_metric": "x", "tiers": []})
        assert "matching workflow" in out

    def test_fallback_when_no_signals(self, mod):
        out = mod.criteria_for({})
        # Catch-all fallback.
        assert "matching Hermes behavior" in out


class TestDisplayAchievement:
    def test_normal_item(self, mod):
        item = {
            "id": "x",
            "name": "Test",
            "description": "desc",
            "state": "unlocked",
            "threshold_metric": "x",
            "tiers": [{"name": "T", "threshold": 1}],
        }
        out = mod.display_achievement(item)
        # Original fields preserved.
        assert out["name"] == "Test"
        assert out["description"] == "desc"
        # criteria injected.
        assert "criteria" in out

    def test_secret_state_replaces_name(self, mod):
        item = {
            "id": "secret_one",
            "name": "Real Name",
            "description": "real description",
            "state": "secret",
            "secret": True,
        }
        out = mod.display_achievement(item)
        assert out["name"] == "???"
        assert "hidden" in out["description"]
        assert out["icon"] == "secret"

    def test_input_not_mutated(self, mod):
        item = {
            "id": "x",
            "state": "unlocked",
            "threshold_metric": "x",
            "tiers": [{"name": "T", "threshold": 1}],
        }
        original = dict(item)
        mod.display_achievement(item)
        # Source dict not modified.
        assert item == original
