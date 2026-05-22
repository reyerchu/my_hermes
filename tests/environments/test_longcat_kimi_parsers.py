"""Coverage for Longcat Flash and Kimi K2 tool-call parsers."""
from __future__ import annotations

import json

import pytest

from environments.tool_call_parsers import get_parser, list_parsers


class TestLongcatParser:
    parser = get_parser("longcat")

    def test_no_tag_passthrough(self):
        content, tcs = self.parser.parse("hello")
        assert tcs is None or tcs == []
        assert content == "hello"

    def test_single_closed_tag(self):
        text = '<longcat_tool_call>{"name":"x","arguments":{"a":1}}</longcat_tool_call>'
        _, tcs = self.parser.parse(text)
        assert tcs is not None and len(tcs) == 1
        assert tcs[0].function.name == "x"
        assert json.loads(tcs[0].function.arguments) == {"a": 1}

    def test_unclosed_tag(self):
        text = '<longcat_tool_call>{"name":"y"}'
        _, tcs = self.parser.parse(text)
        assert tcs is not None and tcs[0].function.name == "y"

    def test_arguments_default_empty_dict(self):
        text = '<longcat_tool_call>{"name":"z"}</longcat_tool_call>'
        _, tcs = self.parser.parse(text)
        assert json.loads(tcs[0].function.arguments) == {}

    def test_two_calls(self):
        text = (
            '<longcat_tool_call>{"name":"a"}</longcat_tool_call>'
            '<longcat_tool_call>{"name":"b"}</longcat_tool_call>'
        )
        _, tcs = self.parser.parse(text)
        assert [tc.function.name for tc in tcs] == ["a", "b"]

    def test_id_prefix_is_call_(self):
        text = '<longcat_tool_call>{"name":"x"}</longcat_tool_call>'
        _, tcs = self.parser.parse(text)
        assert tcs[0].id.startswith("call_")

    def test_blank_inside_tags_skipped(self):
        text = '<longcat_tool_call>  </longcat_tool_call>'
        _, tcs = self.parser.parse(text)
        assert tcs is None or tcs == []

    def test_leading_content_preserved(self):
        text = (
            'thinking…\n'
            '<longcat_tool_call>{"name":"fn"}</longcat_tool_call>'
        )
        content, tcs = self.parser.parse(text)
        assert tcs is not None
        # Implementation strips before tag.
        assert content is None or "thinking" in content


class TestKimiK2Parser:
    parser = get_parser("kimi_k2")

    def test_no_start_token_passthrough(self):
        content, tcs = self.parser.parse("nope")
        assert tcs is None or tcs == []
        assert content == "nope"

    def test_basic_call_with_functions_prefix(self):
        text = (
            "<|tool_calls_section_begin|>"
            "<|tool_call_begin|>functions.get_weather:0"
            "<|tool_call_argument_begin|>"
            '{"city": "TPE"}'
            "<|tool_call_end|>"
            "<|tool_calls_section_end|>"
        )
        _, tcs = self.parser.parse(text)
        assert tcs is not None and len(tcs) == 1
        # "functions.get_weather:0" → "get_weather"
        assert tcs[0].function.name == "get_weather"
        assert tcs[0].function.arguments == '{"city": "TPE"}'
        # Original full id preserved.
        assert tcs[0].id == "functions.get_weather:0"

    def test_no_dot_prefix_uses_bare_name(self):
        text = (
            "<|tool_calls_section_begin|>"
            "<|tool_call_begin|>bare_name:1"
            "<|tool_call_argument_begin|>"
            '{}'
            "<|tool_call_end|>"
            "<|tool_calls_section_end|>"
        )
        _, tcs = self.parser.parse(text)
        assert tcs is not None
        assert tcs[0].function.name == "bare_name"

    def test_singular_section_variant_recognized(self):
        # <|tool_call_section_begin|> (singular) is also accepted.
        text = (
            "<|tool_call_section_begin|>"
            "<|tool_call_begin|>x.fn:0"
            "<|tool_call_argument_begin|>"
            '{}'
            "<|tool_call_end|>"
            "<|tool_call_section_end|>"
        )
        _, tcs = self.parser.parse(text)
        assert tcs is not None
        assert tcs[0].function.name == "fn"

    def test_two_calls_back_to_back(self):
        text = (
            "<|tool_calls_section_begin|>"
            "<|tool_call_begin|>f.a:0<|tool_call_argument_begin|>{}<|tool_call_end|>"
            "<|tool_call_begin|>f.b:1<|tool_call_argument_begin|>{}<|tool_call_end|>"
            "<|tool_calls_section_end|>"
        )
        _, tcs = self.parser.parse(text)
        assert tcs is not None and [tc.function.name for tc in tcs] == ["a", "b"]

    def test_args_whitespace_stripped(self):
        text = (
            "<|tool_calls_section_begin|>"
            "<|tool_call_begin|>f.x:0<|tool_call_argument_begin|>"
            '   {"k":1}   '
            "<|tool_call_end|>"
            "<|tool_calls_section_end|>"
        )
        _, tcs = self.parser.parse(text)
        assert tcs[0].function.arguments == '{"k":1}'


class TestRegistration:
    def test_longcat_registered(self):
        assert "longcat" in list_parsers()

    def test_kimi_registered(self):
        assert "kimi_k2" in list_parsers()
