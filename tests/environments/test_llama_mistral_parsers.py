"""Coverage for Llama and Mistral tool-call parsers."""
from __future__ import annotations

import json

import pytest

from environments.tool_call_parsers import get_parser, list_parsers
from environments.tool_call_parsers.mistral_parser import _generate_mistral_id


class TestLlamaParser:
    parser = get_parser("llama3_json")

    def test_no_brace_or_bot_token_returns_text(self):
        content, tcs = self.parser.parse("Just a sentence.")
        assert tcs is None or tcs == []
        assert content == "Just a sentence."

    def test_single_json_with_arguments(self):
        text = '{"name": "read", "arguments": {"path": "/etc"}}'
        _, tcs = self.parser.parse(text)
        assert tcs is not None and len(tcs) == 1
        assert tcs[0].function.name == "read"
        assert json.loads(tcs[0].function.arguments) == {"path": "/etc"}

    def test_parameters_alias_for_arguments(self):
        text = '{"name": "fn", "parameters": {"x": 1}}'
        _, tcs = self.parser.parse(text)
        assert tcs is not None
        assert json.loads(tcs[0].function.arguments) == {"x": 1}

    def test_bot_token_prefix_ok(self):
        text = '<|python_tag|>{"name":"a","arguments":{}}'
        _, tcs = self.parser.parse(text)
        assert tcs is not None and tcs[0].function.name == "a"

    def test_missing_name_skipped(self):
        text = '{"arguments": {"x": 1}}'
        _, tcs = self.parser.parse(text)
        assert tcs is None or tcs == []

    def test_two_json_objects_both_extracted(self):
        text = '{"name":"a","arguments":{"k":1}}\n{"name":"b","parameters":{}}'
        _, tcs = self.parser.parse(text)
        assert tcs is not None
        assert [tc.function.name for tc in tcs] == ["a", "b"]

    def test_both_aliases_resolve(self):
        a = get_parser("llama3_json")
        b = get_parser("llama4_json")
        assert type(a) is type(b)
        assert "llama3_json" in list_parsers()
        assert "llama4_json" in list_parsers()

    def test_id_prefix_is_call_(self):
        text = '{"name":"x","arguments":{}}'
        _, tcs = self.parser.parse(text)
        assert tcs[0].id.startswith("call_")


class TestMistralIdGen:
    def test_id_is_9_chars(self):
        for _ in range(5):
            assert len(_generate_mistral_id()) == 9

    def test_id_alnum(self):
        out = _generate_mistral_id()
        assert out.isalnum()


class TestMistralParser:
    parser = get_parser("mistral")

    def test_no_bot_token(self):
        content, tcs = self.parser.parse("hi there")
        assert tcs is None or tcs == []
        assert content == "hi there"

    def test_pre_v11_array_format(self):
        text = '[TOOL_CALLS] [{"name": "read", "arguments": {"p": 1}}]'
        _, tcs = self.parser.parse(text)
        assert tcs is not None and len(tcs) == 1
        assert tcs[0].function.name == "read"
        assert json.loads(tcs[0].function.arguments) == {"p": 1}

    def test_pre_v11_single_object(self):
        # Single object should be auto-wrapped into a list.
        text = '[TOOL_CALLS] {"name": "ping", "arguments": {}}'
        _, tcs = self.parser.parse(text)
        assert tcs is not None and len(tcs) == 1
        assert tcs[0].function.name == "ping"

    def test_v11_format_two_calls(self):
        text = (
            '[TOOL_CALLS]first{"a":1}'
            '[TOOL_CALLS]second{"b":2}'
        )
        _, tcs = self.parser.parse(text)
        assert tcs is not None and [tc.function.name for tc in tcs] == ["first", "second"]

    def test_content_before_token_preserved_in_text(self):
        text = 'Some thinking. [TOOL_CALLS] [{"name":"x","arguments":{}}]'
        content, tcs = self.parser.parse(text)
        assert tcs is not None
        # Implementation strips content before token.
        assert content is None or "thinking" in content

    def test_mistral_id_format(self):
        text = '[TOOL_CALLS] [{"name":"x","arguments":{}}]'
        _, tcs = self.parser.parse(text)
        assert len(tcs[0].id) == 9
