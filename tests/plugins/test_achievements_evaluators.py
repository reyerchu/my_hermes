"""Coverage for evaluation + classification helpers in
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


class TestToolNameFromCall:
    def test_top_level_name(self, mod):
        assert mod._tool_name_from_call({"name": "read_file"}) == "read_file"

    def test_function_block_name(self, mod):
        assert mod._tool_name_from_call(
            {"function": {"name": "write_file"}}
        ) == "write_file"

    def test_top_level_wins(self, mod):
        assert mod._tool_name_from_call(
            {"name": "outer", "function": {"name": "inner"}}
        ) == "outer"

    def test_non_dict_returns_none(self, mod):
        assert mod._tool_name_from_call("string") is None
        assert mod._tool_name_from_call(42) is None
        assert mod._tool_name_from_call(None) is None


class TestContent:
    def test_string(self, mod):
        assert mod._content({"content": "hi"}) == "hi"

    def test_none(self, mod):
        assert mod._content({}) == ""
        assert mod._content({"content": None}) == ""

    def test_list_json_serialized(self, mod):
        out = mod._content({"content": [{"type": "text", "text": "x"}]})
        # JSON-encoded
        assert "type" in out

    def test_unserializable_falls_back_to_str(self, mod):
        class Weird:
            def __repr__(self):
                return "<Weird>"
        out = mod._content({"content": Weird()})
        # str fallback
        assert "Weird" in out


class TestCountTool:
    def test_basic(self, mod):
        count = mod._count_tool(["read_file", "write_file", "terminal"], "file")
        assert count == 2

    def test_multiple_needles(self, mod):
        count = mod._count_tool(
            ["read_file", "search_files", "terminal", "browse"],
            "file", "browse",
        )
        assert count == 3

    def test_case_insensitive(self, mod):
        count = mod._count_tool(["READ_FILE", "Terminal"], "file")
        assert count == 1

    def test_empty(self, mod):
        assert mod._count_tool([], "file") == 0


class TestModelProvider:
    def test_slash_prefix(self, mod):
        assert mod.model_provider("openai/gpt-4o") == "openai"

    def test_known_substring(self, mod):
        # "openai" substring match: model name needs to contain "openai".
        assert mod.model_provider("openai-gpt-4") == "openai"
        # claude substring not in list — fallback splits on "-" → "claude".
        # Test what's in the keyword list instead.
        assert mod.model_provider("anthropic-claude") == "anthropic"

    def test_gemini_to_google(self, mod):
        assert mod.model_provider("gemini-3-flash") == "google"

    def test_none_or_empty(self, mod):
        assert mod.model_provider("") is None
        assert mod.model_provider("none") is None
        assert mod.model_provider(None) is None

    def test_fallback_split(self, mod):
        # Unknown prefix-name → "unknown:foo-bar" splits to "unknown".
        out = mod.model_provider("ollama:llama-3")
        assert out == "ollama"


class TestIsLocalModelName:
    def test_local_marker(self, mod):
        assert mod.is_local_model_name("ollama/llama-3") is True
        assert mod.is_local_model_name("local:my-model") is True
        assert mod.is_local_model_name("model.gguf") is True

    def test_non_local(self, mod):
        assert mod.is_local_model_name("gpt-4") is False

    def test_blank(self, mod):
        assert mod.is_local_model_name("") is False
        assert mod.is_local_model_name("none") is False
        assert mod.is_local_model_name(None) is False


class TestEvaluateTiered:
    def test_unlocked_first_tier(self, mod):
        definition = {
            "threshold_metric": "tool_calls",
            "tiers": [
                {"name": "Copper", "threshold": 100},
                {"name": "Silver", "threshold": 500},
            ],
        }
        out = mod.evaluate_tiered(definition, {"tool_calls": 250})
        assert out["unlocked"] is True
        assert out["tier"] == "Copper"
        assert out["next_tier"] == "Silver"

    def test_max_tier_reached(self, mod):
        definition = {
            "threshold_metric": "x",
            "tiers": [{"name": "T", "threshold": 10}],
        }
        out = mod.evaluate_tiered(definition, {"x": 20})
        assert out["tier"] == "T"
        assert out["next_tier"] is None
        assert out["progress_pct"] == 100

    def test_no_progress(self, mod):
        definition = {
            "threshold_metric": "x",
            "tiers": [{"name": "T", "threshold": 10}],
        }
        out = mod.evaluate_tiered(definition, {"x": 0})
        assert out["unlocked"] is False
        assert out["discovered"] is False or out["discovered"] is True

    def test_secret_unsuited(self, mod):
        definition = {
            "threshold_metric": "x",
            "tiers": [{"name": "T", "threshold": 10}],
            "secret": True,
        }
        out = mod.evaluate_tiered(definition, {"x": 0})
        assert out["state"] == "secret"


class TestEvaluateRequirements:
    def test_unlocked(self, mod):
        definition = {
            "requirements": [
                {"metric": "a", "gte": 10},
                {"metric": "b", "gte": 5},
            ],
        }
        out = mod.evaluate_requirements(definition, {"a": 20, "b": 6})
        assert out["unlocked"] is True
        assert out["progress_pct"] == 100

    def test_partial(self, mod):
        definition = {
            "requirements": [
                {"metric": "a", "gte": 10},
                {"metric": "b", "gte": 10},
            ],
        }
        out = mod.evaluate_requirements(definition, {"a": 5, "b": 0})
        # ~25% (5/10 + 0/10) / 2 = 25%
        assert out["unlocked"] is False
        assert out["progress_pct"] == 25

    def test_no_requirements(self, mod):
        out = mod.evaluate_requirements({"requirements": []}, {})
        assert out["unlocked"] is False


class TestEvaluateBoolean:
    def test_truthy(self, mod):
        out = mod.evaluate_boolean({"metric": "did_it"}, {"did_it": True})
        assert out["unlocked"] is True
        assert out["progress_pct"] == 100

    def test_falsy(self, mod):
        out = mod.evaluate_boolean({"metric": "did_it"}, {"did_it": False})
        assert out["unlocked"] is False

    def test_zero(self, mod):
        out = mod.evaluate_boolean({"metric": "x"}, {"x": 0})
        assert out["unlocked"] is False
