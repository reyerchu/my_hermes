"""Coverage for the ABCs in tools.web_providers.base and
tools.browser_providers.base — verifies the abstract contract."""
from __future__ import annotations

import inspect

import pytest

from tools.web_providers.base import WebSearchProvider, WebExtractProvider
from tools.browser_providers.base import CloudBrowserProvider


class TestWebSearchProvider:
    def test_is_abstract(self):
        with pytest.raises(TypeError):
            WebSearchProvider()  # type: ignore[abstract]

    def test_required_methods(self):
        for name in ("provider_name", "is_configured", "search"):
            attr = getattr(WebSearchProvider, name)
            assert getattr(attr, "__isabstractmethod__", False)

    def test_concrete_subclass_works(self):
        class Mine(WebSearchProvider):
            def provider_name(self): return "mine"
            def is_configured(self): return True
            def search(self, query, limit=5):
                return {"success": True, "data": {"web": []}}
        m = Mine()
        assert m.provider_name() == "mine"
        assert m.is_configured() is True
        assert m.search("q")["success"] is True

    def test_missing_method_blocks_instantiation(self):
        class Partial(WebSearchProvider):
            def provider_name(self): return "x"
            # is_configured + search missing
        with pytest.raises(TypeError):
            Partial()  # type: ignore[abstract]


class TestWebExtractProvider:
    def test_is_abstract(self):
        with pytest.raises(TypeError):
            WebExtractProvider()  # type: ignore[abstract]

    def test_required_methods(self):
        for name in ("provider_name", "is_configured", "extract"):
            attr = getattr(WebExtractProvider, name)
            assert getattr(attr, "__isabstractmethod__", False)

    def test_concrete_subclass(self):
        class Mine(WebExtractProvider):
            def provider_name(self): return "mine"
            def is_configured(self): return False
            def extract(self, urls, **kw): return {"success": True, "data": []}
        m = Mine()
        assert m.extract(["http://x"])["success"] is True


class TestCloudBrowserProvider:
    def test_is_abstract(self):
        with pytest.raises(TypeError):
            CloudBrowserProvider()  # type: ignore[abstract]

    def test_required_methods(self):
        for name in ("provider_name", "is_configured", "create_session",
                     "close_session", "emergency_cleanup"):
            attr = getattr(CloudBrowserProvider, name)
            assert getattr(attr, "__isabstractmethod__", False)

    def test_concrete_subclass(self):
        class Mine(CloudBrowserProvider):
            def provider_name(self): return "mine"
            def is_configured(self): return True
            def create_session(self, task_id):
                return {"session_name": "n", "bb_session_id": "s",
                        "cdp_url": "wss://x", "features": {}}
            def close_session(self, sid): return True
            def emergency_cleanup(self, sid): return None
        m = Mine()
        assert m.create_session("t")["session_name"] == "n"
        assert m.close_session("s") is True
        m.emergency_cleanup("s")  # must not raise
