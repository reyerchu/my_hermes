"""Coverage for
``agent.codex_responses_adapter._summarize_user_message_for_log``."""
from __future__ import annotations

import pytest

from agent.codex_responses_adapter import _summarize_user_message_for_log


class TestSummarizeUserMessageForLog:
    def test_none_returns_empty_string(self):
        assert _summarize_user_message_for_log(None) == ""

    def test_str_passes_through(self):
        assert _summarize_user_message_for_log("hello") == "hello"

    def test_empty_list_returns_empty(self):
        assert _summarize_user_message_for_log([]) == ""

    def test_text_parts_concatenated(self):
        out = _summarize_user_message_for_log([
            {"type": "text", "text": "alpha"},
            {"type": "text", "text": "beta"},
        ])
        assert "alpha" in out
        assert "beta" in out

    def test_image_parts_mentioned(self):
        out = _summarize_user_message_for_log([
            {"type": "text", "text": "see this"},
            {"type": "image_url", "image_url": {"url": "x"}},
        ])
        assert "see this" in out
        # The summary tags image counts somehow (e.g. "[+1 image]").
        assert "image" in out.lower() or "1" in out

    def test_raw_string_parts_concatenated(self):
        out = _summarize_user_message_for_log(["alpha", "beta"])
        assert "alpha" in out and "beta" in out

    def test_unexpected_scalar_returns_str_repr(self):
        # Unsupported scalar types fall back to str(content).
        out = _summarize_user_message_for_log(42)
        assert "42" in out
