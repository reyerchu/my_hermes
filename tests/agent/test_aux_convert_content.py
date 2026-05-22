"""Coverage for _convert_content_for_responses in agent.auxiliary_client."""
from __future__ import annotations

import pytest

from agent.auxiliary_client import _convert_content_for_responses


class TestConvertContentForResponses:
    def test_string_passthrough(self):
        assert _convert_content_for_responses("hello") == "hello"

    def test_none(self):
        assert _convert_content_for_responses(None) == ""

    def test_non_list_non_string_coerced(self):
        assert _convert_content_for_responses(42) == "42"

    def test_text_part_converted(self):
        out = _convert_content_for_responses([{"type": "text", "text": "hi"}])
        assert out == [{"type": "input_text", "text": "hi"}]

    def test_image_url_converted(self):
        out = _convert_content_for_responses([
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,XYZ"}},
        ])
        assert out == [{
            "type": "input_image",
            "image_url": "data:image/png;base64,XYZ",
        }]

    def test_image_url_with_detail(self):
        out = _convert_content_for_responses([
            {"type": "image_url", "image_url": {"url": "u", "detail": "high"}},
        ])
        assert out[0]["detail"] == "high"

    def test_image_url_as_string(self):
        out = _convert_content_for_responses([
            {"type": "image_url", "image_url": "https://example/img"},
        ])
        # When image_url isn't a dict, str() is applied.
        assert out[0]["image_url"] == "https://example/img"

    def test_already_responses_format_passthrough(self):
        item = {"type": "input_text", "text": "hi"}
        out = _convert_content_for_responses([item])
        assert out == [item]

    def test_unknown_type_with_text_preserved(self):
        out = _convert_content_for_responses([
            {"type": "weird", "text": "fallback"},
        ])
        assert out == [{"type": "input_text", "text": "fallback"}]

    def test_unknown_type_without_text_dropped(self):
        out = _convert_content_for_responses([
            {"type": "weird"},
        ])
        # No text → nothing emitted → empty list → "".
        assert out == ""

    def test_non_dict_part_skipped(self):
        out = _convert_content_for_responses([
            "string-part",
            {"type": "text", "text": "kept"},
        ])
        assert out == [{"type": "input_text", "text": "kept"}]

    def test_empty_list_returns_empty_string(self):
        # Converted list is empty → fallback to "".
        assert _convert_content_for_responses([]) == ""
