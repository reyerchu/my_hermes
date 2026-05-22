"""Coverage for pure parsing helpers in
``plugins.teams_pipeline.subscriptions``."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from plugins.teams_pipeline.subscriptions import (
    _parse_bool,
    _parse_int,
    _parse_datetime,
    _utc_now,
    _utc_now_iso,
)


class TestParseBool:
    @pytest.mark.parametrize("value", [True, False])
    def test_passthrough_bool(self, value):
        assert _parse_bool(value) is value

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "YES", "on", "ON", "True"])
    def test_truthy_strings(self, value):
        assert _parse_bool(value) is True

    @pytest.mark.parametrize("value", ["0", "false", "False", "no", "NO", "off", "OFF"])
    def test_falsy_strings(self, value):
        assert _parse_bool(value) is False

    def test_padded_strings_stripped(self):
        assert _parse_bool("  true  ") is True
        assert _parse_bool("  false ") is False

    def test_unknown_string_returns_default(self):
        assert _parse_bool("maybe") is False
        assert _parse_bool("maybe", default=True) is True

    def test_none_returns_default(self):
        assert _parse_bool(None) is False
        assert _parse_bool(None, default=True) is True

    def test_int_returns_default(self):
        # Non-bool, non-str → default
        assert _parse_bool(1) is False
        assert _parse_bool(0, default=True) is True


class TestParseInt:
    def test_int_passthrough(self):
        assert _parse_int(42, default=0) == 42

    def test_numeric_string(self):
        assert _parse_int("100", default=0) == 100

    def test_none_returns_default(self):
        assert _parse_int(None, default=7) == 7

    def test_garbage_returns_default(self):
        assert _parse_int("abc", default=9) == 9

    def test_float_string_returns_default(self):
        # int("3.14") raises ValueError → default
        assert _parse_int("3.14", default=-1) == -1


class TestParseDatetime:
    def test_none_returns_none(self):
        assert _parse_datetime(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_datetime("") is None
        assert _parse_datetime("   ") is None

    def test_z_suffix_converted_to_utc(self):
        out = _parse_datetime("2026-05-22T12:00:00Z")
        assert out is not None
        assert out.tzinfo is not None
        assert out.utcoffset() == timedelta(0)
        assert out.year == 2026 and out.hour == 12

    def test_offset_string_normalized_to_utc(self):
        out = _parse_datetime("2026-05-22T12:00:00+08:00")
        assert out is not None
        # Normalized to UTC → 04:00 UTC.
        assert out.utcoffset() == timedelta(0)
        assert out.hour == 4

    def test_naive_datetime_assumed_utc(self):
        out = _parse_datetime("2026-05-22T12:00:00")
        assert out is not None
        assert out.tzinfo is not None
        assert out.utcoffset() == timedelta(0)


class TestUtcNowHelpers:
    def test_utc_now_returns_aware_datetime(self):
        now = _utc_now()
        assert now.tzinfo is not None
        assert now.utcoffset() == timedelta(0)

    def test_utc_now_iso_ends_with_z(self):
        out = _utc_now_iso()
        assert out.endswith("Z")
        # No microseconds (truncated by replace(microsecond=0))
        assert "." not in out

    def test_utc_now_iso_is_parseable(self):
        out = _utc_now_iso()
        # Should round-trip through _parse_datetime
        parsed = _parse_datetime(out)
        assert parsed is not None
        assert parsed.utcoffset() == timedelta(0)
