"""Coverage for pure helpers in plugins.google_meet.meet_bot.

Avoids importing run_bot() which pulls in playwright. We import only the
small pure helpers via direct module attr access."""
from __future__ import annotations

import pytest

# Skip the entire module if playwright (which meet_bot imports) is missing.
pytest.importorskip("playwright")

from plugins.google_meet.meet_bot import (  # noqa: E402
    _is_safe_meet_url,
    _meeting_id_from_url,
    _looks_like_human_speaker,
    _parse_duration,
)


class TestIsSafeMeetUrl:
    @pytest.mark.parametrize("url", [
        "https://meet.google.com/abc-defg-hij",
        "https://meet.google.com/abc-defg-hij?authuser=0",
        "https://meet.google.com/new",
        "https://meet.google.com/lookup/abc",
    ])
    def test_accepts_valid_urls(self, url):
        assert _is_safe_meet_url(url) is True

    @pytest.mark.parametrize("url", [
        "http://meet.google.com/abc-defg-hij",       # http (not https)
        "https://meet.evil.com/abc-defg-hij",        # wrong host
        "https://meet.google.com.evil.com/abc-d-h",  # subdomain trick
        "https://meet.google.com/",                  # no code
        "  ",                                        # blank
    ])
    def test_rejects_invalid_urls(self, url):
        assert _is_safe_meet_url(url) is False

    def test_non_string(self):
        assert _is_safe_meet_url(None) is False  # type: ignore[arg-type]
        assert _is_safe_meet_url(42) is False  # type: ignore[arg-type]


class TestMeetingIdFromUrl:
    def test_extracts_three_segment_code(self):
        assert _meeting_id_from_url("https://meet.google.com/abc-defg-hij") == "abc-defg-hij"

    def test_ignores_trailing_path(self):
        out = _meeting_id_from_url("https://meet.google.com/abc-defg-hij/extra?x=y")
        assert out == "abc-defg-hij"

    def test_fallback_for_unknown_url(self):
        out = _meeting_id_from_url("https://meet.google.com/new")
        assert out.startswith("meet-")

    def test_fallback_for_empty(self):
        out = _meeting_id_from_url("")
        assert out.startswith("meet-")

    def test_fallback_for_none(self):
        out = _meeting_id_from_url(None)  # type: ignore[arg-type]
        assert out.startswith("meet-")


class TestLooksLikeHumanSpeaker:
    def test_real_name_is_human(self):
        assert _looks_like_human_speaker("Alice", "Hermes Bot") is True

    def test_blank_is_not_human(self):
        assert _looks_like_human_speaker("", "Hermes Bot") is False
        assert _looks_like_human_speaker("   ", "Hermes Bot") is False

    def test_unknown_label_not_human(self):
        assert _looks_like_human_speaker("unknown", "Hermes") is False
        assert _looks_like_human_speaker("Unknown", "Hermes") is False

    def test_you_not_human(self):
        # Meet sometimes attributes captions to "You".
        assert _looks_like_human_speaker("You", "Hermes") is False

    def test_bot_name_not_human(self):
        # Bot's own captions don't count.
        assert _looks_like_human_speaker("Hermes Bot", "Hermes Bot") is False

    def test_case_insensitive(self):
        assert _looks_like_human_speaker("HERMES BOT", "hermes bot") is False


class TestParseDuration:
    def test_hours(self):
        assert _parse_duration("2h") == 7200.0

    def test_minutes(self):
        assert _parse_duration("30m") == 1800.0

    def test_seconds_suffix(self):
        assert _parse_duration("45s") == 45.0

    def test_bare_number_is_seconds(self):
        assert _parse_duration("90") == 90.0

    def test_float_values(self):
        assert _parse_duration("0.5h") == 1800.0

    def test_blank_returns_none(self):
        assert _parse_duration("") is None
        assert _parse_duration(None) is None  # type: ignore[arg-type]

    def test_garbage_returns_none(self):
        assert _parse_duration("not-a-number") is None
        assert _parse_duration("xh") is None

    def test_whitespace_stripped(self):
        assert _parse_duration("  30m  ") == 1800.0
