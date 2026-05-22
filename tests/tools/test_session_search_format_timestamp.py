"""Coverage for the pure timestamp helper inside
``tools.session_search_tool``."""
from __future__ import annotations

import re

import pytest

from tools.session_search_tool import _format_timestamp


_HUMAN_DATE_RE = re.compile(
    r"^[A-Za-z]+ \d{2}, \d{4} at \d{2}:\d{2} (AM|PM)$"
)


class TestFormatTimestamp:
    def test_none_returns_unknown(self):
        assert _format_timestamp(None) == "unknown"

    def test_int_epoch_renders_human_date(self):
        out = _format_timestamp(1_700_000_000)
        # The format string used is "%B %d, %Y at %I:%M %p".
        assert _HUMAN_DATE_RE.match(out), out

    def test_float_epoch_renders_human_date(self):
        out = _format_timestamp(1_700_000_000.5)
        assert _HUMAN_DATE_RE.match(out), out

    def test_numeric_string_treated_as_epoch(self):
        # The helper detects numeric-looking strings and converts them.
        out = _format_timestamp("1700000000")
        assert _HUMAN_DATE_RE.match(out), out

    def test_iso_string_passes_through(self):
        # Non-numeric strings (ISO-like) are returned as-is.
        out = _format_timestamp("2025-01-01T12:00:00Z")
        assert out == "2025-01-01T12:00:00Z"

    def test_garbage_string_returns_string(self):
        # Returns either the original string or the str(ts) fallback.
        out = _format_timestamp("not a date")
        assert isinstance(out, str) and "not a date" in out

    def test_overflow_value_does_not_crash(self):
        # An absurd epoch value triggers OverflowError on Linux; helper
        # swallows it and returns a safe fallback string.
        out = _format_timestamp(10**18)
        assert isinstance(out, str)
