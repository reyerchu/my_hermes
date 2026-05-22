"""Extra coverage for additional tool-call parsers: llama, glm45, glm47,
deepseek_v3, mistral, hermes, kimi_k2.  Each parser is registered under
its own name; we verify the dispatch contract is honoured."""
from __future__ import annotations

import json

import pytest

from environments.tool_call_parsers import get_parser, list_parsers


class TestRegisteredParsers:
    @pytest.mark.parametrize("name", [
        "hermes", "qwen", "longcat", "llama3_json", "llama4_json",
        "glm45", "glm47", "deepseek_v3", "mistral", "kimi_k2",
    ])
    def test_parser_is_listed_and_constructable(self, name: str):
        names = list_parsers()
        assert name in names
        # Construction shouldn't crash.
        parser = get_parser(name)
        assert parser is not None
        assert hasattr(parser, "parse")


class TestLlamaJsonParser:
    def test_no_tool_call_returns_text_passthrough(self):
        parser = get_parser("llama3_json")
        out = parser.parse("Plain assistant reply, no JSON.")
        assert out[1] is None or out[1] == []

    def test_extracts_a_basic_function_call(self):
        parser = get_parser("llama3_json")
        text = json.dumps({"name": "read_file", "arguments": {"path": "/x"}})
        content, tool_calls = parser.parse(text)
        assert tool_calls is not None
        assert tool_calls[0].function.name == "read_file"
        assert json.loads(tool_calls[0].function.arguments) == {"path": "/x"}

    def test_accepts_parameters_key_alias(self):
        # Some Llama variants emit "parameters" instead of "arguments".
        parser = get_parser("llama3_json")
        text = json.dumps({"name": "foo", "parameters": {"y": 2}})
        _, tool_calls = parser.parse(text)
        assert tool_calls is not None
        assert tool_calls[0].function.name == "foo"


class TestHermesParser:
    def test_no_tool_call_returns_text(self):
        parser = get_parser("hermes")
        out = parser.parse("just text")
        assert out[1] is None or out[1] == []

    def test_extracts_standard_call(self):
        parser = get_parser("hermes")
        text = (
            '<tool_call>{"name":"x","arguments":{"k":"v"}}</tool_call>'
        )
        _, tool_calls = parser.parse(text)
        assert tool_calls is not None
        assert tool_calls[0].function.name == "x"


class TestGlmParsers:
    @pytest.mark.parametrize("name", ["glm45", "glm47"])
    def test_no_tool_call_returns_text(self, name):
        parser = get_parser(name)
        out = parser.parse("plain reply")
        assert out[1] is None or out[1] == []


class TestMistralParser:
    def test_no_token_returns_text(self):
        parser = get_parser("mistral")
        out = parser.parse("plain reply without [TOOL_CALLS]")
        assert out[1] is None or out[1] == []

    def test_extracts_pre_v11_json_array(self):
        parser = get_parser("mistral")
        text = (
            '[TOOL_CALLS] [{"name":"foo","arguments":{"x":1}}]'
        )
        _, tool_calls = parser.parse(text)
        assert tool_calls is not None
        assert tool_calls[0].function.name == "foo"


class TestDeepseekParser:
    def test_no_call_returns_text(self):
        parser = get_parser("deepseek_v3")
        out = parser.parse("regular content")
        assert out[1] is None or out[1] == []
