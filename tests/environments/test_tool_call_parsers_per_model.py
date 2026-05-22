"""Per-parser coverage for tool-call parsers that aren't directly covered
by tests/tools/test_tool_call_parsers.py."""
from __future__ import annotations

import json

import pytest

from environments.tool_call_parsers import get_parser


class TestQwenParser:
    """Qwen 2.5 reuses Hermes's <tool_call> format — verify the parser
    is registered and decodes the standard payload."""

    def test_get_parser_returns_instance(self):
        parser = get_parser("qwen")
        assert parser is not None

    def test_parses_a_basic_tool_call(self):
        parser = get_parser("qwen")
        text = (
            '<tool_call>{"name":"foo","arguments":{"x":1}}</tool_call>'
        )
        content, tool_calls = parser.parse(text)
        assert tool_calls is not None
        assert len(tool_calls) == 1
        assert tool_calls[0].function.name == "foo"
        assert json.loads(tool_calls[0].function.arguments) == {"x": 1}

    def test_no_tool_calls_returns_original_text(self):
        parser = get_parser("qwen")
        text = "plain text answer"
        content, tool_calls = parser.parse(text)
        assert tool_calls is None
        assert content == text


class TestLongcatParser:
    def test_get_parser_returns_instance(self):
        parser = get_parser("longcat")
        assert parser is not None

    def test_parses_basic_longcat_call(self):
        parser = get_parser("longcat")
        text = (
            '<longcat_tool_call>{"name":"bar","arguments":{"y":2}}</longcat_tool_call>'
        )
        content, tool_calls = parser.parse(text)
        assert tool_calls is not None
        assert tool_calls[0].function.name == "bar"
        assert json.loads(tool_calls[0].function.arguments) == {"y": 2}

    def test_unterminated_longcat_call(self):
        # The pattern allows a missing closing tag.
        parser = get_parser("longcat")
        text = '<longcat_tool_call>{"name":"x","arguments":{}}'
        content, tool_calls = parser.parse(text)
        assert tool_calls is not None
        assert tool_calls[0].function.name == "x"

    def test_no_tag_returns_text(self):
        parser = get_parser("longcat")
        out = parser.parse("plain")
        assert out == ("plain", None)

    def test_malformed_json_falls_back_to_text(self):
        parser = get_parser("longcat")
        text = "<longcat_tool_call>not json</longcat_tool_call>"
        content, tool_calls = parser.parse(text)
        # The try/except swallows; helper returns original text + None.
        assert tool_calls is None
        assert content == text

    def test_leading_content_preserved(self):
        parser = get_parser("longcat")
        text = (
            "Let me call a tool.\n"
            '<longcat_tool_call>{"name":"go","arguments":{}}</longcat_tool_call>'
        )
        content, tool_calls = parser.parse(text)
        assert tool_calls is not None
        assert content == "Let me call a tool."

    def test_multiple_calls_all_parsed(self):
        parser = get_parser("longcat")
        text = (
            '<longcat_tool_call>{"name":"a","arguments":{}}</longcat_tool_call>'
            '<longcat_tool_call>{"name":"b","arguments":{}}</longcat_tool_call>'
        )
        content, tool_calls = parser.parse(text)
        assert tool_calls is not None
        assert [tc.function.name for tc in tool_calls] == ["a", "b"]


class TestGetParserDispatch:
    def test_get_parser_for_unknown_name_raises(self):
        with pytest.raises(Exception):
            get_parser("totally-unknown-parser")

    def test_known_parsers_are_listed(self):
        from environments.tool_call_parsers import list_parsers
        names = list_parsers()
        assert "hermes" in names
        assert "qwen" in names
        assert "longcat" in names
