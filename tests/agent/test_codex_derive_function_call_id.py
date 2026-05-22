"""Coverage for ``_derive_responses_function_call_id`` in
``agent.codex_responses_adapter`` — must always produce an id starting
with `fc_` (Responses API requirement)."""
from __future__ import annotations

import pytest

from agent.codex_responses_adapter import _derive_responses_function_call_id


class TestDeriveResponsesFunctionCallId:
    def test_already_fc_prefixed_response_item_passes_through(self):
        assert (
            _derive_responses_function_call_id(
                "anything", response_item_id="fc_abc123"
            )
            == "fc_abc123"
        )

    def test_call_prefixed_source_rewritten_to_fc(self):
        # "call_xyz" → "fc_xyz" (replaces just the prefix).
        out = _derive_responses_function_call_id("call_xyz")
        assert out == "fc_xyz"

    def test_already_fc_call_id_returned_as_is(self):
        assert (
            _derive_responses_function_call_id("fc_already") == "fc_already"
        )

    def test_arbitrary_string_gets_fc_prefix(self):
        # Non-empty plain string source becomes fc_<sanitized>.
        out = _derive_responses_function_call_id("plain-id")
        assert out.startswith("fc_")

    def test_special_characters_sanitised(self):
        # Only [A-Za-z0-9_-] survives sanitization.
        out = _derive_responses_function_call_id("abc/def?ghi=jkl")
        assert out.startswith("fc_")
        # Slashes / question marks / equals signs are stripped.
        for bad in "/?=":
            assert bad not in out

    def test_empty_inputs_synthesize_fc_id(self):
        # No call_id, no response_item_id → random fc_<sha1> with the
        # uuid.uuid4 fallback.
        out = _derive_responses_function_call_id("", response_item_id=None)
        assert out.startswith("fc_")
        assert len(out) > len("fc_")

    def test_long_source_truncated_to_48(self):
        long = "a" * 100
        out = _derive_responses_function_call_id(long)
        # Body is capped at 48 chars after fc_.
        body = out[len("fc_"):]
        assert len(body) <= 48

    def test_response_item_id_falls_back_to_call_id_if_not_fc(self):
        out = _derive_responses_function_call_id(
            "call_abc", response_item_id="not_fc_prefix"
        )
        # When response_item_id doesn't start with fc_, the call_id
        # determines the output.
        assert out == "fc_abc"
