"""Coverage for Qwen3-Coder and GLM 4.7 parsers."""
from __future__ import annotations

import json

import pytest

from environments.tool_call_parsers import get_parser, list_parsers
from environments.tool_call_parsers.qwen3_coder_parser import _try_convert_value


class TestTryConvertValue:
    def test_null(self):
        assert _try_convert_value("null") is None
        assert _try_convert_value("NULL") is None
        assert _try_convert_value("  null  ") is None

    def test_int(self):
        assert _try_convert_value("42") == 42

    def test_float(self):
        assert _try_convert_value("3.14") == 3.14

    def test_bool_lowercase(self):
        assert _try_convert_value("true") is True
        assert _try_convert_value("false") is False

    def test_json_object(self):
        assert _try_convert_value('{"a": 1}') == {"a": 1}

    def test_json_array(self):
        assert _try_convert_value("[1, 2, 3]") == [1, 2, 3]

    def test_python_tuple_fallback(self):
        # JSON fails, literal_eval succeeds.
        assert _try_convert_value("(1, 2)") == (1, 2)

    def test_plain_string_fallback(self):
        assert _try_convert_value("hello world") == "hello world"

    def test_strip_outer_whitespace(self):
        # When all conversions fail, returns stripped string.
        assert _try_convert_value("  hello  ") == "hello"


class TestQwen3CoderParser:
    parser = get_parser("qwen3_coder")

    def test_no_tag_passthrough(self):
        content, tcs = self.parser.parse("hello")
        assert tcs is None or tcs == []
        assert content == "hello"

    def test_single_call_with_one_param(self):
        text = (
            "<tool_call>\n"
            "<function=read_file>\n"
            "<parameter=path>/etc/hosts</parameter>\n"
            "</function>\n"
            "</tool_call>"
        )
        _, tcs = self.parser.parse(text)
        assert tcs is not None and len(tcs) == 1
        assert tcs[0].function.name == "read_file"
        args = json.loads(tcs[0].function.arguments)
        assert args.get("path") == "/etc/hosts"

    def test_multiple_params(self):
        text = (
            "<tool_call>\n"
            "<function=run>\n"
            "<parameter=cmd>ls</parameter>\n"
            "<parameter=timeout>30</parameter>\n"
            "</function>\n"
            "</tool_call>"
        )
        _, tcs = self.parser.parse(text)
        assert tcs is not None
        args = json.loads(tcs[0].function.arguments)
        assert args.get("cmd") == "ls"
        # int is type-coerced via _try_convert_value
        assert args.get("timeout") == 30

    def test_id_prefix_call(self):
        text = (
            "<tool_call><function=f><parameter=x>1</parameter></function></tool_call>"
        )
        _, tcs = self.parser.parse(text)
        assert tcs[0].id.startswith("call_")

    def test_registered(self):
        assert "qwen3_coder" in list_parsers()


class TestGlm47Parser:
    parser = get_parser("glm47")

    def test_registered(self):
        assert "glm47" in list_parsers()

    def test_inherits_from_glm45(self):
        from environments.tool_call_parsers.glm45_parser import Glm45ToolCallParser
        assert isinstance(self.parser, Glm45ToolCallParser)

    def test_no_tag_passthrough(self):
        content, tcs = self.parser.parse("just words")
        assert tcs is None or tcs == []
        assert content == "just words"
