"""Coverage for ``tools.openrouter_client``."""
from __future__ import annotations

from unittest.mock import patch

import pytest

import tools.openrouter_client as orc


class TestCheckApiKey:
    def test_returns_false_when_unset(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        assert orc.check_api_key() is False

    def test_returns_false_when_blank(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "")
        assert orc.check_api_key() is False

    def test_returns_true_when_set(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
        assert orc.check_api_key() is True


class TestGetAsyncClient:
    def setup_method(self):
        # Reset module-scoped cache between tests.
        orc._client = None

    def teardown_method(self):
        orc._client = None

    def test_caches_client_after_first_resolution(self):
        sentinel = object()
        with patch(
            "agent.auxiliary_client.resolve_provider_client",
            return_value=(sentinel, "model"),
        ) as resolve:
            first = orc.get_async_client()
            second = orc.get_async_client()
        assert first is sentinel
        assert second is sentinel
        # Second call hits the cache; resolver only invoked once.
        assert resolve.call_count == 1

    def test_resolves_with_async_mode_and_openrouter_provider(self):
        with patch(
            "agent.auxiliary_client.resolve_provider_client",
            return_value=(object(), "m"),
        ) as resolve:
            orc.get_async_client()
        resolve.assert_called_once_with("openrouter", async_mode=True)

    def test_raises_when_resolve_returns_none_client(self):
        with patch(
            "agent.auxiliary_client.resolve_provider_client",
            return_value=(None, None),
        ):
            with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
                orc.get_async_client()
