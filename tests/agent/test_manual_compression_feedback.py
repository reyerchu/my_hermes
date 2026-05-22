"""Coverage for ``agent.manual_compression_feedback``.

Tiny pure helper that builds the user-facing summary the agent prints after
a manual /compact.  No existing direct tests — the consumers were tested at
a higher level so behavioural drift here is invisible until UI strings
break.
"""
from __future__ import annotations

from agent.manual_compression_feedback import summarize_manual_compression


class TestSummarizeManualCompression:
    def test_noop_when_messages_unchanged(self):
        msgs = [{"role": "user", "content": "hi"}]
        result = summarize_manual_compression(msgs, msgs, 100, 100)
        assert result["noop"] is True
        assert result["note"] is None
        assert "No changes" in result["headline"]
        assert "1 messages" in result["headline"]

    def test_noop_with_unchanged_token_count_uses_unchanged_label(self):
        msgs = [{"role": "user", "content": "hi"}]
        result = summarize_manual_compression(msgs, msgs, 50, 50)
        assert "unchanged" in result["token_line"]
        # No arrow when the counts match.
        assert "→" not in result["token_line"]

    def test_noop_with_different_token_count_shows_arrow(self):
        msgs = [{"role": "user", "content": "hi"}]
        result = summarize_manual_compression(msgs, msgs, 100, 120)
        assert "unchanged" not in result["token_line"]
        assert "→" in result["token_line"]

    def test_compression_reduces_message_count(self):
        before = [{"role": "user", "content": "a"}] * 5
        after = [{"role": "user", "content": "summary"}]
        result = summarize_manual_compression(before, after, 1_000, 600)
        assert result["noop"] is False
        assert result["headline"] == "Compressed: 5 → 1 messages"
        assert result["token_line"] == (
            "Approx request size: ~1,000 → ~600 tokens"
        )
        assert result["note"] is None

    def test_note_appears_when_compression_grows_estimated_tokens(self):
        before = [{"role": "user", "content": "a"}] * 5
        after = [{"role": "user", "content": "denser summary"}]
        result = summarize_manual_compression(before, after, 100, 200)
        assert result["noop"] is False
        assert result["note"] is not None
        assert "denser summaries" in result["note"]

    def test_no_note_when_messages_grew_or_held(self):
        # message count went UP — note should NOT fire.
        before = [{"role": "user", "content": "a"}]
        after = [{"role": "user", "content": "a"}, {"role": "user", "content": "b"}]
        result = summarize_manual_compression(before, after, 100, 200)
        assert result["note"] is None

    def test_token_count_formatted_with_thousands_separator(self):
        before = [{"role": "user", "content": "x"}] * 3
        after = [{"role": "user", "content": "x"}]
        result = summarize_manual_compression(before, after, 1234567, 250000)
        assert "1,234,567" in result["token_line"]
        assert "250,000" in result["token_line"]

    def test_keys_returned_are_stable(self):
        result = summarize_manual_compression([], [], 0, 0)
        assert set(result.keys()) == {"noop", "headline", "token_line", "note"}
