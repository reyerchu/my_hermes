"""Coverage for pure helpers in tools.tts_tool — config resolution
and command-provider option parsing."""
from __future__ import annotations

import pytest

from tools.tts_tool import (
    _resolve_max_text_length,
    _get_provider_section,
    _get_named_provider_config,
    _is_command_provider_config,
    _resolve_command_provider_config,
    _iter_command_providers,
    _get_command_tts_timeout,
    _get_command_tts_output_format,
    _is_command_tts_voice_compatible,
    BUILTIN_TTS_PROVIDERS,
    PROVIDER_MAX_TEXT_LENGTH,
    ELEVENLABS_MODEL_MAX_TEXT_LENGTH,
    FALLBACK_MAX_TEXT_LENGTH,
    DEFAULT_COMMAND_TTS_TIMEOUT_SECONDS,
    DEFAULT_COMMAND_TTS_OUTPUT_FORMAT,
    DEFAULT_COMMAND_TTS_MAX_TEXT_LENGTH,
)


class TestResolveMaxTextLength:
    def test_none_provider_returns_fallback(self):
        assert _resolve_max_text_length(None) == FALLBACK_MAX_TEXT_LENGTH

    def test_empty_provider_returns_fallback(self):
        assert _resolve_max_text_length("") == FALLBACK_MAX_TEXT_LENGTH

    def test_known_builtin_provider(self):
        # Pick any known built-in.
        provider = next(iter(PROVIDER_MAX_TEXT_LENGTH))
        out = _resolve_max_text_length(provider, {})
        assert out == PROVIDER_MAX_TEXT_LENGTH[provider]

    def test_user_override_wins(self):
        provider = next(iter(PROVIDER_MAX_TEXT_LENGTH))
        cfg = {provider: {"max_text_length": 12345}}
        assert _resolve_max_text_length(provider, cfg) == 12345

    def test_boolean_override_ignored(self):
        provider = next(iter(PROVIDER_MAX_TEXT_LENGTH))
        cfg = {provider: {"max_text_length": True}}
        # Falls through to the built-in value.
        assert _resolve_max_text_length(provider, cfg) == PROVIDER_MAX_TEXT_LENGTH[provider]

    def test_non_positive_override_ignored(self):
        provider = next(iter(PROVIDER_MAX_TEXT_LENGTH))
        cfg = {provider: {"max_text_length": -100}}
        assert _resolve_max_text_length(provider, cfg) == PROVIDER_MAX_TEXT_LENGTH[provider]

    def test_elevenlabs_model_lookup(self):
        # Use the first known model id from the table.
        if not ELEVENLABS_MODEL_MAX_TEXT_LENGTH:
            pytest.skip("ELEVENLABS_MODEL_MAX_TEXT_LENGTH is empty")
        model_id, expected = next(iter(ELEVENLABS_MODEL_MAX_TEXT_LENGTH.items()))
        cfg = {"elevenlabs": {"model_id": model_id}}
        assert _resolve_max_text_length("elevenlabs", cfg) == expected

    def test_user_command_provider_default(self):
        # User-declared command provider with no max_text_length →
        # DEFAULT_COMMAND_TTS_MAX_TEXT_LENGTH.
        cfg = {"providers": {"my-tts": {"type": "command", "command": "say {text}"}}}
        out = _resolve_max_text_length("my-tts", cfg)
        assert out == DEFAULT_COMMAND_TTS_MAX_TEXT_LENGTH

    def test_user_command_provider_override(self):
        cfg = {"providers": {"my-tts": {"type": "command", "command": "x", "max_text_length": 7777}}}
        assert _resolve_max_text_length("my-tts", cfg) == 7777


class TestGetProviderSection:
    def test_returns_dict(self):
        assert _get_provider_section({"x": {"a": 1}}, "x") == {"a": 1}

    def test_missing_returns_empty(self):
        assert _get_provider_section({}, "x") == {}

    def test_non_dict_value_returns_empty(self):
        assert _get_provider_section({"x": "string"}, "x") == {}

    def test_non_dict_tts_config_returns_empty(self):
        assert _get_provider_section("not a dict", "x") == {}  # type: ignore[arg-type]


class TestGetNamedProviderConfig:
    def test_canonical_path(self):
        cfg = {"providers": {"my": {"command": "x"}}}
        assert _get_named_provider_config(cfg, "my") == {"command": "x"}

    def test_legacy_path_for_non_builtin(self):
        cfg = {"my": {"command": "x"}}
        assert _get_named_provider_config(cfg, "my") == {"command": "x"}

    def test_legacy_path_rejected_for_builtin(self):
        # Even if the user puts settings under tts.<builtin>, that's not
        # treated as a "named" provider — returns empty.
        provider = next(iter(BUILTIN_TTS_PROVIDERS))
        cfg = {provider: {"command": "x"}}
        assert _get_named_provider_config(cfg, provider) == {}

    def test_missing_returns_empty(self):
        assert _get_named_provider_config({}, "unknown") == {}


