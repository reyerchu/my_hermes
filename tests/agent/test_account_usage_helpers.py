"""Coverage for pure helpers in agent.account_usage."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.account_usage import (
    AccountUsageSnapshot,
    AccountUsageWindow,
    _title_case_slug,
    _parse_dt,
    _format_reset,
    _resolve_codex_usage_url,
    render_account_usage_lines,
)


class TestTitleCaseSlug:
    def test_basic(self):
        assert _title_case_slug("hello_world") == "Hello World"

    def test_hyphenated(self):
        assert _title_case_slug("the-quick-fox") == "The Quick Fox"

    def test_empty_returns_none(self):
        assert _title_case_slug("") is None
        assert _title_case_slug(None) is None
        assert _title_case_slug("  ") is None


class TestParseDt:
    def test_none(self):
        assert _parse_dt(None) is None

    def test_empty_string(self):
        assert _parse_dt("") is None
        assert _parse_dt("   ") is None

    def test_unix_int(self):
        out = _parse_dt(1000)
        assert out is not None
        assert out.tzinfo is not None

    def test_unix_float(self):
        out = _parse_dt(1779804000.5)
        assert out is not None

    def test_z_suffix(self):
        out = _parse_dt("2026-05-22T12:00:00Z")
        assert out is not None
        assert out.tzinfo is not None

    def test_offset_suffix(self):
        out = _parse_dt("2026-05-22T12:00:00+00:00")
        assert out is not None

    def test_naive_assumed_utc(self):
        out = _parse_dt("2026-05-22T12:00:00")
        assert out is not None
        assert out.tzinfo is not None

    def test_invalid_returns_none(self):
        assert _parse_dt("not a date") is None


class TestFormatReset:
    def test_none_unknown(self):
        assert _format_reset(None) == "unknown"

    def test_past_now(self):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        out = _format_reset(past)
        assert out.startswith("now")

    def test_within_hour(self):
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        out = _format_reset(future)
        assert "in 30m" in out or "in 29m" in out

    def test_hours_and_minutes(self):
        future = datetime.now(timezone.utc) + timedelta(hours=3, minutes=15)
        out = _format_reset(future)
        assert "in 3h" in out

    def test_days_and_hours(self):
        future = datetime.now(timezone.utc) + timedelta(days=2, hours=5)
        out = _format_reset(future)
        assert "in 2d" in out


class TestResolveCodexUsageUrl:
    def test_empty_uses_default(self):
        # Default is the backend-api/codex base, which gets the /wham/usage tail.
        out = _resolve_codex_usage_url("")
        assert out == "https://chatgpt.com/backend-api/wham/usage"

    def test_strips_trailing_slash(self):
        out = _resolve_codex_usage_url("https://api.example/")
        assert "/api/codex/usage" in out

    def test_strips_codex_suffix(self):
        out = _resolve_codex_usage_url("https://x/codex")
        assert out.endswith("/api/codex/usage")

    def test_backend_api_path(self):
        out = _resolve_codex_usage_url("https://x/backend-api")
        assert out == "https://x/backend-api/wham/usage"


class TestRenderAccountUsageLines:
    def test_none_returns_empty(self):
        assert render_account_usage_lines(None) == []

    def test_basic_render(self):
        snap = AccountUsageSnapshot(
            provider="openai",
            source="codex",
            fetched_at=datetime.now(timezone.utc),
            windows=(AccountUsageWindow(label="5h", used_percent=20.0),),
        )
        out = render_account_usage_lines(snap)
        assert "Account limits" in out[0]
        assert "Provider: openai" in out[1]
        # 100 - 20 = 80% remaining
        assert "80% remaining" in out[2]
        assert "(20% used)" in out[2]

    def test_markdown_bold(self):
        snap = AccountUsageSnapshot(
            provider="x", source="y", fetched_at=datetime.now(timezone.utc),
        )
        out = render_account_usage_lines(snap, markdown=True)
        assert "**Account limits**" in out[0]

    def test_unavailable_window(self):
        snap = AccountUsageSnapshot(
            provider="x", source="y", fetched_at=datetime.now(timezone.utc),
            windows=(AccountUsageWindow(label="weekly", used_percent=None),),
        )
        out = render_account_usage_lines(snap)
        assert "weekly: unavailable" in "\n".join(out)

    def test_plan_in_header(self):
        snap = AccountUsageSnapshot(
            provider="x", source="y", fetched_at=datetime.now(timezone.utc),
            plan="Pro",
        )
        out = render_account_usage_lines(snap)
        assert "Provider: x (Pro)" in out[1]

    def test_details_appended(self):
        snap = AccountUsageSnapshot(
            provider="x", source="y", fetched_at=datetime.now(timezone.utc),
            details=("Note 1", "Note 2"),
        )
        out = render_account_usage_lines(snap)
        assert "Note 1" in out
        assert "Note 2" in out

    def test_unavailable_reason_with_window(self):
        # An unavailable_reason combined with at least one window/detail
        # appends an "Unavailable:" line.
        snap = AccountUsageSnapshot(
            provider="x", source="y", fetched_at=datetime.now(timezone.utc),
            windows=(AccountUsageWindow(label="5h", used_percent=10.0),),
            unavailable_reason="auth required",
        )
        out = render_account_usage_lines(snap)
        assert any("Unavailable: auth required" in line for line in out)
