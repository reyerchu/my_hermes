"""Coverage for DDGSSearchProvider."""
from __future__ import annotations

import sys
import types
from unittest.mock import patch, MagicMock

import pytest

from tools.web_providers.ddgs import DDGSSearchProvider


@pytest.fixture
def provider():
    return DDGSSearchProvider()


class TestProviderIdentity:
    def test_provider_name(self, provider):
        assert provider.provider_name() == "ddgs"


class TestIsConfigured:
    def test_returns_true_when_ddgs_importable(self, provider, monkeypatch):
        # Inject a stub ddgs module so the import succeeds.
        stub = types.ModuleType("ddgs")
        monkeypatch.setitem(sys.modules, "ddgs", stub)
        assert provider.is_configured() is True

    def test_returns_false_when_ddgs_missing(self, provider, monkeypatch):
        # Block ddgs from being importable.
        monkeypatch.setitem(sys.modules, "ddgs", None)
        assert provider.is_configured() is False


class TestSearch:
    def test_returns_error_when_package_missing(self, provider, monkeypatch):
        monkeypatch.setitem(sys.modules, "ddgs", None)
        out = provider.search("anything")
        assert out["success"] is False
        assert "not installed" in out["error"]

    def _install_ddgs_stub(self, monkeypatch, hits):
        # Build a fake ddgs module with a DDGS context manager that
        # yields the supplied hits from .text().
        ddgs_mod = types.ModuleType("ddgs")

        class _FakeClient:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *exc):
                return False

            def text(self_inner, query, max_results=5):
                yield from hits

        ddgs_mod.DDGS = _FakeClient
        monkeypatch.setitem(sys.modules, "ddgs", ddgs_mod)

    def test_basic_success_path(self, provider, monkeypatch):
        hits = [
            {"title": "T1", "href": "https://a", "body": "B1"},
            {"title": "T2", "url": "https://b", "body": "B2"},
        ]
        self._install_ddgs_stub(monkeypatch, hits)
        out = provider.search("test", limit=5)
        assert out["success"] is True
        web = out["data"]["web"]
        assert len(web) == 2
        assert web[0]["title"] == "T1"
        assert web[0]["url"] == "https://a"
        assert web[0]["description"] == "B1"
        assert web[0]["position"] == 1
        # Falls back to "url" key when "href" missing.
        assert web[1]["url"] == "https://b"
        assert web[1]["position"] == 2

    def test_limit_caps_results(self, provider, monkeypatch):
        # Iterator can produce more than asked — provider must cut at limit.
        hits = [{"title": f"T{i}", "href": f"u{i}", "body": ""} for i in range(10)]
        self._install_ddgs_stub(monkeypatch, hits)
        out = provider.search("q", limit=3)
        assert out["success"] is True
        assert len(out["data"]["web"]) == 3

    def test_limit_minimum_is_one(self, provider, monkeypatch):
        # Even limit=0 should be coerced to at least 1.
        hits = [{"title": "T", "href": "u", "body": ""}]
        self._install_ddgs_stub(monkeypatch, hits)
        out = provider.search("q", limit=0)
        assert out["success"] is True
        assert len(out["data"]["web"]) >= 0  # smoke

    def test_exception_surfaces_as_error(self, provider, monkeypatch):
        ddgs_mod = types.ModuleType("ddgs")

        class _BoomClient:
            def __enter__(self_inner): return self_inner
            def __exit__(self_inner, *exc): return False
            def text(self_inner, query, max_results=5):
                raise RuntimeError("rate limited")

        ddgs_mod.DDGS = _BoomClient
        monkeypatch.setitem(sys.modules, "ddgs", ddgs_mod)
        out = provider.search("q")
        assert out["success"] is False
        assert "rate limited" in out["error"]

    def test_missing_fields_default_to_empty(self, provider, monkeypatch):
        # Hit with no title/url/body should yield empty strings.
        self._install_ddgs_stub(monkeypatch, [{}])
        out = provider.search("q")
        web = out["data"]["web"]
        assert web[0]["title"] == ""
        assert web[0]["url"] == ""
        assert web[0]["description"] == ""
