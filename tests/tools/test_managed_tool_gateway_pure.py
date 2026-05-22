"""Coverage for the pure helpers in ``tools.managed_tool_gateway``:
timestamp parsing, token-expiry math, and gateway-URL builders."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tools.managed_tool_gateway import (
    _access_token_is_expiring,
    _parse_timestamp,
    build_vendor_gateway_url,
    get_tool_gateway_scheme,
)


class TestParseTimestamp:
    def test_iso_with_offset(self):
        out = _parse_timestamp("2025-01-01T12:00:00+00:00")
        assert out is not None
        assert out.tzinfo is not None

    def test_iso_with_zulu_suffix_normalised(self):
        # The helper rewrites the trailing Z to +00:00 before fromisoformat.
        out = _parse_timestamp("2025-01-01T12:00:00Z")
        assert out is not None
        assert out.tzinfo is not None

    def test_empty_or_blank_returns_none(self):
        assert _parse_timestamp("") is None
        assert _parse_timestamp("   ") is None

    def test_non_string_returns_none(self):
        assert _parse_timestamp(None) is None
        assert _parse_timestamp(12345) is None

    def test_garbage_returns_none(self):
        assert _parse_timestamp("not a date") is None


class TestAccessTokenIsExpiring:
    def test_none_value_treated_as_expired(self):
        assert _access_token_is_expiring(None, skew_seconds=60) is True

    def test_past_timestamp_is_expiring(self):
        ts = (
            datetime.now(timezone.utc) - timedelta(minutes=5)
        ).isoformat()
        assert _access_token_is_expiring(ts, skew_seconds=60) is True

    def test_far_future_is_not_expiring(self):
        ts = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat()
        assert _access_token_is_expiring(ts, skew_seconds=60) is False

    def test_within_skew_window_is_expiring(self):
        ts = (
            datetime.now(timezone.utc) + timedelta(seconds=30)
        ).isoformat()
        assert _access_token_is_expiring(ts, skew_seconds=120) is True

    def test_negative_skew_treated_as_zero(self):
        ts = (
            datetime.now(timezone.utc) + timedelta(seconds=10)
        ).isoformat()
        # skew < 0 floors to 0 → token must already be expired
        assert _access_token_is_expiring(ts, skew_seconds=-5) is False


class TestGetToolGatewayScheme:
    def test_default_is_https(self, monkeypatch):
        monkeypatch.delenv("TOOL_GATEWAY_SCHEME", raising=False)
        assert get_tool_gateway_scheme() == "https"

    def test_lowercase_https_passes(self, monkeypatch):
        monkeypatch.setenv("TOOL_GATEWAY_SCHEME", "https")
        assert get_tool_gateway_scheme() == "https"

    def test_lowercase_http_passes(self, monkeypatch):
        monkeypatch.setenv("TOOL_GATEWAY_SCHEME", "http")
        assert get_tool_gateway_scheme() == "http"

    def test_unknown_scheme_raises_value_error(self, monkeypatch):
        # The helper validates: anything that isn't http/https raises.
        monkeypatch.setenv("TOOL_GATEWAY_SCHEME", "gopher")
        with pytest.raises(ValueError, match="http"):
            get_tool_gateway_scheme()


class TestBuildVendorGatewayUrl:
    def test_default_origin_uses_nousresearch_domain(self, monkeypatch):
        for name in ("TOOL_GATEWAY_SCHEME", "TOOL_GATEWAY_DOMAIN",
                     "VERCEL_GATEWAY_URL"):
            monkeypatch.delenv(name, raising=False)
        url = build_vendor_gateway_url("vercel")
        assert url == "https://vercel-gateway.nousresearch.com"

    def test_explicit_vendor_url_wins(self, monkeypatch):
        monkeypatch.setenv("VERCEL_GATEWAY_URL", "https://override.example/")
        assert (
            build_vendor_gateway_url("vercel")
            == "https://override.example"
        )

    def test_shared_domain_with_default_scheme(self, monkeypatch):
        monkeypatch.delenv("VERCEL_GATEWAY_URL", raising=False)
        monkeypatch.delenv("TOOL_GATEWAY_SCHEME", raising=False)
        monkeypatch.setenv("TOOL_GATEWAY_DOMAIN", "internal.lan")
        assert (
            build_vendor_gateway_url("vercel")
            == "https://vercel-gateway.internal.lan"
        )

    def test_dashes_in_vendor_become_underscores_in_env_lookup(
        self, monkeypatch,
    ):
        monkeypatch.setenv("BROWSER_USE_GATEWAY_URL", "https://x.example")
        assert (
            build_vendor_gateway_url("browser-use")
            == "https://x.example"
        )
