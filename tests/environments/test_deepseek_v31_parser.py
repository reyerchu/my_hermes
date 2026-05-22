"""Coverage for DeepSeekV31ToolCallParser."""
from __future__ import annotations

import pytest

from environments.tool_call_parsers import get_parser, list_parsers

PARSER = get_parser("deepseek_v3_1")

START = "<｜tool▁calls▁begin｜>"
CALL_BEGIN = "<｜tool▁call▁begin｜>"
SEP = "<｜tool▁sep｜>"
CALL_END = "<｜tool▁call▁end｜>"
CALLS_END = "<｜tool▁calls▁end｜>"


def _wrap(name: str, args: str) -> str:
    return f"{START}{CALL_BEGIN}{name}{SEP}{args}{CALL_END}{CALLS_END}"


class TestDeepseekV31Parse:
    def test_no_start_token(self):
        content, tcs = PARSER.parse("hello")
        assert tcs is None or tcs == []
        assert content == "hello"

    def test_single_call(self):
        text = _wrap("read", '{"p":"x"}')
        content, tcs = PARSER.parse(text)
        assert tcs is not None and len(tcs) == 1
        assert tcs[0].function.name == "read"
        assert tcs[0].function.arguments == '{"p":"x"}'

    def test_id_prefix_call(self):
        text = _wrap("ping", "{}")
        _, tcs = PARSER.parse(text)
        assert tcs[0].id.startswith("call_")

    def test_multiple_calls(self):
        text = (
            START
            + CALL_BEGIN + "a" + SEP + '{"x":1}' + CALL_END
            + CALL_BEGIN + "b" + SEP + '{"y":2}' + CALL_END
            + CALLS_END
        )
        _, tcs = PARSER.parse(text)
        assert [tc.function.name for tc in tcs] == ["a", "b"]

    def test_leading_content_preserved(self):
        text = "thinking...\n" + _wrap("fn", "{}")
        content, tcs = PARSER.parse(text)
        assert tcs is not None
        assert content == "thinking..."

    def test_args_whitespace_stripped(self):
        text = _wrap("fn", '  {"a":1}  ')
        _, tcs = PARSER.parse(text)
        assert tcs[0].function.arguments == '{"a":1}'

    def test_name_whitespace_stripped(self):
        text = _wrap("  fn  ", "{}")
        _, tcs = PARSER.parse(text)
        assert tcs[0].function.name == "fn"


class TestDeepseekV31Aliases:
    def test_both_aliases_registered(self):
        names = list_parsers()
        assert "deepseek_v3_1" in names
        assert "deepseek_v31" in names

    def test_both_aliases_resolve_to_same_class(self):
        a = get_parser("deepseek_v3_1")
        b = get_parser("deepseek_v31")
        assert type(a) is type(b)
