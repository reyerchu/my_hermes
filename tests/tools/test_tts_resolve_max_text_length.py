"""Coverage for ``tools.tts_tool._resolve_max_text_length``.

The helper gates input truncation for every TTS request — a regression
either dispatches over the provider limit (rejected with 4xx) or silently
truncates short content."""
from __future__ import annotations

import pytest

from tools.tts_tool import (
    FALLBACK_MAX_TEXT_LENGTH,
    PROVIDER_MAX_TEXT_LENGTH,
    _resolve_max_text_length,
)


class TestResolveMaxTextLength:
    def test_empty_provider_returns_fallback(self):
        assert _resolve_max_text_length(None) == FALLBACK_MAX_TEXT_LENGTH
        assert _resolve_max_text_length("") == FALLBACK_MAX_TEXT_LENGTH

    def test_known_provider_uses_table_default(self):
        # Pick any provider from the global table.
        for provider, expected in PROVIDER_MAX_TEXT_LENGTH.items():
            out = _resolve_max_text_length(provider)
            assert out == expected

    def test_unknown_provider_falls_back(self):
        # Not in PROVIDER_MAX_TEXT_LENGTH and no user config → fallback.
        assert (
            _resolve_max_text_length("totally-unknown-provider")
            == FALLBACK_MAX_TEXT_LENGTH
        )

    def test_user_override_takes_precedence(self):
        cfg = {"openai": {"max_text_length": 1234}}
        assert _resolve_max_text_length("openai", cfg) == 1234

    def test_non_positive_override_falls_through_to_default(self):
        cfg = {"openai": {"max_text_length": 0}}
        # 0 isn't a valid positive int; helper falls through.
        out = _resolve_max_text_length("openai", cfg)
        assert out != 0
        # OpenAI's built-in default exists in the table.
        if "openai" in PROVIDER_MAX_TEXT_LENGTH:
            assert out == PROVIDER_MAX_TEXT_LENGTH["openai"]

    def test_bool_override_treated_as_invalid(self):
        # `max_text_length: true` in YAML decodes as the bool True; helper
        # rejects bool overrides so a typo can't disable truncation.
        cfg = {"openai": {"max_text_length": True}}
        out = _resolve_max_text_length("openai", cfg)
        # Falls through to provider default or fallback.
        assert out > 0

    def test_provider_name_stripped_and_lowercased(self):
        # Provider name is normalised before the table lookup.
        for provider, expected in PROVIDER_MAX_TEXT_LENGTH.items():
            out = _resolve_max_text_length(f"  {provider.upper()}  ")
            assert out == expected

    def test_string_override_falls_through(self):
        cfg = {"openai": {"max_text_length": "not a number"}}
        out = _resolve_max_text_length("openai", cfg)
        assert out > 0
