"""Coverage for SearXNGSearchProvider."""
from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from tools.web_providers.searxng import SearXNGSearchProvider


@pytest.fixture
def provider():
    return SearXNGSearchProvider()


class TestIdentity:
    def test_provider_name(self, provider):
        assert provider.provider_name() == "searxng"


class TestIsConfigured:
    def test_set(self, provider, monkeypatch):
        monkeypatch.setenv("SEARXNG_URL", "http://x")
        assert provider.is_configured() is True

    def test_missing(self, provider, monkeypatch):
        monkeypatch.delenv("SEARXNG_URL", raising=False)
        assert provider.is_configured() is False

    def test_blank(self, provider, monkeypatch):
        monkeypatch.setenv("SEARXNG_URL", "  ")
        assert provider.is_configured() is False


class TestSearch:
    def test_missing_url(self, provider, monkeypatch):
        monkeypatch.delenv("SEARXNG_URL", raising=False)
        out = provider.search("q")
        assert out["success"] is False
        assert "not set" in out["error"]

    def _stub(self, monkeypatch, body=None, raise_=None):
        mock_resp = MagicMock()
        mock_resp.json.return_value = body or {}
        if raise_ is None:
            mock_resp.raise_for_status.return_value = None
        else:
            mock_resp.raise_for_status.side_effect = raise_
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: mock_resp)
        return mock_resp

    def test_happy_path_sorted_by_score(self, provider, monkeypatch):
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080/")  # trailing slash stripped
        self._stub(
            monkeypatch,
            body={
                "results": [
                    {"title": "low", "url": "u1", "content": "c1", "score": 0.1},
                    {"title": "high", "url": "u2", "content": "c2", "score": 0.9},
                    {"title": "mid", "url": "u3", "content": "c3", "score": 0.5},
                ]
            },
        )
        out = provider.search("q", limit=5)
        assert out["success"] is True
        web = out["data"]["web"]
        # Descending score → ["high", "mid", "low"]
        assert [r["title"] for r in web] == ["high", "mid", "low"]
        # Positions 1-indexed.
        assert [r["position"] for r in web] == [1, 2, 3]
        # "content" → "description"
        assert web[0]["description"] == "c2"

    def test_limit_truncates(self, provider, monkeypatch):
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")
        self._stub(
            monkeypatch,
            body={
                "results": [
                    {"title": f"T{i}", "url": f"u{i}", "content": "", "score": i}
                    for i in range(10)
                ]
            },
        )
        out = provider.search("q", limit=3)
        assert len(out["data"]["web"]) == 3

    def test_missing_score_treated_as_zero(self, provider, monkeypatch):
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")
        self._stub(
            monkeypatch,
            body={
                "results": [
                    {"title": "a", "url": "u1", "content": ""},  # no score
                    {"title": "b", "url": "u2", "content": "", "score": 0.5},
                ]
            },
        )
        out = provider.search("q", limit=5)
        # "b" (score 0.5) should come before "a" (score implicit 0).
        assert out["data"]["web"][0]["title"] == "b"

    def test_http_status_error(self, provider, monkeypatch):
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")
        bad = MagicMock(status_code=503)
        err = httpx.HTTPStatusError("503", request=MagicMock(), response=bad)
        self._stub(monkeypatch, raise_=err)
        out = provider.search("q")
        assert out["success"] is False
        assert "503" in out["error"]

    def test_request_error(self, provider, monkeypatch):
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")
        def _raise(*a, **kw):
            raise httpx.ConnectError("no route")
        monkeypatch.setattr(httpx, "get", _raise)
        out = provider.search("q")
        assert out["success"] is False
        assert "Could not reach" in out["error"]
        assert "localhost:8080" in out["error"]

    def test_json_parse_error(self, provider, monkeypatch):
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = ValueError("bad")
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: mock_resp)
        out = provider.search("q")
        assert out["success"] is False
        assert "JSON" in out["error"]

    def test_no_results_key(self, provider, monkeypatch):
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")
        self._stub(monkeypatch, body={})
        out = provider.search("q")
        assert out["success"] is True
        assert out["data"]["web"] == []
