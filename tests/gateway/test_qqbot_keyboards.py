"""Coverage for parse helpers in gateway.platforms.qqbot.keyboards."""
from __future__ import annotations

import pytest

from gateway.platforms.qqbot.keyboards import (
    parse_approval_button_data,
    parse_update_prompt_button_data,
    APPROVAL_BUTTON_PREFIX,
    UPDATE_PROMPT_PREFIX,
)


class TestParseApprovalButtonData:
    def test_allow_once(self):
        out = parse_approval_button_data("approve:sess-abc:allow-once")
        assert out == ("sess-abc", "allow-once")

    def test_allow_always(self):
        out = parse_approval_button_data("approve:sess:allow-always")
        assert out == ("sess", "allow-always")

    def test_deny(self):
        out = parse_approval_button_data("approve:sess:deny")
        assert out == ("sess", "deny")

    def test_session_key_with_colons(self):
        # session_key may contain colons (greedy match).
        out = parse_approval_button_data("approve:agent:main:qqbot:c2c:OPENID:allow-once")
        assert out is not None
        sk, decision = out
        assert sk == "agent:main:qqbot:c2c:OPENID"
        assert decision == "allow-once"

    def test_no_match(self):
        assert parse_approval_button_data("update_prompt:y") is None

    def test_bad_decision(self):
        # Decision not in allow-once|allow-always|deny → no match
        assert parse_approval_button_data("approve:sess:maybe") is None

    def test_empty(self):
        assert parse_approval_button_data("") is None

    def test_none(self):
        assert parse_approval_button_data(None) is None  # type: ignore[arg-type]


class TestParseUpdatePromptButtonData:
    def test_yes(self):
        assert parse_update_prompt_button_data("update_prompt:y") == "y"

    def test_no(self):
        assert parse_update_prompt_button_data("update_prompt:n") == "n"

    def test_unknown_answer(self):
        assert parse_update_prompt_button_data("update_prompt:maybe") is None

    def test_wrong_prefix(self):
        assert parse_update_prompt_button_data("approve:sess:deny") is None

    def test_empty(self):
        assert parse_update_prompt_button_data("") is None


class TestPrefixes:
    def test_approval_prefix(self):
        assert APPROVAL_BUTTON_PREFIX == "approve:"

    def test_update_prompt_prefix(self):
        assert UPDATE_PROMPT_PREFIX == "update_prompt:"
