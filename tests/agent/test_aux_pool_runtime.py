"""Coverage for _pool_runtime_api_key + _pool_runtime_base_url
in agent.auxiliary_client — the runtime credential surface for
pool entries."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent.auxiliary_client import (
    _pool_runtime_api_key,
    _pool_runtime_base_url,
)


class TestPoolRuntimeApiKey:
    def test_none_entry(self):
        assert _pool_runtime_api_key(None) == ""

    def test_runtime_api_key_wins(self):
        entry = SimpleNamespace(runtime_api_key="rt-key", access_token="other")
        assert _pool_runtime_api_key(entry) == "rt-key"

    def test_falls_back_to_access_token(self):
        entry = SimpleNamespace(runtime_api_key=None, access_token="at-key")
        assert _pool_runtime_api_key(entry) == "at-key"

    def test_strip_whitespace(self):
        entry = SimpleNamespace(runtime_api_key="  rt  ")
        assert _pool_runtime_api_key(entry) == "rt"

    def test_empty_strings_all_around(self):
        entry = SimpleNamespace(runtime_api_key="", access_token="")
        assert _pool_runtime_api_key(entry) == ""

    def test_no_attrs_returns_empty(self):
        entry = SimpleNamespace()
        assert _pool_runtime_api_key(entry) == ""


class TestPoolRuntimeBaseUrl:
    def test_none_entry_returns_stripped_fallback(self):
        assert _pool_runtime_base_url(None, fallback="https://x/") == "https://x"

    def test_none_entry_blank_fallback(self):
        assert _pool_runtime_base_url(None) == ""

    def test_runtime_base_url_wins(self):
        entry = SimpleNamespace(
            runtime_base_url="https://rt/",
            inference_base_url="https://inf",
            base_url="https://bu",
        )
        assert _pool_runtime_base_url(entry, fallback="https://fb") == "https://rt"

    def test_inference_base_url_fallback(self):
        entry = SimpleNamespace(
            runtime_base_url=None,
            inference_base_url="https://inf/",
            base_url="https://bu",
        )
        assert _pool_runtime_base_url(entry) == "https://inf"

    def test_base_url_fallback(self):
        entry = SimpleNamespace(
            runtime_base_url=None,
            inference_base_url=None,
            base_url="https://bu/",
        )
        assert _pool_runtime_base_url(entry) == "https://bu"

    def test_fallback_when_no_attrs(self):
        entry = SimpleNamespace()
        assert _pool_runtime_base_url(entry, fallback="https://fb/") == "https://fb"

    def test_strip_trailing_slashes(self):
        entry = SimpleNamespace(runtime_base_url="https://x///")
        # Implementation uses .rstrip("/") which removes all trailing slashes.
        assert _pool_runtime_base_url(entry) == "https://x"
