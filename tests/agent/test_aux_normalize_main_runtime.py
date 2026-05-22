"""Coverage for _normalize_main_runtime in agent.auxiliary_client."""
from __future__ import annotations

import pytest

from agent.auxiliary_client import (
    _normalize_main_runtime,
    _MAIN_RUNTIME_FIELDS,
)


class TestNormalizeMainRuntime:
    def test_none_returns_empty(self):
        assert _normalize_main_runtime(None) == {}

    def test_non_dict_returns_empty(self):
        assert _normalize_main_runtime("string") == {}
        assert _normalize_main_runtime(42) == {}

    def test_empty_dict_returns_empty(self):
        assert _normalize_main_runtime({}) == {}

    def test_all_fields_preserved(self):
        out = _normalize_main_runtime({
            "provider": "OpenAI",
            "model": "gpt-x",
            "base_url": "https://x",
            "api_key": "sk-123",
            "api_mode": "anthropic_messages",
        })
        assert set(out.keys()) <= set(_MAIN_RUNTIME_FIELDS)
        # Provider is lowercased.
        assert out["provider"] == "openai"
        assert out["model"] == "gpt-x"

    def test_blank_strings_dropped(self):
        out = _normalize_main_runtime({
            "provider": "  ",
            "model": "gpt-x",
        })
        assert "provider" not in out
        assert out["model"] == "gpt-x"

    def test_non_string_values_dropped(self):
        out = _normalize_main_runtime({
            "provider": 42,
            "model": ["list"],
            "base_url": "https://x",
        })
        assert "provider" not in out
        assert "model" not in out
        assert out["base_url"] == "https://x"

    def test_unknown_fields_ignored(self):
        out = _normalize_main_runtime({
            "provider": "openai",
            "unknown_field": "value",
        })
        assert "unknown_field" not in out
        assert out["provider"] == "openai"

    def test_whitespace_stripped(self):
        out = _normalize_main_runtime({
            "provider": "  openai  ",
            "model": "  gpt-x  ",
        })
        assert out["provider"] == "openai"
        assert out["model"] == "gpt-x"

    def test_main_runtime_fields_constant(self):
        # The five canonical fields.
        for field in ("provider", "model", "base_url", "api_key", "api_mode"):
            assert field in _MAIN_RUNTIME_FIELDS
