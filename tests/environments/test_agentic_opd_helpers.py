"""Coverage for pure helpers in environments.agentic_opd_env."""
from __future__ import annotations

import pytest

pytest.importorskip("atroposlib")

from environments.agentic_opd_env import (  # noqa: E402
    _build_hint_judge_messages,
    _parse_hint_result,
    _select_best_hint,
    _append_hint_to_messages,
)


class TestBuildHintJudgeMessages:
    def test_includes_response_and_next_state(self):
        out = _build_hint_judge_messages(
            response_text="assistant did X",
            next_state_text="tool returned Y",
            next_state_role="tool",
        )
        assert len(out) == 2
        assert out[0]["role"] == "system"
        assert out[1]["role"] == "user"
        assert "assistant did X" in out[1]["content"]
        assert "tool returned Y" in out[1]["content"]
        assert "role: tool" in out[1]["content"]

    def test_role_label_customisable(self):
        out = _build_hint_judge_messages("a", "b", next_state_role="user")
        assert "role: user" in out[1]["content"]


class TestParseHintResult:
    def test_positive_hint(self):
        text = (
            "Analysis...\n\\boxed{1}\n[HINT_START]Use the right tool[HINT_END]"
        )
        score, hint = _parse_hint_result(text)
        assert score == 1
        assert hint == "Use the right tool"

    def test_negative_no_hint(self):
        text = "\\boxed{-1}"
        score, hint = _parse_hint_result(text)
        assert score == -1
        assert hint == ""

    def test_missing_box_returns_none(self):
        score, hint = _parse_hint_result("no scoring here")
        assert score is None
        assert hint == ""

    def test_invalid_box_value(self):
        # \boxed{5} isn't ±1 → score=None
        score, _ = _parse_hint_result("\\boxed{5}")
        assert score is None

    def test_picks_last_boxed(self):
        text = "\\boxed{1}\n\\boxed{-1}"
        score, _ = _parse_hint_result(text)
        assert score == -1

    def test_picks_last_hint(self):
        text = "\\boxed{1}\n[HINT_START]first[HINT_END]\n[HINT_START]second[HINT_END]"
        _, hint = _parse_hint_result(text)
        assert hint == "second"

    def test_multiline_hint(self):
        text = "\\boxed{1}\n[HINT_START]line1\nline2[HINT_END]"
        _, hint = _parse_hint_result(text)
        assert "line1" in hint and "line2" in hint


class TestSelectBestHint:
    def test_no_good_votes_returns_none(self):
        votes = [{"score": -1, "hint": "ignored"}]
        assert _select_best_hint(votes) is None

    def test_short_hint_filtered(self):
        # length <= 10 chars → filtered out
        votes = [{"score": 1, "hint": "too short"}]
        assert _select_best_hint(votes) is None

    def test_returns_longest_good_hint(self):
        votes = [
            {"score": 1, "hint": "this is a long hint"},
            {"score": 1, "hint": "even longer hint here yes"},
            {"score": -1, "hint": "this is a very very very long but negative hint"},
        ]
        out = _select_best_hint(votes)
        assert out is not None
        assert out["hint"] == "even longer hint here yes"

    def test_non_string_hint_ignored(self):
        votes = [{"score": 1, "hint": None}]
        assert _select_best_hint(votes) is None


class TestAppendHintToMessages:
    def test_appends_to_last_user(self):
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
        ]
        out = _append_hint_to_messages(msgs, "Try X")
        # Last user message gets the suffix.
        last_user = next(m for m in reversed(out) if m["role"] == "user")
        assert "Q2" in last_user["content"]
        assert "Try X" in last_user["content"]
        assert "[user's hint" in last_user["content"]

    def test_empty_messages_synthesizes_one(self):
        out = _append_hint_to_messages([], "Hi")
        assert len(out) == 1
        assert out[0]["role"] == "user"
        assert "Hi" in out[0]["content"]

    def test_no_user_appends_to_last(self):
        msgs = [{"role": "system", "content": "sys"}]
        out = _append_hint_to_messages(msgs, "Help")
        # No user → appends to last message (the system).
        assert "Help" in out[-1]["content"]

    def test_content_list_is_flattened(self):
        msgs = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "part1"}, {"type": "text", "text": "part2"}],
            }
        ]
        out = _append_hint_to_messages(msgs, "Hint X")
        assert isinstance(out[0]["content"], str)
        assert "part1" in out[0]["content"]
        assert "Hint X" in out[0]["content"]

    def test_does_not_mutate_input(self):
        msgs = [{"role": "user", "content": "orig"}]
        original = msgs[0]["content"]
        _append_hint_to_messages(msgs, "Hint")
        # Input untouched.
        assert msgs[0]["content"] == original
