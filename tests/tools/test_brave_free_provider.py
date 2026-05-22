"""Coverage for BraveFreeSearchProvider."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import httpx
import pytest

from tools.web_providers.brave_free import BraveFreeSearchProvider


@pytest.fixture
def provider():
    return BraveFreeSearchProvider()


class TestIdentity:
    def test_provider_name(self, provider):
        assert provider.provider_name() == "brave-free"


class TestIsConfigured:
    def test_set(self, provider, monkeypatch):
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "k")
        assert provider.is_configured() is True

    def test_missing(self, provider, monkeypatch):
        monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
        assert provider.is_configured() is False

    def test_blank(self, provider, monkeypatch):
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "   ")
        assert provider.is_configured() is False


class TestSearch:
    def test_missing_key_error(self, provider, monkeypatch):
        monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
        out = provider.search("anything")
        assert out["success"] is False
        assert "not set" in out["error"]

    def _stub_response(self, monkeypatch, *, status=200, body=None, raise_=None):
        # Patch httpx.get directly.
        mock_resp = MagicMock()
        mock_resp.status_code = status
        mock_resp.json.return_value = body or {}
        if raise_ is None:
            mock_resp.raise_for_status.return_value = None
        else:
            mock_resp.raise_for_status.side_effect = raise_
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: mock_resp)
        return mock_resp

    def test_happy_path(self, provider, monkeypatch):
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "key")
        self._stub_response(
            monkeypatch,
            body={
                "web": {
                    "results": [
                        {"title": "T1", "url": "U1", "description": "D1"},
                        {"title": "T2", "url": "U2", "description": "D2"},
                    ]
                }
            },
        )
        out = provider.search("hi", limit=5)
        assert out["success"] is True
        web = out["data"]["web"]
        assert len(web) == 2
        assert web[0] == {"title": "T1", "url": "U1", "description": "D1", "position": 1}

    def test_limit_truncates_response_post_fetch(self, provider, monkeypatch):
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "key")
        self._stub_response(
            monkeypatch,
            body={
                "web": {
                    "results": [
                        {"title": f"T{i}", "url": f"u{i}", "description": ""}
                        for i in range(10)
                    ]
                }
            },
        )
        out = provider.search("q", limit=3)
        assert len(out["data"]["web"]) == 3

    def test_http_status_error_returns_dict(self, provider, monkeypatch):
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "k")
        bad_resp = MagicMock(status_code=429)
        err = httpx.HTTPStatusError("429", request=MagicMock(), response=bad_resp)
        self._stub_response(monkeypatch, status=429, raise_=err)
        out = provider.search("q")
        assert out["success"] is False
        assert "429" in out["error"]

    def test_request_error_returns_dict(self, provider, monkeypatch):
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "k")
        def _raise(*a, **kw):
            raise httpx.ConnectError("net down")
        monkeypatch.setattr(httpx, "get", _raise)
        out = provider.search("q")
        assert out["success"] is False
        assert "Could not reach" in out["error"]

    def test_json_parse_error(self, provider, monkeypatch):
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "k")
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = ValueError("bad json")
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: mock_resp)
        out = provider.search("q")
        assert out["success"] is False
        assert "JSON" in out["error"] or "parse" in out["error"].lower()

    def test_no_web_results_key(self, provider, monkeypatch):
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "k")
        self._stub_response(monkeypatch, body={})  # no "web"
        out = provider.search("q")
        assert out["success"] is True
        assert out["data"]["web"] == []
