"""Coverage for the pure translation helpers in
``agent.gemini_cloudcode_adapter``."""
from __future__ import annotations

import pytest

from agent.gemini_cloudcode_adapter import (
    _coerce_content_to_text,
    _normalize_thinking_config,
    _translate_tool_choice_to_gemini,
)


class TestCoerceContentToText:
    def test_none_returns_empty_string(self):
        assert _coerce_content_to_text(None) == ""

    def test_str_passes_through(self):
        assert _coerce_content_to_text("hello") == "hello"

    def test_list_of_strings(self):
        out = _coerce_content_to_text(["a", "b"])
        assert "a" in out and "b" in out

    def test_list_of_text_parts(self):
        out = _coerce_content_to_text([
            {"type": "text", "text": "alpha"},
            {"type": "text", "text": "beta"},
        ])
        assert "alpha" in out and "beta" in out

    def test_image_parts_skipped(self):
        out = _coerce_content_to_text([
            {"type": "text", "text": "alpha"},
            {"type": "image_url", "image_url": {"url": "x"}},
        ])
        assert "alpha" in out
        # Image URL is not text — should not surface.
        assert "x" not in out


class TestTranslateToolChoiceToGemini:
    def test_none_returns_none(self):
        assert _translate_tool_choice_to_gemini(None) is None

    def test_auto_maps_to_auto_mode(self):
        out = _translate_tool_choice_to_gemini("auto")
        assert out == {"functionCallingConfig": {"mode": "AUTO"}}

    def test_required_maps_to_any(self):
        out = _translate_tool_choice_to_gemini("required")
        assert out == {"functionCallingConfig": {"mode": "ANY"}}

    def test_none_string_maps_to_none(self):
        out = _translate_tool_choice_to_gemini("none")
        assert out == {"functionCallingConfig": {"mode": "NONE"}}

    def test_named_function_choice(self):
        out = _translate_tool_choice_to_gemini({
            "type": "function",
            "function": {"name": "lookup"},
        })
        assert out is not None
        # The output should pin Gemini's allowed_function_names to the chosen name.
        cfg = out.get("functionCallingConfig", {})
        names = cfg.get("allowedFunctionNames") or []
        assert "lookup" in names

    def test_unknown_string_value(self):
        # Unknown choice values are either passed through or rejected — both
        # behaviours are acceptable as long as they don't crash.
        out = _translate_tool_choice_to_gemini("totally-unknown")
        # Either None or a dict — function must return cleanly.
        assert out is None or isinstance(out, dict)


class TestNormalizeThinkingConfig:
    def test_non_dict_returns_none(self):
        assert _normalize_thinking_config(None) is None
        assert _normalize_thinking_config("not a dict") is None

    def test_empty_dict_returns_none(self):
        assert _normalize_thinking_config({}) is None

    def test_camelCase_keys_normalised(self):
        out = _normalize_thinking_config({
            "thinkingBudget": 2048,
            "thinkingLevel": "HIGH",
            "includeThoughts": True,
        })
        assert out["thinkingBudget"] == 2048
        assert out["thinkingLevel"] == "high"
        assert out["includeThoughts"] is True

    def test_snake_case_keys_also_accepted(self):
        out = _normalize_thinking_config({
            "thinking_budget": 1024,
            "thinking_level": "low",
            "include_thoughts": False,
        })
        assert out["thinkingBudget"] == 1024
        assert out["thinkingLevel"] == "low"
        assert out["includeThoughts"] is False

    def test_float_budget_coerced_to_int(self):
        out = _normalize_thinking_config({"thinkingBudget": 1024.7})
        assert out["thinkingBudget"] == 1024
        assert isinstance(out["thinkingBudget"], int)

    def test_invalid_typed_fields_dropped(self):
        out = _normalize_thinking_config({
            "thinkingBudget": "not a number",
            "thinkingLevel": 42,
            "includeThoughts": "yes",
        })
        # All three values are wrong-typed and should be filtered out, but
        # the helper may still return an empty dict or None.
        assert out is None or out == {}
