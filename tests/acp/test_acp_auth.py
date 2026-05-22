"""Coverage for ``acp_adapter.auth`` — detects whether Hermes has
any runtime provider configured."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from acp_adapter.auth import detect_provider, has_provider


def _patch_runtime(runtime):
    """Patch resolve_runtime_provider to return the given dict (or raise)."""
    if isinstance(runtime, Exception):
        return patch(
            "hermes_cli.runtime_provider.resolve_runtime_provider",
            side_effect=runtime,
        )
    return patch(
        "hermes_cli.runtime_provider.resolve_runtime_provider",
        return_value=runtime,
    )


class TestDetectProvider:
    def test_returns_lowercase_provider_when_both_present(self):
        with _patch_runtime({"api_key": "sk-xxx", "provider": "Anthropic"}):
            assert detect_provider() == "anthropic"

    def test_returns_none_when_api_key_missing(self):
        with _patch_runtime({"provider": "anthropic"}):
            assert detect_provider() is None

    def test_returns_none_when_api_key_blank(self):
        with _patch_runtime({"api_key": "   ", "provider": "anthropic"}):
            assert detect_provider() is None

    def test_returns_none_when_provider_missing(self):
        with _patch_runtime({"api_key": "sk-xxx"}):
            assert detect_provider() is None

    def test_returns_none_when_provider_blank(self):
        with _patch_runtime({"api_key": "sk-xxx", "provider": "  "}):
            assert detect_provider() is None

    def test_returns_none_when_api_key_not_string(self):
        with _patch_runtime({"api_key": 12345, "provider": "anthropic"}):
            assert detect_provider() is None

    def test_returns_none_on_runtime_error(self):
        with _patch_runtime(RuntimeError("boom")):
            assert detect_provider() is None

    def test_returns_none_on_arbitrary_exception(self):
        with _patch_runtime(ValueError("nope")):
            assert detect_provider() is None

    def test_strips_surrounding_whitespace(self):
        with _patch_runtime({"api_key": "sk-x", "provider": "  Anthropic  "}):
            assert detect_provider() == "anthropic"


class TestHasProvider:
    def test_true_when_detect_provider_returns_value(self):
        with _patch_runtime({"api_key": "k", "provider": "anthropic"}):
            assert has_provider() is True

    def test_false_when_detect_provider_returns_none(self):
        with _patch_runtime({}):
            assert has_provider() is False
