"""Coverage for _translate_tools_to_gemini in
agent.gemini_native_adapter."""
from __future__ import annotations

import pytest

from agent.gemini_native_adapter import _translate_tools_to_gemini


class TestTranslateToolsToGemini:
    def test_non_list(self):
        assert _translate_tools_to_gemini("not a list") == []

    def test_none(self):
        assert _translate_tools_to_gemini(None) == []

    def test_empty(self):
        assert _translate_tools_to_gemini([]) == []

    def test_basic_single_tool(self):
        out = _translate_tools_to_gemini([{
            "type": "function",
            "function": {
                "name": "fn",
                "description": "do thing",
                "parameters": {"type": "object", "properties": {}},
            },
        }])
        assert len(out) == 1
        decls = out[0]["functionDeclarations"]
        assert len(decls) == 1
        assert decls[0]["name"] == "fn"
        assert decls[0]["description"] == "do thing"
        assert "parameters" in decls[0]

    def test_multiple_tools_in_one_declaration_block(self):
        out = _translate_tools_to_gemini([
            {"function": {"name": "a", "parameters": {"type": "object"}}},
            {"function": {"name": "b", "parameters": {"type": "object"}}},
        ])
        # All declarations collapse into one functionDeclarations block.
        assert len(out) == 1
        names = [d["name"] for d in out[0]["functionDeclarations"]]
        assert names == ["a", "b"]

    def test_non_dict_tool_skipped(self):
        out = _translate_tools_to_gemini([
            "not a dict",
            {"function": {"name": "fn"}},
        ])
        assert len(out) == 1
        assert out[0]["functionDeclarations"][0]["name"] == "fn"

    def test_non_dict_function_block_skipped(self):
        out = _translate_tools_to_gemini([
            {"function": "string"},
        ])
        assert out == []

    def test_missing_name_skipped(self):
        out = _translate_tools_to_gemini([{"function": {"description": "x"}}])
        assert out == []

    def test_blank_name_skipped(self):
        out = _translate_tools_to_gemini([{"function": {"name": ""}}])
        assert out == []

    def test_blank_description_dropped(self):
        out = _translate_tools_to_gemini([{
            "function": {"name": "fn", "description": ""},
        }])
        # Description not included on the decl.
        assert "description" not in out[0]["functionDeclarations"][0]

    def test_non_dict_parameters_dropped(self):
        out = _translate_tools_to_gemini([{
            "function": {"name": "fn", "parameters": "string"},
        }])
        assert "parameters" not in out[0]["functionDeclarations"][0]
