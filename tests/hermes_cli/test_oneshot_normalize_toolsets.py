"""Coverage for the toolset-normalisation helper inside
``hermes_cli.oneshot``."""
from __future__ import annotations

import pytest

from hermes_cli.oneshot import _normalize_toolsets


class TestNormalizeToolsets:
    def test_none_returns_none(self):
        assert _normalize_toolsets(None) is None

    def test_empty_string_returns_none(self):
        assert _normalize_toolsets("") is None

    def test_empty_list_returns_none(self):
        # Falsy iterables also map to None.
        assert _normalize_toolsets([]) is None

    def test_single_string_wraps_into_list(self):
        assert _normalize_toolsets("hermes-cli") == ["hermes-cli"]

    def test_comma_separated_string_splits(self):
        assert _normalize_toolsets("a,b,c") == ["a", "b", "c"]

    def test_strips_whitespace_around_each_item(self):
        assert _normalize_toolsets("  a , b ,  c") == ["a", "b", "c"]

    def test_list_input_passes_through_stripped(self):
        assert _normalize_toolsets([" a ", "b "]) == ["a", "b"]

    def test_list_input_each_item_can_be_csv(self):
        assert _normalize_toolsets(["a,b", "c"]) == ["a", "b", "c"]

    def test_tuple_input_works(self):
        assert _normalize_toolsets(("a", "b")) == ["a", "b"]

    def test_scalar_value_wrapped(self):
        # Non-string non-iterable → str() and wrapped.
        assert _normalize_toolsets(42) == ["42"]
