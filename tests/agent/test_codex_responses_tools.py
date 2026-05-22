"""Coverage for ``_responses_tools`` in ``agent.codex_responses_adapter``
— chat-completions tool schemas → Responses function-tool schemas."""
from __future__ import annotations

import pytest

from agent.codex_responses_adapter import _responses_tools


class TestResponsesTools:
    def test_none_returns_none(self):
        assert _responses_tools(None) is None

    def test_empty_list_returns_none(self):
        assert _responses_tools([]) is None

    def test_basic_tool_translated(self):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a file from disk",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                    },
                },
            },
        ]
        out = _responses_tools(tools)
        assert out is not None
        assert len(out) == 1
        t = out[0]
        assert t["type"] == "function"
        assert t["name"] == "read_file"
        assert t["description"] == "Read a file from disk"
        assert t["strict"] is False
        assert t["parameters"]["type"] == "object"

    def test_missing_function_block_skipped(self):
        # Entry without function key is silently skipped (no name to use).
        out = _responses_tools([{"type": "function"}])
        assert out is None

    def test_missing_name_skipped(self):
        out = _responses_tools([{"function": {"description": "x"}}])
        assert out is None

    def test_blank_name_skipped(self):
        out = _responses_tools([{"function": {"name": "  "}}])
        assert out is None

    def test_missing_parameters_defaults_to_empty_object_schema(self):
        out = _responses_tools([{"function": {"name": "foo"}}])
        assert out is not None
        assert out[0]["parameters"] == {"type": "object", "properties": {}}

    def test_missing_description_defaults_to_empty_string(self):
        out = _responses_tools([{"function": {"name": "foo"}}])
        assert out[0]["description"] == ""

    def test_non_dict_item_skipped(self):
        out = _responses_tools(["string", 42, None])
        assert out is None

    def test_strict_field_pinned_false(self):
        # Pinned False per design — strict-schema is opt-in and not
        # exposed via this translator.
        out = _responses_tools([{"function": {"name": "foo"}}])
        assert out[0]["strict"] is False
