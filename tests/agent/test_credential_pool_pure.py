"""Coverage for the pure helpers in ``agent.credential_pool``."""
from __future__ import annotations

import pytest

from agent.credential_pool import (
    EXHAUSTED_TTL_401_SECONDS,
    EXHAUSTED_TTL_429_SECONDS,
    EXHAUSTED_TTL_DEFAULT_SECONDS,
    SOURCE_MANUAL,
    _exhausted_ttl,
    _is_manual_source,
    _normalize_custom_pool_name,
    label_from_token,
)


class TestIsManualSource:
    def test_exact_manual_string(self):
        assert _is_manual_source("manual") is True

    def test_manual_prefix_with_suffix(self):
        assert _is_manual_source("manual:my-key") is True

    def test_case_insensitive(self):
        assert _is_manual_source("MANUAL") is True
        assert _is_manual_source(" Manual: foo") is True

    def test_non_manual_source(self):
        for src in ("env:OPENAI_API_KEY", "claude_code", "qwen-cli"):
            assert _is_manual_source(src) is False

    def test_empty_string(self):
        assert _is_manual_source("") is False


class TestExhaustedTtl:
    def test_401_uses_401_ttl(self):
        assert _exhausted_ttl(401) == EXHAUSTED_TTL_401_SECONDS

    def test_429_uses_429_ttl(self):
        assert _exhausted_ttl(429) == EXHAUSTED_TTL_429_SECONDS

    def test_other_status_uses_default(self):
        assert _exhausted_ttl(500) == EXHAUSTED_TTL_DEFAULT_SECONDS
        assert _exhausted_ttl(0) == EXHAUSTED_TTL_DEFAULT_SECONDS

    def test_none_uses_default(self):
        assert _exhausted_ttl(None) == EXHAUSTED_TTL_DEFAULT_SECONDS

    def test_constants_are_positive_ints(self):
        for k in (EXHAUSTED_TTL_401_SECONDS, EXHAUSTED_TTL_429_SECONDS,
                  EXHAUSTED_TTL_DEFAULT_SECONDS):
            assert isinstance(k, int) and k > 0


class TestNormalizeCustomPoolName:
    def test_lowercases_input(self):
        assert _normalize_custom_pool_name("My-Provider") == "my-provider"

    def test_replaces_spaces_with_hyphens(self):
        assert _normalize_custom_pool_name("My Cool Provider") == "my-cool-provider"

    def test_strips_surrounding_whitespace(self):
        assert _normalize_custom_pool_name("  foo  ") == "foo"

    def test_empty_yields_empty(self):
        assert _normalize_custom_pool_name("") == ""


class TestLabelFromToken:
    def test_fallback_when_token_not_a_jwt(self):
        # Random opaque string isn't a JWT — helper returns the fallback.
        assert label_from_token("opaque", "fallback") == "fallback"

    def test_fallback_when_token_empty(self):
        assert label_from_token("", "fb") == "fb"

    def test_returns_email_from_jwt_payload(self):
        # Build a minimal unsigned JWT with email claim.  Header.Payload.
        import base64
        import json

        def b64(obj):
            data = json.dumps(obj).encode("utf-8")
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

        header = b64({"alg": "none"})
        payload = b64({"email": "user@example.com"})
        # _decode_jwt_claims expects three parts even if the signature is empty.
        token = f"{header}.{payload}."
        assert label_from_token(token, "fb") == "user@example.com"
