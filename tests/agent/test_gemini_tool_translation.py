"""Coverage for tool-call / tool-result translation helpers in
agent.gemini_native_adapter."""
from __future__ import annotations

import json

import pytest

from agent.gemini_native_adapter import (
    _translate_tool_call_to_gemini,
    _translate_tool_result_to_gemini,
)


class TestTranslateToolCallToGemini:
    def test_basic(self):
        out = _translate_tool_call_to_gemini({
            "function": {"name": "fn", "arguments": '{"a": 1}'},
        })
        assert out == {
            "functionCall": {"name": "fn", "args": {"a": 1}},
        }

    def test_missing_function_block(self):
        out = _translate_tool_call_to_gemini({})
        assert out["functionCall"]["name"] == ""
        assert out["functionCall"]["args"] == {}

    def test_empty_arguments_string(self):
        out = _translate_tool_call_to_gemini({"function": {"name": "fn", "arguments": ""}})
        assert out["functionCall"]["args"] == {}

    def test_invalid_json_arguments_wrapped(self):
        out = _translate_tool_call_to_gemini({
            "function": {"name": "fn", "arguments": "not-json"},
        })
        # Falls back to _raw wrapper.
        assert "_raw" in out["functionCall"]["args"]
        assert out["functionCall"]["args"]["_raw"] == "not-json"

    def test_non_dict_arguments_wrapped(self):
        out = _translate_tool_call_to_gemini({
            "function": {"name": "fn", "arguments": "[1, 2]"},
        })
        # JSON parses to a list — wrapped in _value.
        assert "_value" in out["functionCall"]["args"]

    def test_thought_signature_passed_through(self):
        out = _translate_tool_call_to_gemini({
            "function": {"name": "fn", "arguments": "{}"},
            "extra_content": {"google": {"thoughtSignature": "sig-blob"}},
        })
        assert "thoughtSignature" in out


class TestTranslateToolResultToGemini:
    def test_basic_string_content(self):
        out = _translate_tool_result_to_gemini({
            "role": "tool",
            "tool_call_id": "t1",
            "name": "fn",
            "content": "result text",
        })
        assert out["functionResponse"]["name"] == "fn"
        assert out["functionResponse"]["response"] == {"output": "result text"}

    def test_falls_back_to_tool_call_id_when_no_name(self):
        out = _translate_tool_result_to_gemini({
            "role": "tool",
            "tool_call_id": "call-1",
            "content": "x",
        })
        assert out["functionResponse"]["name"] == "call-1"

    def test_name_lookup_from_map(self):
        out = _translate_tool_result_to_gemini(
            {"tool_call_id": "t1", "content": "x"},
            tool_name_by_call_id={"t1": "lookup_name"},
        )
        assert out["functionResponse"]["name"] == "lookup_name"

    def test_default_name_when_all_missing(self):
        out = _translate_tool_result_to_gemini({"content": "x"})
        assert out["functionResponse"]["name"] == "tool"

    def test_json_object_content_parsed(self):
        out = _translate_tool_result_to_gemini({
            "name": "fn",
            "content": '{"result": "ok"}',
        })
        # JSON object → used directly as response.
        assert out["functionResponse"]["response"] == {"result": "ok"}

    def test_json_array_content_wrapped(self):
        out = _translate_tool_result_to_gemini({
            "name": "fn",
            "content": '[1, 2, 3]',
        })
        # Non-dict parsed → falls back to output wrapper.
        assert out["functionResponse"]["response"]["output"] == "[1, 2, 3]"

    def test_invalid_json_wrapped(self):
        out = _translate_tool_result_to_gemini({
            "name": "fn",
            "content": "{not-json",
        })
        # parse fails → output wrapper.
        assert out["functionResponse"]["response"]["output"] == "{not-json"