class TestIsCommandProviderConfig:
    def test_command_string(self):
        assert _is_command_provider_config({"command": "say {text}"}) is True

    def test_explicit_type(self):
        assert _is_command_provider_config({"type": "command", "command": "x"}) is True

    def test_wrong_type_rejected(self):
        assert _is_command_provider_config({"type": "openai", "command": "x"}) is False

    def test_missing_command_rejected(self):
        assert _is_command_provider_config({"type": "command"}) is False

    def test_blank_command_rejected(self):
        assert _is_command_provider_config({"command": "   "}) is False

    def test_non_dict_returns_false(self):
        assert _is_command_provider_config("string") is False  # type: ignore[arg-type]


class TestResolveCommandProviderConfig:
    def test_builtin_returns_none(self):
        # Even with a command spec, built-in provider names are rejected.
        provider = next(iter(BUILTIN_TTS_PROVIDERS))
        cfg = {provider: {"command": "x"}}
        assert _resolve_command_provider_config(provider, cfg) is None

    def test_user_command(self):
        cfg = {"providers": {"my": {"type": "command", "command": "say {text}"}}}
        out = _resolve_command_provider_config("my", cfg)
        assert out is not None
        assert out["command"] == "say {text}"

    def test_empty_provider(self):
        assert _resolve_command_provider_config("", {}) is None


class TestIterCommandProviders:
    def test_yields_only_command_types(self):
        cfg = {
            "providers": {
                "a": {"command": "say-a {text}"},
                "b": {"type": "openai"},  # not command
                "c": {"command": ""},     # blank
            }
        }
        out = dict(_iter_command_providers(cfg))
        assert "a" in out
        assert "b" not in out
        assert "c" not in out

    def test_non_dict_yields_nothing(self):
        assert list(_iter_command_providers(None)) == []  # type: ignore[arg-type]

    def test_builtin_name_filtered(self):
        provider = next(iter(BUILTIN_TTS_PROVIDERS))
        cfg = {"providers": {provider: {"command": "x"}}}
        assert list(_iter_command_providers(cfg)) == []


class TestCommandTtsTimeout:
    def test_default(self):
        assert _get_command_tts_timeout({}) == float(DEFAULT_COMMAND_TTS_TIMEOUT_SECONDS)

    def test_timeout_field(self):
        assert _get_command_tts_timeout({"timeout": 45}) == 45.0

    def test_timeout_seconds_field(self):
        assert _get_command_tts_timeout({"timeout_seconds": 90}) == 90.0

    def test_garbage_falls_back(self):
        assert _get_command_tts_timeout({"timeout": "bad"}) == float(DEFAULT_COMMAND_TTS_TIMEOUT_SECONDS)

    def test_zero_or_negative_falls_back(self):
        assert _get_command_tts_timeout({"timeout": 0}) == float(DEFAULT_COMMAND_TTS_TIMEOUT_SECONDS)
        assert _get_command_tts_timeout({"timeout": -10}) == float(DEFAULT_COMMAND_TTS_TIMEOUT_SECONDS)


class TestCommandTtsOutputFormat:
    def test_default(self):
        assert _get_command_tts_output_format({}) == DEFAULT_COMMAND_TTS_OUTPUT_FORMAT

    def test_explicit_format_field(self):
        assert _get_command_tts_output_format({"format": "wav"}) == "wav"

    def test_output_format_alias(self):
        assert _get_command_tts_output_format({"output_format": "ogg"}) == "ogg"

    def test_invalid_format_falls_back(self):
        assert _get_command_tts_output_format({"format": "exe"}) == DEFAULT_COMMAND_TTS_OUTPUT_FORMAT

    def test_inferred_from_output_path(self):
        assert _get_command_tts_output_format({}, output_path="/tmp/x.flac") == "flac"

    def test_invalid_path_extension_falls_back_to_format(self):
        assert (
            _get_command_tts_output_format({"format": "wav"}, output_path="/tmp/x.exe")
            == "wav"
        )


class TestVoiceCompatible:
    def test_default_false(self):
        assert _is_command_tts_voice_compatible({}) is False

    def test_bool_passthrough(self):
        assert _is_command_tts_voice_compatible({"voice_compatible": True}) is True

    def test_truthy_strings(self):
        for s in ("1", "true", "TRUE", "yes", "on"):
            assert _is_command_tts_voice_compatible({"voice_compatible": s}) is True

    def test_falsy_strings(self):
        for s in ("0", "false", "no", "off"):
            assert _is_command_tts_voice_compatible({"voice_compatible": s}) is False
