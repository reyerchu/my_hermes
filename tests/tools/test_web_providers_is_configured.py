"""Coverage for the ``is_configured`` / ``provider_name`` contract on the
free-tier web search providers.

These predicates gate the provider router — every dispatch decision asks
"is this provider configured?" so a regression where a missing env var
falsely returns True silently picks a provider that will then crash on
the first network call."""
from __future__ import annotations

import importlib.util

import pytest

from tools.web_providers.brave_free import BraveFreeSearchProvider
from tools.web_providers.searxng import SearXNGSearchProvider


class TestBraveFreeSearchProvider:
    def test_provider_name(self):
        assert BraveFreeSearchProvider().provider_name() == "brave-free"

    def test_unconfigured_when_env_var_missing(self, monkeypatch):
        monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
        assert BraveFreeSearchProvider().is_configured() is False

    def test_unconfigured_when_env_var_blank(self, monkeypatch):
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "")
        assert BraveFreeSearchProvider().is_configured() is False

    def test_unconfigured_when_env_var_whitespace(self, monkeypatch):
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "   ")
        assert BraveFreeSearchProvider().is_configured() is False

    def test_configured_when_env_var_set(self, monkeypatch):
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "tok-xyz")
        assert BraveFreeSearchProvider().is_configured() is True


class TestSearXNGSearchProvider:
    def test_provider_name(self):
        assert SearXNGSearchProvider().provider_name() == "searxng"

    def test_unconfigured_when_url_missing(self, monkeypatch):
        monkeypatch.delenv("SEARXNG_URL", raising=False)
        assert SearXNGSearchProvider().is_configured() is False

    def test_unconfigured_when_url_blank(self, monkeypatch):
        monkeypatch.setenv("SEARXNG_URL", "")
        assert SearXNGSearchProvider().is_configured() is False

    def test_configured_when_url_set(self, monkeypatch):
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")
        assert SearXNGSearchProvider().is_configured() is True


class TestDDGSSearchProvider:
    def test_provider_name(self):
        from tools.web_providers.ddgs import DDGSSearchProvider
        assert DDGSSearchProvider().provider_name() == "ddgs"

    def test_is_configured_depends_on_package_availability(self):
        from tools.web_providers.ddgs import DDGSSearchProvider
        # The predicate must reflect whether `ddgs` is importable.
        expected = importlib.util.find_spec("ddgs") is not None
        assert DDGSSearchProvider().is_configured() == expected
