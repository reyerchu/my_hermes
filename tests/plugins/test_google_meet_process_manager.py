"""Coverage for plugins.google_meet.process_manager — state file
helpers and status/transcript public API."""
from __future__ import annotations

import json
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


class TestRootAndActiveFile:
    def test_root_under_workspace_meetings(self, hermes_home):
        out = pm._root()
        assert out == hermes_home / "workspace" / "meetings"

    def test_active_file_under_root(self, hermes_home):
        out = pm._active_file()
        assert out.name == ".active.json"
        assert out.parent == pm._root()


class TestReadWriteActive:
    def test_missing_returns_none(self, hermes_home):
        assert pm._read_active() is None

    def test_write_then_read(self, hermes_home):
        pm._write_active({"pid": 1, "meeting_id": "m1"})
        out = pm._read_active()
        assert out == {"pid": 1, "meeting_id": "m1"}

    def test_write_creates_parent(self, hermes_home):
        pm._write_active({"pid": 1})
        assert (hermes_home / "workspace" / "meetings").is_dir()

    def test_corrupt_file_returns_none(self, hermes_home):
        path = pm._active_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not json", encoding="utf-8")
        assert pm._read_active() is None


class TestClearActive:
    def test_idempotent(self, hermes_home):
        # No file → no crash
        pm._clear_active()

    def test_clears_existing(self, hermes_home):
        pm._write_active({"pid": 1})
        pm._clear_active()
        assert pm._read_active() is None


class TestPidAlive:
    def test_alive_for_current_process(self):
        import os
        # The current PID is always alive.
        assert pm._pid_alive(os.getpid()) is True

    def test_dead_for_zero(self):
        # PID 0 is special — gateway.status._pid_exists must return False.
        assert pm._pid_alive(0) is False


class TestStatus:
    def test_no_active(self, hermes_home):
        out = pm.status()
        assert out["ok"] is False
        assert out["reason"] == "no active meeting"

    def test_active_alive(self, hermes_home, tmp_path):
        import os
        out_dir = tmp_path / "meet1"
        out_dir.mkdir()
        # Write a stub status.json for the bot
        (out_dir / "status.json").write_text(
            json.dumps({"phase": "joined"}), encoding="utf-8"
        )
        pm._write_active({
            "pid": os.getpid(),
            "meeting_id": "m1",
            "url": "https://meet.example/x",
            "started_at": 1.0,
            "out_dir": str(out_dir),
        })
        out = pm.status()
        assert out["ok"] is True
        assert out["alive"] is True
        assert out["meetingId"] == "m1"
        assert out["url"] == "https://meet.example/x"
        assert out["phase"] == "joined"  # merged in from bot_status

    def test_active_corrupt_status(self, hermes_home, tmp_path):
        import os
        out_dir = tmp_path / "meet1"
        out_dir.mkdir()
        (out_dir / "status.json").write_text("not json", encoding="utf-8")
        pm._write_active({
            "pid": os.getpid(),
            "meeting_id": "m1",
            "out_dir": str(out_dir),
        })
        out = pm.status()
        assert out["ok"] is True  # doesn't crash on bad JSON
        assert out["alive"] is True


class TestTranscript:
    def test_no_active(self, hermes_home):
        out = pm.transcript()
        assert out["ok"] is False

    def test_no_transcript_file(self, hermes_home, tmp_path):
        out_dir = tmp_path / "meet1"
        out_dir.mkdir()
        pm._write_active({"meeting_id": "m1", "out_dir": str(out_dir)})
        out = pm.transcript()
        assert out["ok"] is True
        assert out["lines"] == []
        assert out["total"] == 0

    def test_with_transcript(self, hermes_home, tmp_path):
        out_dir = tmp_path / "meet1"
        out_dir.mkdir()
        (out_dir / "transcript.txt").write_text(
            "line A\nline B\n\nline C\n",
            encoding="utf-8",
        )
        pm._write_active({"meeting_id": "m1", "out_dir": str(out_dir)})
        out = pm.transcript()
        assert out["ok"] is True
        assert out["lines"] == ["line A", "line B", "line C"]
        assert out["total"] == 3

    def test_last_n_lines(self, hermes_home, tmp_path):
        out_dir = tmp_path / "meet1"
        out_dir.mkdir()
        (out_dir / "transcript.txt").write_text(
            "a\nb\nc\nd\ne\n",
            encoding="utf-8",
        )
        pm._write_active({"meeting_id": "m1", "out_dir": str(out_dir)})
        out = pm.transcript(last=2)
        # Total still 5, but only last 2 returned.
        assert out["lines"] == ["d", "e"]
        assert out["total"] == 5


class TestEnqueueSay:
    def test_empty_text(self, hermes_home):
        out = pm.enqueue_say("")
        assert out["ok"] is False
        assert "required" in out["reason"]

    def test_no_active(self, hermes_home):
        out = pm.enqueue_say("hello")
        assert out["ok"] is False
