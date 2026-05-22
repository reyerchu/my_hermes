"""Coverage for _list_recent_sessions in tools.session_search_tool."""
from __future__ import annotations

import json

import pytest

from tools.session_search_tool import _list_recent_sessions


class FakeDB:
    def __init__(self, sessions, parent_map=None):
        self.sessions = sessions
        self.parent_map = parent_map or {}

    def list_sessions_rich(self, limit, exclude_sources, order_by_last_active):
        return self.sessions[:limit]

    def get_session(self, sid):
        # Look up parent for lineage walk.
        for s in self.sessions:
            if s["id"] == sid:
                return {"parent_session_id": self.parent_map.get(sid)}
        return None


def _sess(sid, **overrides):
    base = {
        "id": sid,
        "title": f"title-{sid}",
        "source": "cli",
        "started_at": "2026-05-22T12:00:00Z",
        "last_active": "2026-05-22T13:00:00Z",
        "message_count": 5,
        "preview": "preview text",
    }
    base.update(overrides)
    return base


class TestListRecentSessions:
    def test_basic_list(self):
        db = FakeDB([_sess("a"), _sess("b"), _sess("c")])
        out = _list_recent_sessions(db, limit=10)
        data = json.loads(out)
        assert data["success"] is True
        assert data["mode"] == "recent"
        assert data["count"] == 3
        assert [r["session_id"] for r in data["results"]] == ["a", "b", "c"]

    def test_excludes_current_session(self):
        db = FakeDB([_sess("current"), _sess("other")])
        out = _list_recent_sessions(db, limit=10, current_session_id="current")
        data = json.loads(out)
        assert data["count"] == 1
        assert data["results"][0]["session_id"] == "other"

    def test_excludes_child_sessions(self):
        db = FakeDB([_sess("parent"), _sess("child", parent_session_id="parent")])
        out = _list_recent_sessions(db, limit=10)
        data = json.loads(out)
        # "child" has parent_session_id → excluded.
        assert [r["session_id"] for r in data["results"]] == ["parent"]

    def test_limit_applied(self):
        db = FakeDB([_sess(s) for s in ("a", "b", "c", "d", "e")])
        out = _list_recent_sessions(db, limit=2)
        data = json.loads(out)
        assert data["count"] == 2

    def test_lineage_walk_excludes_root(self):
        # current → parent → grandparent.
        db = FakeDB(
            [_sess("gp"), _sess("p"), _sess("c"), _sess("other")],
            parent_map={"c": "p", "p": "gp"},
        )
        out = _list_recent_sessions(db, limit=10, current_session_id="c")
        data = json.loads(out)
        # The grandparent (lineage root) should be excluded, "other" should remain.
        # "p" and "c" have parent_session_id so they're filtered as children.
        ids = [r["session_id"] for r in data["results"]]
        assert "gp" not in ids
        assert "other" in ids

    def test_db_exception_returns_error(self):
        class BoomDB:
            def list_sessions_rich(self, *a, **kw):
                raise RuntimeError("db down")
        out = _list_recent_sessions(BoomDB(), limit=5)
        data = json.loads(out)
        assert data["success"] is False

    def test_empty_db_returns_empty_results(self):
        db = FakeDB([])
        out = _list_recent_sessions(db, limit=10)
        data = json.loads(out)
        assert data["success"] is True
        assert data["count"] == 0
        assert data["results"] == []

    def test_lineage_walk_failure_does_not_crash(self):
        # get_session raises → falls back to current_session_id as root.
        class BadDB(FakeDB):
            def get_session(self, sid):
                raise RuntimeError("nope")
        db = BadDB([_sess("current"), _sess("other")])
        out = _list_recent_sessions(db, limit=10, current_session_id="current")
        data = json.loads(out)
        # current should still be excluded via fallback.
        assert all(r["session_id"] != "current" for r in data["results"])
