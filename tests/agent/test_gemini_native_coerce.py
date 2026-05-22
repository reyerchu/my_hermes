"""Coverage for ``_coerce_content_to_text`` in
``agent.gemini_native_adapter``."""
from __future__ import annotations

import pytest

from agent.gemini_native_adapter import _coerce_content_to_text


class TestCoerceContentToText:
    def test_none_returns_empty(self):
        assert _coerce_content_to_text(None) == ""

    def test_str_passes_through(self):
        assert _coerce_content_to_text("hi") == "hi"

    def test_list_of_strings_joined_with_newlines(self):
        out = _coerce_content_to_text(["a", "b"])
        assert out == "a\nb"

    def test_text_parts_extracted(self):
        out = _coerce_content_to_text([
            {"type": "text", "text": "alpha"},
            {"type": "text", "text": "beta"},
        ])
        assert out == "alpha\nbeta"

    def test_non_text_parts_skipped(self):
        out = _coerce_content_to_text([
            {"type": "text", "text": "keep"},
            {"type": "image_url", "image_url": {"url": "x"}},
        ])
        # The image part is silently dropped.
        assert out == "keep"

    def test_mixed_strings_and_dict_parts(self):
        out = _coerce_content_to_text([
            "raw-string",
            {"type": "text", "text": "in-dict"},
        ])
        assert out == "raw-string\nin-dict"

    def test_non_string_type_part_skipped(self):
        # type field present but not "text" → skipped.
        out = _coerce_content_to_text([
            {"type": "image", "text": "ignored"},
        ])
        assert out == ""

    def test_dict_text_field_not_a_string_skipped(self):
        out = _coerce_content_to_text([
            {"type": "text", "text": 42},
        ])
        assert out == ""

    def test_unsupported_scalar_falls_back_to_str_repr(self):
        # Anything that isn't None / str / list goes through str().
        out = _coerce_content_to_text(42)
        assert out == "42"
