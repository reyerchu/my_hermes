"""Coverage for the pure helpers in ``tools.image_generation_tool``."""
from __future__ import annotations

import pytest

from tools.image_generation_tool import (
    _extract_http_status,
    _normalize_fal_queue_url_format,
)


class TestNormalizeFalQueueUrlFormat:
    def test_strips_trailing_slash_and_adds_back(self):
        out = _normalize_fal_queue_url_format("https://example.com/x/")
        assert out == "https://example.com/x/"

    def test_no_trailing_slash_input_gets_one(self):
        out = _normalize_fal_queue_url_format("https://example.com")
        assert out == "https://example.com/"

    def test_strips_surrounding_whitespace(self):
        out = _normalize_fal_queue_url_format("  https://example.com  ")
        assert out == "https://example.com/"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="required"):
            _normalize_fal_queue_url_format("")

    def test_none_raises(self):
        with pytest.raises(ValueError):
            _normalize_fal_queue_url_format(None)  # type: ignore[arg-type]

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            _normalize_fal_queue_url_format("   ")


class TestExtractHttpStatus:
    def test_none_when_no_status_attached(self):
        class _Plain(Exception):
            pass
        assert _extract_http_status(_Plain()) is None

    def test_status_from_response_attribute(self):
        class _Resp:
            status_code = 429
        class _Exc(Exception):
            response = _Resp()
        assert _extract_http_status(_Exc()) == 429

    def test_status_directly_on_exception(self):
        class _Exc(Exception):
            status_code = 500
        assert _extract_http_status(_Exc()) == 500

    def test_response_status_takes_priority(self):
        # When both .response.status_code and .status_code are present,
        # the response-level value wins.
        class _Resp:
            status_code = 429
        class _Exc(Exception):
            response = _Resp()
            status_code = 500
        assert _extract_http_status(_Exc()) == 429

    def test_non_int_status_falls_through(self):
        class _Exc(Exception):
            status_code = "not a number"
        assert _extract_http_status(_Exc()) is None

    def test_response_with_no_status_code_attribute(self):
        class _Resp:
            pass
        class _Exc(Exception):
            response = _Resp()
        assert _extract_http_status(_Exc()) is None
