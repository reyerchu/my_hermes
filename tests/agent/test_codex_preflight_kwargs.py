"""Coverage for _preflight_codex_api_kwargs in
agent.codex_responses_adapter — the API-kwarg normaliser/validator."""
from __future__ import annotations

import pytest

from agent.codex_responses_adapter import _preflight_codex_api_kwargs


def _minimal_request(**overrides):
    base = {
        "model": "gpt-x",
        "instructions": "do things",
        "input": [],
        "store": False,
    }
    base.update(overrides)
    return base


class TestNonDictAndMissingFields:
    def test_non_dict_raises(self):
        with pytest.raises(ValueError, match="must be a dict"):
            _preflight_codex_api_kwargs("nope")

    def test_missing_required_raises(self):
        with pytest.raises(ValueError, match="missing required"):
            _preflight_codex_api_kwargs({"model": "x"})


class TestModelValidation:
    def test_empty_model_raises(self):
        with pytest.raises(ValueError, match="'model' must be a non-empty"):
            _preflight_codex_api_kwargs(_minimal_request(model=""))

    def test_whitespace_model_raises(self):
        with pytest.raises(ValueError, match="'model' must be a non-empty"):
            _preflight_codex_api_kwargs(_minimal_request(model="  "))

    def test_non_string_model_raises(self):
        with pytest.raises(ValueError, match="'model' must be a non-empty"):
            _preflight_codex_api_kwargs(_minimal_request(model=42))

    def test_model_stripped(self):
        out = _preflight_codex_api_kwargs(_minimal_request(model="  gpt-x  "))
        assert out["model"] == "gpt-x"


class TestInstructions:
    def test_string_passthrough(self):
        out = _preflight_codex_api_kwargs(_minimal_request(instructions="prompt"))
        assert out["instructions"] == "prompt"

    def test_none_uses_default(self):
        from agent.prompt_builder import DEFAULT_AGENT_IDENTITY
        out = _preflight_codex_api_kwargs(_minimal_request(instructions=None))
        assert out["instructions"] == DEFAULT_AGENT_IDENTITY

    def test_blank_uses_default(self):
        from agent.prompt_builder import DEFAULT_AGENT_IDENTITY
        out = _preflight_codex_api_kwargs(_minimal_request(instructions="   "))
        assert out["instructions"] == DEFAULT_AGENT_IDENTITY


class TestStore:
    def test_store_false_required(self):
        out = _preflight_codex_api_kwargs(_minimal_request(store=False))
        assert out["store"] is False

    def test_store_true_raises(self):
        with pytest.raises(ValueError, match="'store' to be false"):
            _preflight_codex_api_kwargs(_minimal_request(store=True))


class TestTools:
    def test_no_tools(self):
        out = _preflight_codex_api_kwargs(_minimal_request())
        assert "tools" not in out

    def test_non_list_tools_raises(self):
        with pytest.raises(ValueError, match="'tools' must be a list"):
            _preflight_codex_api_kwargs(_minimal_request(tools="not a list"))

    def test_non_dict_tool_entry_raises(self):
        with pytest.raises(ValueError, match="tools\\[0\\] must be"):
            _preflight_codex_api_kwargs(_minimal_request(tools=["str"]))

    def test_wrong_tool_type_raises(self):
        with pytest.raises(ValueError, match="unsupported type"):
            _preflight_codex_api_kwargs(_minimal_request(tools=[{
                "type": "code_interpreter",
                "name": "x",
                "parameters": {},
            }]))

    def test_missing_name_raises(self):
        with pytest.raises(ValueError, match="missing a valid name"):
            _preflight_codex_api_kwargs(_minimal_request(tools=[{
                "type": "function",
                "parameters": {},
            }]))

    def test_missing_parameters_raises(self):
        with pytest.raises(ValueError, match="missing valid parameters"):
            _preflight_codex_api_kwargs(_minimal_request(tools=[{
                "type": "function",
                "name": "fn",
            }]))

    def test_normalized_tool_structure(self):
        out = _preflight_codex_api_kwargs(_minimal_request(tools=[{
            "type": "function",
            "name": "  fn  ",
            "description": "  do  ",
            "parameters": {"type": "object"},
            "strict": "truthy",
        }]))
        tool = out["tools"][0]
        assert tool["name"] == "fn"
        # description currently NOT stripped (just normalised to string).
        assert "do" in tool["description"]
        assert tool["strict"] is True  # bool() coercion
        assert tool["parameters"] == {"type": "object"}


