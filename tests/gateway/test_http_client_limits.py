"""Coverage for gateway.platforms._http_client_limits."""
from __future__ import annotations

import os

import pytest

from gateway.platforms._http_client_limits import (
    platform_httpx_limits,
    _DEFAULT_KEEPALIVE_EXPIRY_S,
    _DEFAULT_MAX_KEEPALIVE,
)


# Env vars under test
KE_VAR = "HERMES_GATEWAY_HTTPX_KEEPALIVE_EXPIRY"
MX_VAR = "HERMES_GATEWAY_HTTPX_MAX_KEEPALIVE"


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv(KE_VAR, raising=False)
    monkeypatch.delenv(MX_VAR, raising=False)
    yield


class TestPlatformHttpxLimits:
    def test_defaults(self):
        out = platform_httpx_limits()
        assert out is not None
        assert out.max_keepalive_connections == _DEFAULT_MAX_KEEPALIVE
        assert out.keepalive_expiry == _DEFAULT_KEEPALIVE_EXPIRY_S

    def test_max_connections_left_at_httpx_default(self):
        out = platform_httpx_limits()
        # We explicitly do NOT set max_connections — it stays at httpx's
        # built-in default of 100 (or None on very old httpx versions).
        # Whichever it is, our helper shouldn't override it.
        import httpx as _httpx
        default_limits = _httpx.Limits()
        assert out.max_connections == default_limits.max_connections

    def test_env_override_keepalive_expiry(self, monkeypatch):
        monkeypatch.setenv(KE_VAR, "7.5")
        out = platform_httpx_limits()
        assert out.keepalive_expiry == 7.5

    def test_env_override_max_keepalive(self, monkeypatch):
        monkeypatch.setenv(MX_VAR, "42")
        out = platform_httpx_limits()
        assert out.max_keepalive_connections == 42

    def test_env_garbage_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv(KE_VAR, "not-a-number")
        monkeypatch.setenv(MX_VAR, "also-garbage")
        out = platform_httpx_limits()
        assert out.keepalive_expiry == _DEFAULT_KEEPALIVE_EXPIRY_S
        assert out.max_keepalive_connections == _DEFAULT_MAX_KEEPALIVE

    def test_env_zero_falls_back_to_default(self, monkeypatch):
        # Zero or negative is treated as invalid and replaced with default.
        monkeypatch.setenv(KE_VAR, "0")
        monkeypatch.setenv(MX_VAR, "0")
        out = platform_httpx_limits()
        assert out.keepalive_expiry == _DEFAULT_KEEPALIVE_EXPIRY_S
        assert out.max_keepalive_connections == _DEFAULT_MAX_KEEPALIVE

    def test_env_negative_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv(KE_VAR, "-1.0")
        monkeypatch.setenv(MX_VAR, "-5")
        out = platform_httpx_limits()
        assert out.keepalive_expiry == _DEFAULT_KEEPALIVE_EXPIRY_S
        assert out.max_keepalive_connections == _DEFAULT_MAX_KEEPALIVE

    def test_env_padded_whitespace_treated_as_unset(self, monkeypatch):
        monkeypatch.setenv(KE_VAR, "   ")
        out = platform_httpx_limits()
        assert out.keepalive_expiry == _DEFAULT_KEEPALIVE_EXPIRY_S

    def test_env_float_for_int_var_falls_back(self, monkeypatch):
        # int("3.14") raises → default
        monkeypatch.setenv(MX_VAR, "3.14")
        out = platform_httpx_limits()
        assert out.max_keepalive_connections == _DEFAULT_MAX_KEEPALIVE


class TestPlatformHttpxLimitsNoHttpx:
    def test_returns_none_when_httpx_missing(self, monkeypatch):
        # Simulate httpx being unimportable by setting module-level to None.
        import gateway.platforms._http_client_limits as mod
        monkeypatch.setattr(mod, "httpx", None)
        assert mod.platform_httpx_limits() is None
