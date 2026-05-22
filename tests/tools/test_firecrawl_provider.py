"""Coverage for FirecrawlProvider browser session helpers."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tools.browser_providers.firecrawl import FirecrawlProvider, _BASE_URL


@pytest.fixture
def provider():
    return FirecrawlProvider()


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for var in ("FIRECRAWL_API_KEY", "FIRECRAWL_API_URL", "FIRECRAWL_BROWSER_TTL"):
        monkeypatch.delenv(var, raising=False)


class TestIdentity:
    def test_name(self, provider):
        assert provider.provider_name() == "Firecrawl"


class TestIsConfigured:
    def test_present(self, provider, monkeypatch):
        monkeypatch.setenv("FIRECRAWL_API_KEY", "k")
        assert provider.is_configured() is True

    def test_missing(self, provider):
        assert provider.is_configured() is False


class TestApiUrl:
    def test_default(self, provider):
        assert provider._api_url() == _BASE_URL

    def test_override(self, provider, monkeypatch):
        monkeypatch.setenv("FIRECRAWL_API_URL", "https://eu.firecrawl.local")
        assert provider._api_url() == "https://eu.firecrawl.local"


class TestHeaders:
    def test_raises_when_no_key(self, provider):
        with pytest.raises(ValueError, match="FIRECRAWL_API_KEY"):
            provider._headers()

    def test_uses_bearer_token(self, provider, monkeypatch):
        monkeypatch.setenv("FIRECRAWL_API_KEY", "secret-key")
        h = provider._headers()
        assert h["Authorization"] == "Bearer secret-key"
        assert h["Content-Type"] == "application/json"


class TestCreateSession:
    def test_happy_path(self, provider, monkeypatch):
        monkeypatch.setenv("FIRECRAWL_API_KEY", "k")
        resp = MagicMock(ok=True)
        resp.json.return_value = {"id": "sess-1", "cdpUrl": "wss://cdp"}
        with patch("tools.browser_providers.firecrawl.requests.post", return_value=resp) as post:
            out = provider.create_session("task-123")
        assert out["bb_session_id"] == "sess-1"
        assert out["cdp_url"] == "wss://cdp"
        assert out["session_name"].startswith("hermes_task-123_")
        # 8-char uuid suffix
        suffix = out["session_name"].rsplit("_", 1)[-1]
        assert len(suffix) == 8

    def test_uses_default_ttl_300(self, provider, monkeypatch):
        monkeypatch.setenv("FIRECRAWL_API_KEY", "k")
        captured = {}
        def _post(url, headers, json, timeout):
            captured.update(json)
            r = MagicMock(ok=True)
            r.json.return_value = {"id": "s", "cdpUrl": "u"}
            return r
        with patch("tools.browser_providers.firecrawl.requests.post", side_effect=_post):
            provider.create_session("t")
        assert captured["ttl"] == 300

    def test_ttl_env_override(self, provider, monkeypatch):
        monkeypatch.setenv("FIRECRAWL_API_KEY", "k")
        monkeypatch.setenv("FIRECRAWL_BROWSER_TTL", "120")
        captured = {}
        def _post(url, headers, json, timeout):
            captured.update(json)
            r = MagicMock(ok=True)
            r.json.return_value = {"id": "s", "cdpUrl": "u"}
            return r
        with patch("tools.browser_providers.firecrawl.requests.post", side_effect=_post):
            provider.create_session("t")
        assert captured["ttl"] == 120

    def test_raises_on_non_ok_response(self, provider, monkeypatch):
        monkeypatch.setenv("FIRECRAWL_API_KEY", "k")
        resp = MagicMock(ok=False, status_code=429, text="rate limited")
        with patch("tools.browser_providers.firecrawl.requests.post", return_value=resp):
            with pytest.raises(RuntimeError, match="429"):
                provider.create_session("t")


class TestCloseSession:
    def test_success_204(self, provider, monkeypatch):
        monkeypatch.setenv("FIRECRAWL_API_KEY", "k")
        resp = MagicMock(status_code=204, text="")
        with patch("tools.browser_providers.firecrawl.requests.delete", return_value=resp):
            assert provider.close_session("sess-1") is True

    def test_success_200(self, provider, monkeypatch):
        monkeypatch.setenv("FIRECRAWL_API_KEY", "k")
        resp = MagicMock(status_code=200, text="")
        with patch("tools.browser_providers.firecrawl.requests.delete", return_value=resp):
            assert provider.close_session("sess-1") is True

    def test_returns_false_on_failure(self, provider, monkeypatch):
        monkeypatch.setenv("FIRECRAWL_API_KEY", "k")
        resp = MagicMock(status_code=500, text="internal error")
        with patch("tools.browser_providers.firecrawl.requests.delete", return_value=resp):
            assert provider.close_session("sess-1") is False

    def test_returns_false_on_exception(self, provider, monkeypatch):
        monkeypatch.setenv("FIRECRAWL_API_KEY", "k")
        with patch(
            "tools.browser_providers.firecrawl.requests.delete",
            side_effect=RuntimeError("boom"),
        ):
            assert provider.close_session("sess-1") is False


class TestEmergencyCleanup:
    def test_handles_missing_credentials(self, provider):
        # _headers() raises ValueError when no key — emergency_cleanup
        # must swallow it.
        provider.emergency_cleanup("sess")  # must not raise

    def test_swallows_request_exception(self, provider, monkeypatch):
        monkeypatch.setenv("FIRECRAWL_API_KEY", "k")
        with patch(
            "tools.browser_providers.firecrawl.requests.delete",
            side_effect=RuntimeError("net"),
        ):
            provider.emergency_cleanup("sess")  # must not raise

    def test_normal_path(self, provider, monkeypatch):
        monkeypatch.setenv("FIRECRAWL_API_KEY", "k")
        with patch("tools.browser_providers.firecrawl.requests.delete") as d:
            provider.emergency_cleanup("sess-x")
        d.assert_called_once()
        # Must hit DELETE /v2/browser/<id>
        args, kwargs = d.call_args
        assert args[0].endswith("/v2/browser/sess-x")
