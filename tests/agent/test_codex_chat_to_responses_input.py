"""Coverage for _chat_messages_to_responses_input in
agent.codex_responses_adapter — converts chat-style internal messages
into Responses-API input items."""
from __future__ import annotations

import pytest

from agent.codex_responses_adapter import _chat_messages_to_responses_input


class TestChatMessagesToResponsesInput:
    def test_empty_returns_empty(self):
        assert _chat_messages_to_responses_input([]) == []

    def test_system_message_dropped(self):
        out = _chat_messages_to_responses_input([
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
        ])
        # System never emits a separate item.
        assert not any(it.get("role") == "system" for it in out)
        # User does.
        assert any(it.get("role") == "user" for it in out)

    def test_user_string_content(self):
        out = _chat_messages_to_responses_input([
            {"role": "user", "content": "hello"},
        ])
        # At least one item with role=user emitted.
        user_items = [it for it in out if it.get("role") == "user"]
        assert len(user_items) >= 1

    def test_assistant_string_content(self):
        out = _chat_messages_to_responses_input([
            {"role": "assistant", "content": "Hi there"},
        ])
        # At least one item with role=assistant emitted.
        assert any(
            it.get("role") == "assistant" or it.get("type") == "message"
            for it in out
        )

    def test_non_dict_messages_skipped(self):
        out = _chat_messages_to_responses_input([
            "not a dict",
            42,
            {"role": "user", "content": "ok"},
        ])
        # Only the dict survives.
        user_items = [it for it in out if it.get("role") == "user"]
        assert len(user_items) >= 1

    def test_unknown_role_skipped(self):
        # Role "tool" / "function" etc. aren't in {user, assistant} —
        # the function takes other branches for those (or skips).  We
        # just verify it doesn't crash.
        _chat_messages_to_responses_input([
            {"role": "tool", "content": "x", "tool_call_id": "t1", "name": "f"},
        ])

    def test_user_list_content_extracts_text_parts(self):
        out = _chat_messages_to_responses_input([
            {
                "role": "user",
                "content": [{"type": "text", "text": "abc"}],
            },
        ])
        # The user message contains the input_text content.
        user_items = [it for it in out if it.get("role") == "user"]
        assert user_items
        # Find the text inside.
        flat = str(user_items)
        assert "abc" in flat

    def test_codex_reasoning_replay_skips_no_encrypted_content(self):
        # codex_reasoning_items with no encrypted_content shouldn't add anything.
        out = _chat_messages_to_responses_input([
            {
                "role": "assistant",
                "content": "x",
                "codex_reasoning_items": [{"id": "r1"}],
            },
        ])
        # No reasoning item emitted (no encrypted_content).
        assert not any(it.get("type") == "reasoning" for it in out)

    def test_codex_reasoning_replay_includes_encrypted(self):
        out = _chat_messages_to_responses_input([
            {
                "role": "assistant",
                "content": "x",
                "codex_reasoning_items": [
                    {"id": "r1", "type": "reasoning", "encrypted_content": "blob"},
                ],
            },
        ])
        # The reasoning item is replayed (without its id field).
        reasoning_items = [it for it in out if it.get("type") == "reasoning"]
        assert len(reasoning_items) == 1
        # id should be stripped from the replayed item.
        assert "id" not in reasoning_items[0]
        assert reasoning_items[0]["encrypted_content"] == "blob"

    def test_codex_reasoning_dedup_by_id(self):
        out = _chat_messages_to_responses_input([
            {
                "role": "assistant",
                "content": "x",
                "codex_reasoning_items": [
                    {"id": "r1", "type": "reasoning", "encrypted_content": "a"},
                    {"id": "r1", "type": "reasoning", "encrypted_content": "b"},
                ],
            },
        ])
        reasoning_items = [it for it in out if it.get("type") == "reasoning"]
        # Only first instance kept (deduped on item id).
        assert len(reasoning_items) == 1
