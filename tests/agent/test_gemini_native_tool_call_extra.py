"""Coverage for ``_tool_call_extra_signature`` in
``agent.gemini_native_adapter``."""
from __future__ import annotations

import pytest

from agent.gemini_native_adapter import _tool_call_extra_signature


class TestToolCallExtraSignature:
    def test_no_extra_content_returns_none(self):
        assert _tool_call_extra_signature({}) is None

    def test_non_dict_extra_returns_none(self):
        assert _tool_call_extra_signature({"extra_content": "not a dict"}) is None

    def test_string_under_google_returns_string(self):
        out = _tool_call_extra_signature({
            "extra_content": {"google": "sig-abc"},
        })
        assert out == "sig-abc"

    def test_dict_under_google_with_thought_signature_key(self):
        out = _tool_call_extra_signature({
            "extra_content": {
                "google": {"thought_signature": "sig-1"},
            },
        })
        assert out == "sig-1"

    def test_dict_under_google_with_camelCase_thoughtSignature(self):
        out = _tool_call_extra_signature({
            "extra_content": {
                "google": {"thoughtSignature": "sig-2"},
            },
        })
        assert out == "sig-2"

    def test_dict_with_no_signature_keys_returns_none(self):
        out = _tool_call_extra_signature({
            "extra_content": {"google": {"unrelated": "x"}},
        })
        assert out is None

    def test_thought_signature_top_level_alias(self):
        # `thought_signature` directly under extra_content is an alias.
        out = _tool_call_extra_signature({
            "extra_content": {"thought_signature": "alias-sig"},
        })
        assert out == "alias-sig"

    def test_empty_string_signature_returns_none(self):
        out = _tool_call_extra_signature({
            "extra_content": {"google": ""},
        })
        assert out is None
