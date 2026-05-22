"""Coverage for _preflight_codex_input_items in
agent.codex_responses_adapter."""
from __future__ import annotations

import json

import pytest

from agent.codex_responses_adapter import _preflight_codex_input_items


class TestPreflightCodexInputItems:
    def test_non_list_raises(self):
        with pytest.raises(ValueError, match="list of input items"):
            _preflight_codex_input_items("not a list")

    def test_non_dict_item_raises(self):
        with pytest.raises(ValueError, match="must be an object"):
            _preflight_codex_input_items(["string"])

    def test_function_call_missing_call_id_raises(self):
        with pytest.raises(ValueError, match="call_id"):
            _preflight_codex_input_items([{
                "type": "function_call",
                "name": "fn",
            }])

    def test_function_call_missing_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            _preflight_codex_input_items([{
                "type": "function_call",
                "call_id": "c1",
            }])

    def test_function_call_normalized(self):
        out = _preflight_codex_input_items([{
            "type": "function_call",
            "call_id": " c1 ",
            "name": " fn ",
            "arguments": {"k": 1},
        }])
        assert len(out) == 1
        fn = out[0]
        assert fn["type"] == "function_call"
        assert fn["call_id"] == "c1"  # stripped
        assert fn["name"] == "fn"
        # dict arguments serialized to JSON string.
        assert json.loads(fn["arguments"]) == {"k": 1}

    def test_function_call_arguments_default(self):
        out = _preflight_codex_input_items([{
            "type": "function_call",
            "call_id": "c1",
            "name": "fn",
        }])
        # No arguments → "{}"
        assert out[0]["arguments"] == "{}"

    def test_function_call_blank_arguments_becomes_empty_object(self):
        out = _preflight_codex_input_items([{
            "type": "function_call",
            "call_id": "c1",
            "name": "fn",
            "arguments": "  ",
        }])
        assert out[0]["arguments"] == "{}"

    def test_function_call_arguments_passthrough_string(self):
        out = _preflight_codex_input_items([{
            "type": "function_call",
            "call_id": "c1",
            "name": "fn",
            "arguments": '{"a": 1}',
        }])
        assert json.loads(out[0]["arguments"]) == {"a": 1}

    def test_function_call_arguments_coerced_to_str(self):
        out = _preflight_codex_input_items([{
            "type": "function_call",
            "call_id": "c1",
            "name": "fn",
            "arguments": 42,
        }])
        # int → str(...) → "42"
        assert out[0]["arguments"] == "42"

    def test_function_call_output_missing_call_id_raises(self):
        with pytest.raises(ValueError, match="call_id"):
            _preflight_codex_input_items([{
                "type": "function_call_output",
                "output": "hello",
            }])

    def test_function_call_output_string_passes_through(self):
        out = _preflight_codex_input_items([{
            "type": "function_call_output",
            "call_id": "c1",
            "output": "hello",
        }])
        assert out[0]["output"] == "hello"

    def test_function_call_output_list_with_input_text(self):
        out = _preflight_codex_input_items([{
            "type": "function_call_output",
            "call_id": "c1",
            "output": [
                {"type": "input_text", "text": "hi"},
                {"type": "input_text", "text": ""},  # blank text dropped
                "not-a-dict",                        # non-dict dropped
            ],
        }])
        assert out[0]["output"] == [{"type": "input_text", "text": "hi"}]

    def test_function_call_output_list_with_image(self):
        out = _preflight_codex_input_items([{
            "type": "function_call_output",
            "call_id": "c1",
            "output": [
                {"type": "input_image", "image_url": "https://x", "detail": "high"},
                {"type": "input_image", "image_url": ""},  # missing url → drop
            ],
        }])
        # Only one image part survives.
        assert out[0]["output"] == [
            {"type": "input_image", "image_url": "https://x", "detail": "high"},
        ]

    def test_function_call_output_none(self):
        out = _preflight_codex_input_items([{
            "type": "function_call_output",
            "call_id": "c1",
            "output": None,
        }])
        # None coerced to empty string.
        assert out[0]["output"] == ""

    def test_function_call_output_empty_list_becomes_empty_string(self):
        out = _preflight_codex_input_items([{
            "type": "function_call_output",
            "call_id": "c1",
            "output": [],
        }])
        # Empty list of cleaned parts becomes "".
        assert out[0]["output"] == ""
