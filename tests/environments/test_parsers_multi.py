"""Coverage for hermes/qwen/glm45 tool-call parsers."""
from __future__ import annotations

import json

import pytest

from environments.tool_call_parsers import get_parser
from environments.tool_call_parsers.glm45_parser import _deserialize_value


class TestHermesParser:
    parser = get_parser("hermes")

    def test_no_tag_returns_raw(self):
        content, tcs = self.parser.parse("just a string")
        assert tcs is None
        assert content == "just a string"

    def test_single_closed_tag(self):
        text = '<tool_call>{"name": "read", "arguments": {"p": 1}}</tool_call>'
        content, tcs = self.parser.parse(text)
        assert tcs is not None and len(tcs) == 1
        assert tcs[0].function.name == "read"
        assert json.loads(tcs[0].function.arguments) == {"p": 1}

    def test_unclosed_tag_at_eof(self):
        text = '<tool_call>{"name": "write", "arguments": {"x": 2}}'
        content, tcs = self.parser.parse(text)
        assert tcs is not None and len(tcs) == 1
        assert tcs[0].function.name == "write"

    def test_blank_tag_skipped(self):
        # Empty body inside tags returns None tool_calls.
        text = "<tool_call>   </tool_call>"
        _, tcs = self.parser.parse(text)
        assert tcs is None or tcs == []

    def test_missing_name_skipped(self):
        text = '<tool_call>{"arguments": {}}</tool_call>'
        _, tcs = self.parser.parse(text)
        assert tcs is None or tcs == []

    def test_args_default_to_empty_object(self):
        text = '<tool_call>{"name": "ping"}</tool_call>'
        _, tcs = self.parser.parse(text)
        assert tcs is not None and len(tcs) == 1
        assert json.loads(tcs[0].function.arguments) == {}

    def test_id_prefix_is_call_(self):
        text = '<tool_call>{"name": "ping"}</tool_call>'
        _, tcs = self.parser.parse(text)
        assert tcs[0].id.startswith("call_")

    def test_two_calls_extracted(self):
        text = (
            '<tool_call>{"name":"a"}</tool_call>'
            '<tool_call>{"name":"b"}</tool_call>'
        )
        _, tcs = self.parser.parse(text)
        assert tcs is not None and [tc.function.name for tc in tcs] == ["a", "b"]


class TestQwenParserAliasesHermes:
    """Qwen 2.5 uses the same <tool_call> format as Hermes."""

    def test_qwen_registered(self):
        from environments.tool_call_parsers import list_parsers
        assert "qwen" in list_parsers()

    def test_same_behaviour_as_hermes(self):
        parser = get_parser("qwen")
        text = '<tool_call>{"name":"x","arguments":{"k":"v"}}</tool_call>'
        _, tcs = parser.parse(text)
        assert tcs is not None
        assert tcs[0].function.name == "x"


class TestGlm45Deserialize:
    def test_json_int(self):
        assert _deserialize_value("42") == 42

    def test_json_bool(self):
        assert _deserialize_value("true") is True

    def test_json_object(self):
        assert _deserialize_value('{"a": 1}') == {"a": 1}

    def test_python_literal_tuple(self):
        # JSON fails; literal_eval succeeds.
        assert _deserialize_value("(1, 2)") == (1, 2)

    def test_raw_string_fallback(self):
        # Neither JSON nor literal_eval handle bare identifiers.
        assert _deserialize_value("hello world") == "hello world"

    def test_empty_string(self):
        # json.loads fails on "", literal_eval fails — fall back to raw "".
        assert _deserialize_value("") == ""


class TestGlm45Parser:
    parser = get_parser("glm45")

    def test_no_tag_passthrough(self):
        content, tcs = self.parser.parse("nothing here")
        assert tcs is None or tcs == []
        assert content == "nothing here"

    def test_basic_call_parsed(self):
        text = (
            "<tool_call>my_func\n"
            "<arg_key>n</arg_key><arg_value>3</arg_value>\n"
            "<arg_key>s</arg_key><arg_value>hello</arg_value>\n"
            "</tool_call>"
        )
        _, tcs = self.parser.parse(text)
        assert tcs is not None and len(tcs) == 1
        assert tcs[0].function.name == "my_func"
        args = json.loads(tcs[0].function.arguments)
        assert args["n"] == 3
        assert args["s"] == "hello"

    def test_id_uses_call_prefix(self):
        text = (
            "<tool_call>fn\n"
            "<arg_key>k</arg_key><arg_value>1</arg_value>\n"
            "</tool_call>"
        )
        _, tcs = self.parser.parse(text)
        assert tcs[0].id.startswith("call_")
