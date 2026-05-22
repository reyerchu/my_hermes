"""Coverage for ``_chat_content_to_responses_parts`` in
``agent.codex_responses_adapter`` — the OpenAI Chat → Responses content
translator."""
from __future__ import annotations

import pytest

from agent.codex_responses_adapter import _chat_content_to_responses_parts


class TestChatContentToResponsesParts:
    def test_plain_string_returns_empty(self):
        # The helper expects a list; plain strings return [] so callers
        # fall back to a string-path code branch.
        out = _chat_content_to_responses_parts("hello", role="user")
        assert out == []

    def test_user_role_uses_input_text(self):
        out = _chat_content_to_responses_parts(
            [{"type": "text", "text": "hi"}], role="user"
        )
        assert out[0]["type"] == "input_text"

    def test_assistant_role_uses_output_text(self):
        out = _chat_content_to_responses_parts(
            [{"type": "text", "text": "hi"}], role="assistant"
        )
        assert out[0]["type"] == "output_text"

    def test_text_parts_translated(self):
        out = _chat_content_to_responses_parts(
            [{"type": "text", "text": "alpha"}],
            role="user",
        )
        assert out[0]["type"] == "input_text"
        assert out[0]["text"] == "alpha"

    def test_image_url_part_translated_to_input_image(self):
        out = _chat_content_to_responses_parts(
            [{"type": "image_url", "image_url": {"url": "data:..."}}],
            role="user",
        )
        # The Responses API requires "input_image".
        assert any(p.get("type") == "input_image" for p in out)

    def test_none_content_returns_empty_list(self):
        out = _chat_content_to_responses_parts(None, role="user")
        assert out == []

    def test_empty_string_returns_empty(self):
        # Non-list input always returns [] per the helper's contract.
        assert _chat_content_to_responses_parts("", role="user") == []

    def test_empty_string_inside_list_skipped(self):
        # Empty strings inside the list are skipped (no zero-width parts).
        out = _chat_content_to_responses_parts(["", "text"], role="user")
        # Only one non-empty text part should survive.
        texts = [p["text"] for p in out if p.get("type") in ("input_text", "output_text")]
        assert texts == ["text"]

    def test_mixed_list_produces_one_part_per_input(self):
        out = _chat_content_to_responses_parts(
            [
                {"type": "text", "text": "before"},
                {"type": "image_url", "image_url": {"url": "x"}},
                {"type": "text", "text": "after"},
            ],
            role="user",
        )
        types = [p.get("type") for p in out]
        # Order is preserved.
        assert types[0] == "input_text"
        assert types[1] == "input_image"
        assert types[2] == "input_text"
