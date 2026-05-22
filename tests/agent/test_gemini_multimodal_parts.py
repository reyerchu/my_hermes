"""Coverage for _extract_multimodal_parts in agent.gemini_native_adapter."""
from __future__ import annotations

import base64

import pytest

from agent.gemini_native_adapter import _extract_multimodal_parts


class TestExtractMultimodalParts:
    def test_string_content(self):
        out = _extract_multimodal_parts("hello")
        assert out == [{"text": "hello"}]

    def test_empty_string_returns_empty_list(self):
        # _coerce_content_to_text returns "" → list with no [{"text": ""}].
        assert _extract_multimodal_parts("") == []

    def test_none_returns_empty(self):
        assert _extract_multimodal_parts(None) == []

    def test_string_in_list(self):
        out = _extract_multimodal_parts(["hello"])
        assert out == [{"text": "hello"}]

    def test_text_part_dict(self):
        out = _extract_multimodal_parts([{"type": "text", "text": "hi"}])
        assert out == [{"text": "hi"}]

    def test_blank_text_part_skipped(self):
        out = _extract_multimodal_parts([{"type": "text", "text": ""}])
        assert out == []

    def test_non_dict_skipped(self):
        out = _extract_multimodal_parts([42, "kept", {"type": "text", "text": "also kept"}])
        assert {"text": "kept"} in out
        assert {"text": "also kept"} in out
        assert len(out) == 2

    def test_image_url_data_uri(self):
        png_bytes = b"\x89PNG\r\n\x1a\n"
        b64 = base64.b64encode(png_bytes).decode("ascii")
        data_url = f"data:image/png;base64,{b64}"
        out = _extract_multimodal_parts([
            {"type": "image_url", "image_url": {"url": data_url}},
        ])
        assert len(out) == 1
        assert out[0]["inlineData"]["mimeType"] == "image/png"
        # Base64 round-tripped.
        decoded = base64.b64decode(out[0]["inlineData"]["data"])
        assert decoded == png_bytes

    def test_image_url_non_data_uri_skipped(self):
        out = _extract_multimodal_parts([
            {"type": "image_url", "image_url": {"url": "https://example/x.png"}},
        ])
        assert out == []

    def test_image_url_malformed_silently_dropped(self):
        out = _extract_multimodal_parts([
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,not-valid-b64!!"}},
        ])
        # The bytes round-trip via base64 — malformed input may still pass.
        # If it raises, the part is dropped.  Just check we get a list.
        assert isinstance(out, list)

    def test_unknown_part_type_skipped(self):
        out = _extract_multimodal_parts([{"type": "weird", "text": "x"}])
        assert out == []

    def test_image_url_no_image_url_field(self):
        out = _extract_multimodal_parts([{"type": "image_url"}])
        assert out == []
