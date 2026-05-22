"""Coverage for ``_extract_retry_delay_seconds`` in
``agent.credential_pool``."""
from __future__ import annotations

import pytest

from agent.credential_pool import _extract_retry_delay_seconds


class TestExtractRetryDelaySeconds:
    def test_empty_message_returns_none(self):
        assert _extract_retry_delay_seconds("") is None
        assert _extract_retry_delay_seconds(None) is None  # type: ignore[arg-type]

    def test_no_delay_token_returns_none(self):
        assert _extract_retry_delay_seconds("some generic error") is None

    def test_quota_reset_delay_seconds(self):
        msg = "quotaResetDelay: 30s before retry"
        assert _extract_retry_delay_seconds(msg) == 30.0

    def test_quota_reset_delay_milliseconds_converted(self):
        msg = "quotaResetDelay: 1500ms"
        assert _extract_retry_delay_seconds(msg) == 1.5

    def test_quota_reset_delay_float_value(self):
        msg = 'quotaResetDelay: "2.5s"'
        assert _extract_retry_delay_seconds(msg) == 2.5

    def test_quota_reset_delay_case_insensitive(self):
        # Both the key and the unit are case-insensitive.
        assert _extract_retry_delay_seconds("QUOTARESETDELAY: 1MS") == 0.001

    def test_retry_after_seconds_pattern(self):
        msg = "rate-limited, retry after 5 seconds"
        assert _extract_retry_delay_seconds(msg) == 5.0

    def test_retry_n_sec_pattern(self):
        assert _extract_retry_delay_seconds("retry 7 sec") == 7.0

    def test_retry_n_s_pattern(self):
        assert _extract_retry_delay_seconds("retry 12 s") == 12.0

    def test_quota_reset_delay_takes_priority_over_retry_after(self):
        # When both patterns appear, the quotaResetDelay one wins.
        msg = "quotaResetDelay: 30s ; retry after 60 seconds"
        assert _extract_retry_delay_seconds(msg) == 30.0
