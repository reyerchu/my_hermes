"""Extended coverage for plugins.google_meet.process_manager —
enqueue_say + stop."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from plugins.google_meet import process_manager as pm


@pytest.fixture
def hermes_home(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "plugins.google_meet.process_manager.get_hermes_home",
        lambda: tmp_path,
    )
    return tmp_path


class TestEnqueueSay:
    def test_empty_text_rejected(self, hermes_home):
        out = pm.enqueue_say("")
        assert out["ok"] is False
        assert "required" in out["reason"]

    def test_whitespace_only_rejected(self, hermes_home):
        out = pm.enqueue_say("   ")
        assert out["ok"] is False

    def test_no_active(self, hermes_home):
        out = pm.enqueue_say("hello")
        assert out["ok"] is False
        assert "no active" in out["reason"]

    def test_transcribe_mode_rejected(self, hermes_home, tmp_path):
        out_dir = tmp_path / "m1"
        out_dir.mkdir()
        pm._write_active({
            "pid": 1, "meeting_id": "m1", "out_dir": str(out_dir),
            "mode": "transcribe",
        })
        out = pm.enqueue_say("hi")
        assert out["ok"] is False
        assert "realtime" in out["reason"]

    def test_missing_out_dir(self, hermes_home):
        pm._write_active({
            "pid": 1, "meeting_id": "m1",
            "out_dir": "/definitely/nope",
            "mode": "realtime",
        })
        out = pm.enqueue_say("hi")
        assert out["ok"] is False
        assert "out_dir missing" in out["reason"]

    def test_happy_path_writes_jsonl(self, hermes_home, tmp_path):
        out_dir = tmp_path / "m1"
        out_dir.mkdir()
        pm._write_active({
            "pid": 1, "meeting_id": "m1",
            "out_dir": str(out_dir),
            "mode": "realtime",
        })
        out = pm.enqueue_say("hello world")
        assert out["ok"] is True
        assert out["meetingId"] == "m1"
        assert len(out["enqueued_id"]) == 12
        queue = (out_dir / "say_queue.jsonl").read_text(encoding="utf-8")
        line = queue.strip().splitlines()[-1]
        entry = json.loads(line)
        assert entry["text"] == "hello world"
        assert "id" in entry

    def test_text_stripped(self, hermes_home, tmp_path):
        out_dir = tmp_path / "m1"
        out_dir.mkdir()
        pm._write_active({
            "pid": 1, "meeting_id": "m1",
            "out_dir": str(out_dir),
            "mode": "realtime",
        })
        pm.enqueue_say("  hello  ")
        queue = (out_dir / "say_queue.jsonl").read_text(encoding="utf-8")
        entry = json.loads(queue.strip().splitlines()[-1])
        assert entry["text"] == "hello"


class TestStop:
    def test_no_active(self, hermes_home):
        out = pm.stop()
        assert out["ok"] is False

    def test_dead_pid_returns_ok_and_clears(self, hermes_home, tmp_path):
        # No process at pid=999999 → cleanup goes through happy path.
        out_dir = tmp_path / "m1"
        out_dir.mkdir()
        pm._write_active({
            "pid": 0,  # 0 → never alive
            "meeting_id": "m1",
            "out_dir": str(out_dir),
        })
        out = pm.stop(reason="testing")
        assert out["ok"] is True
        assert out["reason"] == "testing"
        assert out["meetingId"] == "m1"
        # Active pointer cleared.
        assert pm._read_active() is None
        # Transcript path returned even if file doesn't exist.
        assert out["transcriptPath"].endswith("transcript.txt")
