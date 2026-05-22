"""Coverage for optional-skills/devops/watchers/scripts/_watermark.py."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


# The script lives under a hyphenated path (optional-skills/) so it
# can't be imported with the regular import machinery. Load it directly
# via importlib.util.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_MOD_PATH = _REPO_ROOT / "optional-skills" / "devops" / "watchers" / "scripts" / "_watermark.py"
_SPEC = importlib.util.spec_from_file_location("_watermark_mod", _MOD_PATH)
_mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_mod)

Watermark = _mod.Watermark
format_items_as_markdown = _mod.format_items_as_markdown


@pytest.fixture
def tmp_state(monkeypatch, tmp_path):
    monkeypatch.setenv("WATCHER_STATE_DIR", str(tmp_path))
    return tmp_path


class TestWatermarkInit:
    def test_default_name_alphanumeric(self):
        wm = Watermark("my-feed_2")
        assert wm.name == "my-feed_2"

    def test_invalid_name_rejected(self):
        with pytest.raises(ValueError, match="alphanumeric"):
            Watermark("bad name!")

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError):
            Watermark("")


class TestWatermarkLoad:
    def test_load_when_no_file_is_first_run(self, tmp_state):
        wm = Watermark.load("feed1")
        assert wm.is_first_run is True
        assert wm.seen == []

    def test_load_existing_file_clears_first_run(self, tmp_state):
        path = tmp_state / "feed1.json"
        path.write_text(json.dumps({"seen_ids": ["a", "b"]}), encoding="utf-8")
        wm = Watermark.load("feed1")
        assert wm.is_first_run is False
        assert sorted(wm.seen) == ["a", "b"]

    def test_corrupt_file_falls_back_to_first_run(self, tmp_state):
        path = tmp_state / "feed1.json"
        path.write_text("not json {{{", encoding="utf-8")
        wm = Watermark.load("feed1")
        assert wm.is_first_run is True


class TestFilterNew:
    def test_first_run_records_but_emits_nothing(self, tmp_state):
        wm = Watermark.load("feed")
        items = [{"id": "1"}, {"id": "2"}]
        out = wm.filter_new(items)
        assert out == []
        assert sorted(wm.seen) == ["1", "2"]
        assert wm.is_first_run is False  # set after filter_new()

    def test_subsequent_run_emits_new_items_only(self, tmp_state):
        path = tmp_state / "feed.json"
        path.write_text(json.dumps({"seen_ids": ["1"], "first_run": False}), encoding="utf-8")
        wm = Watermark.load("feed")
        out = wm.filter_new([{"id": "1"}, {"id": "2"}])
        assert [it["id"] for it in out] == ["2"]
        assert sorted(wm.seen) == ["1", "2"]

    def test_items_without_id_skipped(self, tmp_state):
        wm = Watermark.load("feed")
        wm._data["first_run"] = False  # simulate not-first-run
        out = wm.filter_new([{"id": "1"}, {"no_id": True}])
        assert [it["id"] for it in out] == ["1"]

    def test_custom_id_key(self, tmp_state):
        wm = Watermark.load("feed")
        wm._data["first_run"] = False
        out = wm.filter_new([{"slug": "x"}, {"slug": "y"}], id_key="slug")
        assert {it["slug"] for it in out} == {"x", "y"}

    def test_max_seen_truncates_to_capacity(self, tmp_state):
        wm = Watermark("feed", max_seen=3)
        wm._data["first_run"] = False
        wm._data["seen_ids"] = ["1", "2", "3"]
        wm.filter_new([{"id": "4"}, {"id": "5"}])
        # Truncated to max_seen size; new IDs are appended last so they
        # are guaranteed to be present after truncation.
        assert len(wm.seen) == 3
        assert "4" in wm.seen
        assert "5" in wm.seen


class TestSave:
    def test_round_trip(self, tmp_state):
        wm = Watermark.load("feed")
        wm._data["first_run"] = False
        wm.filter_new([{"id": "a"}])
        wm.save()
        # Reload and check.
        reloaded = Watermark.load("feed")
        assert "a" in reloaded.seen
        assert reloaded.is_first_run is False

    def test_atomic_no_tmp_file_left_behind(self, tmp_state):
        wm = Watermark.load("feed")
        wm.save()
        assert not (tmp_state / "feed.tmp").exists()
        assert (tmp_state / "feed.json").exists()


class TestFormatItemsAsMarkdown:
    def test_empty_returns_empty_string(self):
        assert format_items_as_markdown([]) == ""

    def test_single_item_with_url(self):
        out = format_items_as_markdown([{"title": "T1", "url": "https://x"}])
        assert "## T1" in out
        assert "https://x" in out
        assert out.endswith("\n")

    def test_missing_title_uses_no_title(self):
        out = format_items_as_markdown([{"url": "https://x"}])
        assert "(no title)" in out

    def test_body_truncated_at_max_chars(self):
        long_body = "x" * 1000
        out = format_items_as_markdown(
            [{"title": "T", "url": "u", "body": long_body}],
            body_key="body",
            max_body_chars=50,
        )
        # 50-char body + ellipsis
        assert "…" in out
        # The truncated body should be in the output.
        assert "x" * 50 in out

    def test_body_only_added_when_body_key_given(self):
        out = format_items_as_markdown(
            [{"title": "T", "url": "u", "body": "hello"}],
        )
        assert "hello" not in out

    def test_url_omitted_when_blank(self):
        out = format_items_as_markdown([{"title": "T", "url": ""}])
        # No URL line printed.
        assert "## T" in out
        # Body should not contain blank "" line treated as URL.
