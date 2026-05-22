"""Coverage for gateway.platforms.helpers — shared adapter helpers."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from gateway.platforms.helpers import (
    MessageDeduplicator,
    ThreadParticipationTracker,
    redact_phone,
    strip_markdown,
)


class TestMessageDeduplicator:
    def test_first_seen_not_duplicate(self):
        d = MessageDeduplicator()
        assert d.is_duplicate("m1") is False

    def test_second_seen_is_duplicate(self):
        d = MessageDeduplicator()
        d.is_duplicate("m1")
        assert d.is_duplicate("m1") is True

    def test_empty_msg_id_not_duplicate(self):
        d = MessageDeduplicator()
        assert d.is_duplicate("") is False
        assert d.is_duplicate(None) is False  # type: ignore[arg-type]

    def test_ttl_expiry(self, monkeypatch):
        d = MessageDeduplicator(ttl_seconds=1.0)
        # Insert at t=0
        monkeypatch.setattr(time, "time", lambda: 100.0)
        assert d.is_duplicate("m") is False  # records
        # Same time → duplicate
        assert d.is_duplicate("m") is True
        # After TTL window → no longer duplicate (entry expired)
        monkeypatch.setattr(time, "time", lambda: 102.0)
        assert d.is_duplicate("m") is False  # treated as new and re-records

    def test_clear_resets(self):
        d = MessageDeduplicator()
        d.is_duplicate("m1")
        d.clear()
        assert d.is_duplicate("m1") is False

    def test_max_size_eviction_under_burst(self):
        # All entries within TTL, but cache > max_size → newest retained
        d = MessageDeduplicator(max_size=3, ttl_seconds=300)
        for i in range(10):
            d.is_duplicate(f"m{i}")
        # Internal _seen capped to max_size after eviction.
        # The latest 3 should be the survivors.
        assert "m9" in d._seen
        assert "m8" in d._seen
        assert len(d._seen) <= d._max_size + 1  # +1 for the latest insertion


class TestStripMarkdown:
    def test_strip_bold(self):
        assert strip_markdown("hello **world**") == "hello world"

    def test_strip_italic_star(self):
        assert strip_markdown("*emphasis*") == "emphasis"

    def test_strip_bold_underscore(self):
        assert strip_markdown("__bold__") == "bold"

    def test_strip_italic_underscore(self):
        assert strip_markdown("_em_") == "em"

    def test_strip_code_block(self):
        out = strip_markdown("```python\nprint('x')\n```")
        # Code block fences removed (the body remains as plain text).
        assert "```" not in out

    def test_strip_inline_code(self):
        assert strip_markdown("hello `world`") == "hello world"

    def test_strip_heading(self):
        out = strip_markdown("# Title\nbody")
        assert "Title" in out
        assert "# " not in out

    def test_strip_link_keeps_text(self):
        assert strip_markdown("[click](http://x)") == "click"

    def test_collapse_blank_runs(self):
        out = strip_markdown("a\n\n\n\nb")
        # Reduced to double-newline.
        assert out == "a\n\nb"

    def test_strip_whitespace(self):
        assert strip_markdown("   hello   ") == "hello"


class TestRedactPhone:
    def test_none_string(self):
        assert redact_phone("") == "<none>"

    def test_short_4_chars_or_less(self):
        # len <= 4 → "****"
        assert redact_phone("123") == "****"
        assert redact_phone("1234") == "****"

    def test_medium_5_to_8_chars(self):
        out = redact_phone("12345678")
        assert out.startswith("12")
        assert out.endswith("78")
        assert "****" in out

    def test_long_phone_keeps_country_and_last_4(self):
        out = redact_phone("+886912345678")
        assert out.startswith("+886")
        assert out.endswith("5678")
        assert "****" in out


class TestThreadParticipationTracker:
    @pytest.fixture
    def hermes_home(self, monkeypatch, tmp_path):
        import gateway.platforms.helpers as helpers
        from hermes_constants import get_hermes_home  # noqa: F401
        # Patch get_hermes_home referenced inside _state_path.
        monkeypatch.setattr(
            "hermes_constants.get_hermes_home", lambda: tmp_path
        )
        return tmp_path

    def test_starts_empty(self, hermes_home):
        t = ThreadParticipationTracker("test-plat")
        assert "anything" not in t

    def test_mark_persists(self, hermes_home):
        t = ThreadParticipationTracker("test-plat")
        t.mark("thr-1")
        # State file written on mark.
        path = hermes_home / "test-plat_threads.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "thr-1" in data

    def test_contains(self, hermes_home):
        t = ThreadParticipationTracker("test-plat")
        t.mark("thr-1")
        assert "thr-1" in t
        assert "thr-2" not in t

    def test_double_mark_idempotent(self, hermes_home):
        t = ThreadParticipationTracker("test-plat")
        t.mark("thr-1")
        t.mark("thr-1")
        data = json.loads((hermes_home / "test-plat_threads.json").read_text())
        assert data.count("thr-1") == 1

    def test_clear(self, hermes_home):
        t = ThreadParticipationTracker("test-plat")
        t.mark("thr-1")
        t.clear()
        assert "thr-1" not in t

    def test_load_existing_file(self, hermes_home):
        path = hermes_home / "test-plat_threads.json"
        path.write_text(json.dumps(["x", "y", "z"]), encoding="utf-8")
        t = ThreadParticipationTracker("test-plat")
        assert "x" in t and "y" in t and "z" in t

    def test_load_corrupt_file(self, hermes_home):
        path = hermes_home / "test-plat_threads.json"
        path.write_text("not json", encoding="utf-8")
        # Should not raise; start empty.
        t = ThreadParticipationTracker("test-plat")
        assert "x" not in t

    def test_max_tracked_truncation(self, hermes_home):
        t = ThreadParticipationTracker("test-plat", max_tracked=3)
        for i in range(5):
            t.mark(f"thr-{i}")
        # File should contain only the last 3 thread IDs.
        data = json.loads((hermes_home / "test-plat_threads.json").read_text())
        assert len(data) == 3
        # Most recent retained.
        assert "thr-4" in data
        assert "thr-3" in data
