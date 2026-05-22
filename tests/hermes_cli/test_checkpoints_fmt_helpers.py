"""Coverage for the format helpers in ``hermes_cli.checkpoints``."""
from __future__ import annotations

import time
from datetime import datetime

from hermes_cli.checkpoints import _fmt_age, _fmt_bytes, _fmt_ts


class TestFmtBytes:
    def test_zero(self):
        assert _fmt_bytes(0) == "0 B"

    def test_small_bytes_returned_as_int(self):
        assert _fmt_bytes(512) == "512 B"

    def test_kilobytes(self):
        assert _fmt_bytes(1024) == "1.0 KB"
        assert _fmt_bytes(2048) == "2.0 KB"

    def test_megabytes(self):
        assert _fmt_bytes(1024 * 1024) == "1.0 MB"

    def test_gigabytes(self):
        assert _fmt_bytes(1024 ** 3) == "1.0 GB"

    def test_terabytes_clamps(self):
        # TB is the largest unit — anything bigger still renders as TB.
        size = 5 * 1024 ** 4
        out = _fmt_bytes(size)
        assert out.endswith("TB")

    def test_none_treated_as_zero(self):
        assert _fmt_bytes(None) == "0 B"  # type: ignore[arg-type]


class TestFmtTs:
    def test_valid_timestamp_renders_year_month_day(self):
        # 2024-06-15 00:00 UTC ≈ 1718409600 (timezone-dependent).
        out = _fmt_ts(1_718_409_600)
        # Best assertion: the output looks like "YYYY-MM-DD HH:MM".
        # Parse it back to verify the format.
        datetime.strptime(out, "%Y-%m-%d %H:%M")

    def test_invalid_input_returns_em_dash(self):
        assert _fmt_ts(None) == "—"
        assert _fmt_ts("not a number") == "—"


class TestFmtAge:
    def test_invalid_input_returns_em_dash(self):
        assert _fmt_age(None) == "—"
        assert _fmt_age("nope") == "—"

    def test_future_timestamp_returns_now(self):
        assert _fmt_age(time.time() + 1000) == "now"

    def test_under_minute_uses_seconds(self):
        now = time.time()
        assert _fmt_age(now - 30).endswith("s ago")

    def test_under_hour_uses_minutes(self):
        now = time.time()
        assert _fmt_age(now - 600).endswith("m ago")

    def test_under_day_uses_hours(self):
        now = time.time()
        assert _fmt_age(now - 7200).endswith("h ago")