class TestUnsupportedKeys:
    def test_unexpected_key_raises(self):
        with pytest.raises(ValueError, match="unsupported field"):
            _preflight_codex_api_kwargs(_minimal_request(weird="field"))

    def test_stream_disallowed_by_default(self):
        with pytest.raises(ValueError, match="stream flag is only allowed"):
            _preflight_codex_api_kwargs(_minimal_request(stream=True))


class TestPassthroughs:
    def test_reasoning_dict_passthrough(self):
        out = _preflight_codex_api_kwargs(
            _minimal_request(reasoning={"effort": "high"}),
        )
        assert out["reasoning"] == {"effort": "high"}

    def test_reasoning_non_dict_dropped(self):
        out = _preflight_codex_api_kwargs(
            _minimal_request(reasoning="not a dict"),
        )
        assert "reasoning" not in out

    def test_max_output_tokens_int(self):
        out = _preflight_codex_api_kwargs(
            _minimal_request(max_output_tokens=100),
        )
        assert out["max_output_tokens"] == 100

    def test_max_output_tokens_zero_dropped(self):
        out = _preflight_codex_api_kwargs(
            _minimal_request(max_output_tokens=0),
        )
        assert "max_output_tokens" not in out

    def test_temperature_float(self):
        out = _preflight_codex_api_kwargs(
            _minimal_request(temperature=0.7),
        )
        assert out["temperature"] == 0.7

    def test_tool_choice_passthrough(self):
        out = _preflight_codex_api_kwargs(
            _minimal_request(tool_choice="auto"),
        )
        assert out["tool_choice"] == "auto"

    def test_service_tier_stripped(self):
        out = _preflight_codex_api_kwargs(
            _minimal_request(service_tier="  priority  "),
        )
        assert out["service_tier"] == "priority"


class TestExtraHeaders:
    def test_dict_passthrough(self):
        out = _preflight_codex_api_kwargs(
            _minimal_request(extra_headers={"X-Foo": "bar"}),
        )
        assert out["extra_headers"]["X-Foo"] == "bar"

    def test_non_dict_raises(self):
        with pytest.raises(ValueError, match="'extra_headers' must be an object"):
            _preflight_codex_api_kwargs(_minimal_request(extra_headers="x"))

    def test_blank_key_raises(self):
        with pytest.raises(ValueError, match="keys must be non-empty"):
            _preflight_codex_api_kwargs(_minimal_request(extra_headers={"": "v"}))

    def test_none_value_dropped(self):
        out = _preflight_codex_api_kwargs(
            _minimal_request(extra_headers={"X": None, "Y": "v"}),
        )
        # None dropped; Y survives.
        assert "X" not in out.get("extra_headers", {})
        assert out["extra_headers"]["Y"] == "v"

    def test_keys_stripped(self):
        out = _preflight_codex_api_kwargs(
            _minimal_request(extra_headers={"  X  ": "v"}),
        )
        assert "X" in out["extra_headers"]


class TestAllowStream:
    def test_allow_stream_true(self):
        out = _preflight_codex_api_kwargs(
            _minimal_request(stream=True),
            allow_stream=True,
        )
        assert out.get("stream") is True

    def test_allow_stream_with_false_raises(self):
        with pytest.raises(ValueError, match="'stream' must be true when set"):
            _preflight_codex_api_kwargs(
                _minimal_request(stream=False),
                allow_stream=True,
            )
