"""Coverage for ``_normalize_error_context`` in
``agent.credential_pool``."""
from __future__ import annotations

import time

import pytest

from agent.credential_pool import _normalize_error_context


class TestNormalizeErrorContext:
    def test_none_returns_empty_dict(self):
        assert _normalize_error_context(None) == {}

    def test_non_dict_returns_empty_dict(self):
        assert _normalize_error_context("not a dict") == {}  # type: ignore[arg-type]

    def test_empty_dict_returns_empty(self):
        assert _normalize_error_context({}) == {}

    def test_reason_and_message_passed_through_stripped(self):
        out = _normalize_error_context({
            "reason": "  quota  ",
            "message": "  rate-limited  ",
        })
        assert out["reason"] == "quota"
        assert out["message"] == "rate-limited"

    def test_blank_reason_dropped(self):
        out = _normalize_error_context({"reason": "   ", "message": "msg"})
        assert "reason" not in out
        assert out["message"] == "msg"

    def test_reset_at_parsed_to_seconds(self):
        out = _normalize_error_context({"reset_at": 1_700_000_000})
        assert out["reset_at"] == 1_700_000_000.0

    def test_resets_at_alias_accepted(self):
        out = _normalize_error_context({"resets_at": 1_700_000_000})
        assert out["reset_at"] == 1_700_000_000.0

    def test_retry_until_alias_accepted(self):
        out = _normalize_error_context({"retry_until": 1_700_000_000})
        assert out["reset_at"] == 1_700_000_000.0

    def test_retry_delay_in_message_synthesizes_reset_at(self):
        # Without explicit reset_at, helper extracts a delay from message
        # and computes reset_at = now + delay.
        before = time.time()
        out = _normalize_error_context({
            "message": "rate-limited, retry after 5 seconds",
        })
        after = time.time()
        assert "reset_at" in out
        assert before + 5 - 1 <= out["reset_at"] <= after + 5 + 1

    def test_no_timing_info_omits_reset_at(self):
        out = _normalize_error_context({"message": "vague error"})
        assert "reset_at" not in out

    def test_non_string_reason_dropped(self):
        out = _normalize_error_context({"reason": 42, "message": "ok"})
        assert "reason" not in out
        assert out["message"] == "ok"
