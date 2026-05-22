"""Coverage for the pure helpers in ``hermes_cli.providers``.

Existing tests cover end-to-end provider resolution; this pins the
small helpers that gate every dispatch: normalize_provider,
custom_provider_slug, get_label fallback, and is_aggregator."""
from __future__ import annotations

import pytest

from hermes_cli.providers import (
    custom_provider_slug,
    get_label,
    is_aggregator,
    normalize_provider,
)


class TestNormalizeProvider:
    def test_lowercases_and_strips_unaliased_name(self):
        # "openai" happens to be aliased to "openrouter" in the canonical
        # map; pick a name without an alias to exercise the lowercase
        # behaviour in isolation.
        assert normalize_provider("  Anthropic  ") == "anthropic"

    def test_preserves_canonical_id_when_no_alias(self):
        assert normalize_provider("anthropic") == "anthropic"

    def test_returns_key_for_unknown_provider(self):
        # The helper deliberately doesn't validate; unknown stays as itself.
        out = normalize_provider("nonexistent-provider-x")
        assert out == "nonexistent-provider-x"

    def test_empty_string_passes_through(self):
        assert normalize_provider("") == ""


class TestCustomProviderSlug:
    def test_lowercases_input(self):
        assert custom_provider_slug("MyProvider") == "custom:myprovider"

    def test_replaces_spaces_with_hyphens(self):
        assert custom_provider_slug("My Cool Provider") == "custom:my-cool-provider"

    def test_strips_surrounding_whitespace(self):
        assert custom_provider_slug("  foo  ") == "custom:foo"

    def test_empty_string_yields_bare_prefix(self):
        assert custom_provider_slug("") == "custom:"


class TestGetLabel:
    def test_returns_string_for_known_provider(self):
        label = get_label("openai")
        assert isinstance(label, str) and label

    def test_returns_a_string_even_for_unknown_provider(self):
        # No exception — falls back to the input id or a similar slug.
        out = get_label("nonexistent-provider-xyz")
        assert isinstance(out, str) and out


class TestIsAggregator:
    def test_unknown_provider_returns_false(self):
        assert is_aggregator("nonexistent-zzz") is False

    def test_returns_bool_for_known_provider(self):
        # openai is a single-model provider so not an aggregator.
        out = is_aggregator("openai")
        assert isinstance(out, bool)
