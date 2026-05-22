"""Coverage for the pure helpers in ``agent.gemini_native_adapter``.

The full request-translation path has its own tests; these pin the
small string-level predicates that gate transport selection and
finish-reason translation.
"""
from __future__ import annotations

import pytest

from agent.gemini_native_adapter import (
    _map_gemini_finish_reason,
    is_free_tier_quota_error,
    is_native_gemini_base_url,
)


class TestIsNativeGeminiBaseUrl:
    def test_empty_returns_false(self):
        assert is_native_gemini_base_url("") is False

    def test_native_endpoint_true(self):
        assert is_native_gemini_base_url(
            "https://generativelanguage.googleapis.com"
        ) is True

    def test_native_endpoint_with_version_path(self):
        assert is_native_gemini_base_url(
            "https://generativelanguage.googleapis.com/v1beta"
        ) is True

    def test_openai_compat_endpoint_returns_false(self):
        # The OpenAI-compat shim suffix /openai routes through a
        # different transport.
        assert is_native_gemini_base_url(
            "https://generativelanguage.googleapis.com/v1beta/openai"
        ) is False

    def test_unrelated_host_returns_false(self):
        assert is_native_gemini_base_url("https://example.com/v1") is False

    def test_trailing_slash_handled(self):
        assert is_native_gemini_base_url(
            "https://generativelanguage.googleapis.com/"
        ) is True

    def test_case_insensitive(self):
        assert is_native_gemini_base_url(
            "HTTPS://GENERATIVELANGUAGE.GOOGLEAPIS.COM"
        ) is True


class TestIsFreeTierQuotaError:
    def test_empty_message_returns_false(self):
        assert is_free_tier_quota_error("") is False
        assert is_free_tier_quota_error(None) is False  # type: ignore[arg-type]

    def test_free_tier_in_message_returns_true(self):
        assert (
            is_free_tier_quota_error("quota exceeded for free_tier") is True
        )

    def test_case_insensitive(self):
        assert is_free_tier_quota_error("FREE_TIER quota hit") is True

    def test_regular_rate_limit_message_false(self):
        assert (
            is_free_tier_quota_error("rate limit exceeded for project")
            is False
        )


class TestMapGeminiFinishReason:
    def test_stop_maps_to_stop(self):
        assert _map_gemini_finish_reason("STOP") == "stop"

    def test_max_tokens_maps_to_length(self):
        assert _map_gemini_finish_reason("MAX_TOKENS") == "length"

    def test_safety_maps_to_content_filter(self):
        assert _map_gemini_finish_reason("SAFETY") == "content_filter"

    def test_recitation_maps_to_content_filter(self):
        assert _map_gemini_finish_reason("RECITATION") == "content_filter"

    def test_other_maps_to_stop(self):
        assert _map_gemini_finish_reason("OTHER") == "stop"

    def test_unknown_value_defaults_to_stop(self):
        assert _map_gemini_finish_reason("MYSTERY_REASON") == "stop"

    def test_empty_string_defaults_to_stop(self):
        assert _map_gemini_finish_reason("") == "stop"

    def test_none_defaults_to_stop(self):
        assert _map_gemini_finish_reason(None) == "stop"

    def test_case_insensitive_input(self):
        assert _map_gemini_finish_reason("stop") == "stop"
        assert _map_gemini_finish_reason("Max_Tokens") == "length"
