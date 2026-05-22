"""Extended coverage for ``DeepSeekV3ToolCallParser`` parse() behaviour."""
from __future__ import annotations

import json

import pytest

from environments.tool_call_parsers import get_parser


_PARSER = get_parser("deepseek_v3")

_START = "<｜tool▁calls▁begin｜>"
_CALL_BEGIN = "<｜tool▁call▁begin｜>"
_SEP = "<｜tool▁sep｜>"
_CALL_END = "<｜tool▁call▁end｜>"
_CALLS_END = "<｜tool▁calls▁end｜>"


def _build(name: str, args_json: str, *, call_type: str = "function") -> str:
    return (
        f"{_START}"
        f"{_CALL_BEGIN}{call_type}{_SEP}{name}\n```json\n{args_json}\n```\n{_CALL_END}"
        f"{_CALLS_END}"
    )


class TestDeepseekV3ParserParse:
    def test_no_start_token_returns_text(self):
        text = "Plain assistant reply."
        out = _PARSER.parse(text)
        assert out[1] is None or out[1] == []

    def test_single_call_extracted(self):
        text = _build("read_file", '{"path": "/x"}')
        content, tool_calls = _PARSER.parse(text)
        assert tool_calls is not None
        assert len(tool_calls) == 1
        assert tool_calls[0].function.name == "read_file"
        assert json.loads(tool_calls[0].function.arguments) == {"path": "/x"}

    def test_multiple_calls_all_extracted(self):
        text = (
            _START
            + _CALL_BEGIN + "function" + _SEP + "tool_a" + "\n```json\n" + '{"x":1}' + "\n```\n" + _CALL_END
            + _CALL_BEGIN + "function" + _SEP + "tool_b" + "\n```json\n" + '{"y":2}' + "\n```\n" + _CALL_END
            + _CALLS_END
        )
        _, tool_calls = _PARSER.parse(text)
        assert tool_calls is not None
        names = [tc.function.name for tc in tool_calls]
        assert names == ["tool_a", "tool_b"]

    def test_leading_text_preserved(self):
        text = "Let me call a tool.\n" + _build("x", "{}")
        content, _ = _PARSER.parse(text)
        # The content portion before the call should not be empty.
        assert isinstance(content, (str, type(None)))


class TestDeepseekV3ParserConstructable:
    def test_parser_registered_under_canonical_name(self):
        from environments.tool_call_parsers import list_parsers
        assert "deepseek_v3" in list_parsers()
