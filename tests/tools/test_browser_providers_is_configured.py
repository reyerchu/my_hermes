"""Coverage for the ``is_configured`` predicate on the cloud-browser
providers.  Same gating concern as the web-search providers: a regression
in the env-var check is silent until you try a real fetch."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from tools.browser_providers.browserbase import BrowserbaseProvider
from tools.browser_providers.firecrawl import FirecrawlProvider


class TestBrowserbaseProvider:
    def test_provider_name(self):
        assert BrowserbaseProvider().provider_name() == "Browserbase"

    def test_unconfigured_when_both_vars_missing(self, monkeypatch):
        monkeypatch.delenv("BROWSERBASE_API_KEY", raising=False)
        monkeypatch.delenv("BROWSERBASE_PROJECT_ID", raising=False)
        assert BrowserbaseProvider().is_configured() is False

    def test_unconfigured_when_only_api_key_set(self, monkeypatch):
        monkeypatch.setenv("BROWSERBASE_API_KEY", "key")
        monkeypatch.delenv("BROWSERBASE_PROJECT_ID", raising=False)
        assert BrowserbaseProvider().is_configured() is False

    def test_unconfigured_when_only_project_id_set(self, monkeypatch):
        monkeypatch.delenv("BROWSERBASE_API_KEY", raising=False)
        monkeypatch.setenv("BROWSERBASE_PROJECT_ID", "pid")
        assert BrowserbaseProvider().is_configured() is False

    def test_configured_when_both_env_vars_set(self, monkeypatch):
        monkeypatch.setenv("BROWSERBASE_API_KEY", "key")
        monkeypatch.setenv("BROWSERBASE_PROJECT_ID", "pid")
        assert BrowserbaseProvider().is_configured() is True


class TestFirecrawlProvider:
    def test_provider_name(self):
        assert FirecrawlProvider().provider_name() == "Firecrawl"

    def test_unconfigured_when_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        assert FirecrawlProvider().is_configured() is False

    def test_configured_when_api_key_set(self, monkeypatch):
        monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-tok")
        assert FirecrawlProvider().is_configured() is True


class TestBrowserUseProvider:
    """Browser Use config gating has two paths: direct API key OR managed
    gateway.  We exercise both branches."""

    def test_provider_name(self):
        from tools.browser_providers.browser_use import BrowserUseProvider
        assert BrowserUseProvider().provider_name() == "Browser Use"

    def test_unconfigured_when_no_credentials_and_no_managed(self, monkeypatch):
        monkeypatch.delenv("BROWSER_USE_API_KEY", raising=False)
        from tools.browser_providers.browser_use import BrowserUseProvider
        with patch(
            "tools.browser_providers.browser_use.resolve_managed_tool_gateway",
            return_value=None,
        ):
            assert BrowserUseProvider().is_configured() is False

    def test_configured_when_direct_api_key_present(self, monkeypatch):
        monkeypatch.setenv("BROWSER_USE_API_KEY", "key")
        from tools.browser_providers.browser_use import BrowserUseProvider
        with patch(
            "tools.browser_providers.browser_use.prefers_gateway",
            return_value=False,
        ), patch(
            "tools.browser_providers.browser_use.resolve_managed_tool_gateway",
            return_value=None,
        ):
            assert BrowserUseProvider().is_configured() is True
