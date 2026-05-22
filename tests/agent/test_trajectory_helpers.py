"""Pure-function coverage for ``agent.trajectory``.

The module also has a file-writing ``save_trajectory`` helper which the
batch_runner consumes; the tests below cover both the text-rewrite
helpers and that file appender.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from agent.trajectory import (
    convert_scratchpad_to_think,
    has_incomplete_scratchpad,
    save_trajectory,
)


class TestConvertScratchpadToThink:
    def test_empty_string_unchanged(self):
        assert convert_scratchpad_to_think("") == ""

    def test_no_tags_returns_input_unchanged(self):
        assert convert_scratchpad_to_think("just text") == "just text"

    def test_paired_tags_rewritten(self):
        text = "<REASONING_SCRATCHPAD>plan</REASONING_SCRATCHPAD>"
        assert convert_scratchpad_to_think(text) == "<think>plan</think>"

    def test_multiple_pairs_all_rewritten(self):
        text = (
            "<REASONING_SCRATCHPAD>a</REASONING_SCRATCHPAD>"
            "<REASONING_SCRATCHPAD>b</REASONING_SCRATCHPAD>"
        )
        assert convert_scratchpad_to_think(text) == (
            "<think>a</think><think>b</think>"
        )

    def test_unpaired_open_tag_still_rewritten(self):
        # The function replaces tag occurrences, so a dangling open tag
        # becomes a dangling <think> open tag.  This is the documented
        # behaviour — completeness is enforced by has_incomplete_scratchpad.
        text = "<REASONING_SCRATCHPAD>not closed"
        assert convert_scratchpad_to_think(text) == "<think>not closed"

    def test_unpaired_close_tag_alone_is_left_untouched(self):
        # The guard requires the OPEN tag before any rewrite runs, so a
        # stray close tag passes through unchanged.
        text = "no open</REASONING_SCRATCHPAD>"
        assert convert_scratchpad_to_think(text) == text

    def test_surrounding_content_preserved(self):
        text = (
            "before <REASONING_SCRATCHPAD>middle</REASONING_SCRATCHPAD> after"
        )
        assert convert_scratchpad_to_think(text) == (
            "before <think>middle</think> after"
        )


class TestHasIncompleteScratchpad:
    def test_empty_input_is_complete(self):
        assert has_incomplete_scratchpad("") is False

    def test_plain_text_is_complete(self):
        assert has_incomplete_scratchpad("just text") is False

    def test_paired_tags_are_complete(self):
        assert (
            has_incomplete_scratchpad(
                "<REASONING_SCRATCHPAD>x</REASONING_SCRATCHPAD>"
            )
            is False
        )

    def test_open_without_close_is_incomplete(self):
        assert (
            has_incomplete_scratchpad("<REASONING_SCRATCHPAD>partial")
            is True
        )

    def test_close_without_open_is_complete_by_definition(self):
        # The predicate only fires on a dangling OPEN tag — a stray close
        # is treated as "no scratchpad in flight here".
        assert (
            has_incomplete_scratchpad("</REASONING_SCRATCHPAD>") is False
        )

    def test_multiple_opens_with_matching_closes_complete(self):
        text = (
            "<REASONING_SCRATCHPAD>a</REASONING_SCRATCHPAD>"
            " then "
            "<REASONING_SCRATCHPAD>b</REASONING_SCRATCHPAD>"
        )
        assert has_incomplete_scratchpad(text) is False

    def test_text_with_only_open_tag_anywhere_is_incomplete(self):
        assert (
            has_incomplete_scratchpad(
                "intro <REASONING_SCRATCHPAD> trailing without close"
            )
            is True
        )


class TestSaveTrajectory:
    def test_writes_to_default_completed_filename(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        save_trajectory([{"role": "user"}], "test-model", completed=True)
        out = Path("trajectory_samples.jsonl")
        assert out.exists()
        lines = out.read_text(encoding="utf-8").strip().split("\n")
        entry = json.loads(lines[0])
        assert entry["model"] == "test-model"
        assert entry["completed"] is True
        assert entry["conversations"] == [{"role": "user"}]
        assert isinstance(entry["timestamp"], str)

    def test_writes_to_failed_filename_when_not_completed(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        save_trajectory([], "m", completed=False)
        assert Path("failed_trajectories.jsonl").exists()
        assert not Path("trajectory_samples.jsonl").exists()

    def test_appends_to_existing_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        save_trajectory([{"role": "user", "content": "a"}], "m", completed=True)
        save_trajectory([{"role": "user", "content": "b"}], "m", completed=True)
        out = Path("trajectory_samples.jsonl")
        lines = out.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["conversations"][0]["content"] == "a"
        assert json.loads(lines[1])["conversations"][0]["content"] == "b"

    def test_honours_explicit_filename(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        save_trajectory([], "m", completed=True, filename="custom.jsonl")
        assert Path("custom.jsonl").exists()
        assert not Path("trajectory_samples.jsonl").exists()

    def test_failure_to_write_is_logged_not_raised(self, tmp_path, monkeypatch):
        # A directory in the place of a file makes open(..., "a") raise.
        monkeypatch.chdir(tmp_path)
        os.mkdir(tmp_path / "trajectory_samples.jsonl")
        # Should not raise — the helper swallows the OSError.
        save_trajectory([{"role": "user"}], "m", completed=True)
        # Original placeholder directory survives.
        assert (tmp_path / "trajectory_samples.jsonl").is_dir()

    def test_non_ascii_content_preserved(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        save_trajectory(
            [{"role": "user", "content": "你好，世界 🌏"}],
            "m",
            completed=True,
        )
        text = Path("trajectory_samples.jsonl").read_text(encoding="utf-8")
        assert "你好，世界 🌏" in text
