"""Coverage for _get_custom_provider_config in agent.credential_pool."""
from __future__ import annotations

import pytest

from agent.credential_pool import (
    _get_custom_provider_config,
    CUSTOM_POOL_PREFIX,
)


def _stub_providers(monkeypatch, providers):
    """Patch _iter_custom_providers to return the given (name, entry) pairs."""
    from agent import credential_pool
    monkeypatch.setattr(
        credential_pool,
        "_iter_custom_providers",
        lambda: iter(providers),
    )


class TestGetCustomProviderConfig:
    def test_non_prefixed_returns_none(self):
        # Pool keys not starting with "custom:" → None.
        assert _get_custom_provider_config("openai") is None
        assert _get_custom_provider_config("") is None

    def test_match_found(self, monkeypatch):
        entry = {"base_url": "https://together.ai/v1", "name": "together.ai"}
        _stub_providers(monkeypatch, [("together.ai", entry)])
        out = _get_custom_provider_config("custom:together.ai")
        assert out == entry

    def test_no_match_returns_none(self, monkeypatch):
        _stub_providers(monkeypatch, [
            ("together.ai", {"base_url": "x"}),
            ("groq", {"base_url": "y"}),
        ])
        assert _get_custom_provider_config("custom:unknown") is None

    def test_empty_providers(self, monkeypatch):
        _stub_providers(monkeypatch, [])
        assert _get_custom_provider_config("custom:anything") is None

    def test_prefix_constant(self):
        assert CUSTOM_POOL_PREFIX == "custom:"
