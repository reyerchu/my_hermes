"""Coverage for pure helpers in tools.session_search_tool."""
from __future__ import annotations

import pytest

from tools.session_search_tool import (
    _format_timestamp,
    _format_conversation,
    _truncate_around_matches,
    _get_session_search_max_concurrency,
)


class TestFormatTimestamp:
    def test_none_returns_unknown(self):
        assert _format_timestamp(None) == "unknown"

    def test_unix_int(self):
        # 2026-05-22 12:00:00 UTC = 1779804000 (approx).  Just check
        # the formatted result contains a year and time fragment.
        out = _format_timestamp(1779804000)
        assert "2026" in out
        assert ("AM" in out) or ("PM" in out)

    def test_unix_float(self):
        out = _format_timestamp(1779804000.5)
        assert "2026" in out

    def test_iso_string_passthrough(self):
        # Non-numeric strings are returned as-is.
        assert _format_timestamp("2026-05-22T12:00:00Z") == "2026-05-22T12:00:00Z"

    def test_numeric_string(self):
        out = _format_timestamp("1779804000")
        assert "2026" in out

    def test_invalid_passthrough(self):
        # OverflowError, OSError etc. → fall back to str(ts).
        out = _format_timestamp(99999999999999999999)
        assert out  # at minimum, returns some string


class TestFormatConversation:
    def test_empty(self):
        assert _format_conversation([]) == ""

    def test_user_message(self):
        out = _format_conversation([{"role": "user", "content": "hi"}])
        assert out == "[USER]: hi"

    def test_assistant_plain(self):
        out = _format_conversation([{"role": "assistant", "content": "yes"}])
        assert out == "[ASSISTANT]: yes"

    def test_assistant_with_tool_calls(self):
        out = _format_conversation([
            {
                "role": "assistant",
                "content": "thinking...",
                "tool_calls": [
                    {"name": "read"},
                    {"function": {"name": "write"}},
                ],
            }
        ])
        # Both call names plus the visible content.
        assert "[Called: read, write]" in out
        assert "thinking..." in out

    def test_assistant_tool_calls_only(self):
        out = _format_conversation([
            {"role": "assistant", "content": "", "tool_calls": [{"name": "ls"}]}
        ])
        assert "[Called: ls]" in out

    def test_tool_message(self):
        out = _format_conversation([
            {"role": "tool", "tool_name": "read", "content": "hello"},
        ])
        assert out == "[TOOL:read]: hello"

    def test_tool_message_truncated(self):
        long = "x" * 1000
        out = _format_conversation([
            {"role": "tool", "tool_name": "ls", "content": long},
        ])
        assert "[truncated]" in out
        # Head + tail preserved
        assert out.startswith("[TOOL:ls]: " + "x" * 250)
        assert out.endswith("x" * 250)

    def test_unknown_role(self):
        out = _format_conversation([{"role": "system", "content": "sys"}])
        assert out == "[SYSTEM]: sys"


class TestTruncateAroundMatches:
    def test_short_text_returns_full(self):
        out = _truncate_around_matches("hello world", "world", max_chars=100)
        assert out == "hello world"

    def test_phrase_match_centered(self):
        text = "a" * 2000 + " QUERY " + "b" * 2000
        out = _truncate_around_matches(text, "QUERY", max_chars=500)
        # The window must include the phrase.
        assert "QUERY" in out
        # Truncation markers added
        assert "truncated" in out

    def test_no_match_returns_prefix(self):
        text = "z" * 5000
        out = _truncate_around_matches(text, "nonexistent", max_chars=500)
        # Falls back to start with truncated suffix.
        # Output should be (max_chars + suffix) long, not full text.
        assert len(out) < len(text)
        assert out.startswith("z")
        assert "truncated" in out

    def test_individual_terms_fallback(self):
        # Multi-term query, only individual terms appear far apart.
        text = "foo " + "x" * 2000 + " bar"
        out = _truncate_around_matches(text, "foo bar", max_chars=500)
        # Should include at least one match.
        assert "foo" in out or "bar" in out


class TestMaxConcurrency:
    def test_default_when_config_missing(self, monkeypatch):
        import sys
        # Make hermes_cli.config.load_config raise ImportError by removing
        # it from sys.modules and shadowing it.
        monkeypatch.setitem(sys.modules, "hermes_cli.config", None)
        assert _get_session_search_max_concurrency(default=3) == 3

    def test_clamp_low(self, monkeypatch):
        # Mock load_config to return 0 → clamped up to 1.
        import sys
        import types
        fake = types.ModuleType("hermes_cli.config")
        fake.load_config = lambda: {"auxiliary": {"session_search": {"max_concurrency": 0}}}
        monkeypatch.setitem(sys.modules, "hermes_cli.config", fake)
        assert _get_session_search_max_concurrency(default=3) == 1

    def test_clamp_high(self, monkeypatch):
        import sys
        import types
        fake = types.ModuleType("hermes_cli.config")
        fake.load_config = lambda: {"auxiliary": {"session_search": {"max_concurrency": 100}}}
        monkeypatch.setitem(sys.modules, "hermes_cli.config", fake)
        assert _get_session_search_max_concurrency(default=3) == 5

    def test_garbage_falls_back(self, monkeypatch):
        import sys
        import types
        fake = types.ModuleType("hermes_cli.config")
        fake.load_config = lambda: {"auxiliary": {"session_search": {"max_concurrency": "bad"}}}
        monkeypatch.setitem(sys.modules, "hermes_cli.config", fake)
        assert _get_session_search_max_concurrency(default=3) == 3

    def test_normal_value(self, monkeypatch):
        import sys
        import types
        fake = types.ModuleType("hermes_cli.config")
        fake.load_config = lambda: {"auxiliary": {"session_search": {"max_concurrency": 2}}}
        monkeypatch.setitem(sys.modules, "hermes_cli.config", fake)
        assert _get_session_search_max_concurrency(default=3) == 2
