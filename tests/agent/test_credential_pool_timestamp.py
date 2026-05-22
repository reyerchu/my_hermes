"""Coverage for ``_parse_absolute_timestamp`` and ``_next_priority`` in
``agent.credential_pool``."""
from __future__ import annotations

from datetime import datetime

import pytest

from agent.credential_pool import (
    _next_priority,
    _parse_absolute_timestamp,
)


class TestParseAbsoluteTimestamp:
    def test_none_returns_none(self):
        assert _parse_absolute_timestamp(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_absolute_timestamp("") is None
        assert _parse_absolute_timestamp("   ") is None

    def test_negative_int_returns_none(self):
        assert _parse_absolute_timestamp(-100) is None
        assert _parse_absolute_timestamp(0) is None

    def test_epoch_seconds_int(self):
        assert _parse_absolute_timestamp(1_700_000_000) == 1_700_000_000.0

    def test_epoch_milliseconds_converted_to_seconds(self):
        # > 1e12 is treated as milliseconds.
        assert _parse_absolute_timestamp(1_700_000_000_000) == 1_700_000_000.0

    def test_numeric_string_treated_same_as_int(self):
        assert _parse_absolute_timestamp("1700000000") == 1_700_000_000.0

    def test_iso_8601_string(self):
        # 2025-01-01T00:00:00 UTC ≈ 1735689600
        out = _parse_absolute_timestamp("2025-01-01T00:00:00+00:00")
        assert out is not None
        assert int(out) == 1_735_689_600

    def test_zulu_suffix_normalised(self):
        out = _parse_absolute_timestamp("2025-01-01T00:00:00Z")
        assert out is not None

    def test_garbage_string_returns_none(self):
        assert _parse_absolute_timestamp("not a timestamp") is None


class TestNextPriority:
    def test_empty_list_returns_zero(self):
        assert _next_priority([]) == 0

    def test_returns_one_above_max_priority(self):
        # Build a minimal fake-ish entries list.
        class _FakeEntry:
            def __init__(self, priority):
                self.priority = priority

        entries = [_FakeEntry(0), _FakeEntry(5), _FakeEntry(3)]
        assert _next_priority(entries) == 6

    def test_negative_priorities_supported(self):
        class _FakeEntry:
            def __init__(self, priority):
                self.priority = priority

        # Helper falls back to -1 when entries is empty; with a single
        # entry at -10, next priority is -9.
        assert _next_priority([_FakeEntry(-10)]) == -9
