"""Coverage for _extract_url_query_params and _safe_isinstance in
agent.auxiliary_client."""
from __future__ import annotations

import pytest

from agent.auxiliary_client import (
    _extract_url_query_params,
    _safe_isinstance,
)


class TestExtractUrlQueryParams:
    def test_no_query(self):
        clean, params = _extract_url_query_params("https://example.com/path")
        assert clean == "https://example.com/path"
        assert params is None

    def test_single_query_param(self):
        clean, params = _extract_url_query_params("https://x.com/p?a=1")
        assert clean == "https://x.com/p"
        assert params == {"a": "1"}

    def test_multiple_query_params(self):
        clean, params = _extract_url_query_params("https://x.com/p?a=1&b=2")
        assert params == {"a": "1", "b": "2"}

    def test_query_with_path_query(self):
        clean, params = _extract_url_query_params("https://x/p/q?key=v")
        assert clean == "https://x/p/q"
        assert params == {"key": "v"}

    def test_empty_value(self):
        clean, params = _extract_url_query_params("https://x?a=")
        # parse_qs drops empty values by default — params dict won't include "a"
        # OR includes "a": "" depending on parse_qs keep_blank_values default.
        assert clean == "https://x"

    def test_repeated_keys_first_wins(self):
        # parse_qs returns lists; helper takes [0].
        clean, params = _extract_url_query_params("https://x?a=1&a=2")
        assert params == {"a": "1"}


class TestSafeIsinstance:
    def test_true_path(self):
        assert _safe_isinstance(5, int) is True

    def test_false_path(self):
        assert _safe_isinstance("hi", int) is False

    def test_non_type_returns_false(self):
        # When maybe_type isn't a class, isinstance raises TypeError →
        # helper catches it and returns False.
        assert _safe_isinstance(5, "not a class") is False

    def test_none_type_returns_false(self):
        assert _safe_isinstance(5, None) is False
