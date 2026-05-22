"""Coverage for pure helpers in gateway.platforms.qqbot.onboard."""
from __future__ import annotations

import pytest

from gateway.platforms.qqbot.onboard import (
    BindStatus,
    build_connect_url,
    _render_qr,
)


class TestBindStatusEnum:
    def test_values_pinned(self):
        assert BindStatus.NONE == 0
        assert BindStatus.PENDING == 1
        assert BindStatus.COMPLETED == 2
        assert BindStatus.EXPIRED == 3

    def test_all_distinct(self):
        assert len({BindStatus.NONE, BindStatus.PENDING,
                    BindStatus.COMPLETED, BindStatus.EXPIRED}) == 4


class TestBuildConnectUrl:
    def test_basic_task_id(self):
        out = build_connect_url("abc123")
        assert "task_id=abc123" in out
        assert out.startswith("https://q.qq.com/")

    def test_url_quoted_task_id(self):
        # Special chars should be URL-encoded.
        out = build_connect_url("a b")
        # quote() of "a b" is "a%20b"
        assert "task_id=a%20b" in out

    def test_special_chars_passed_through_quote(self):
        # quote() leaves "/" alone by default but encodes other reserved chars.
        out = build_connect_url("a?b")
        assert "task_id=a%3Fb" in out


class TestRenderQr:
    def test_returns_bool(self):
        out = _render_qr("https://x")
        # On a CI box without qrcode dep or stdout, returns False.
        assert isinstance(out, bool)

    def test_returns_false_when_qrcode_missing(self, monkeypatch):
        import gateway.platforms.qqbot.onboard as ob
        monkeypatch.setattr(ob, "_qrcode_mod", None)
        assert _render_qr("https://x") is False
