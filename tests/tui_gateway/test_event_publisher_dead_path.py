"""Coverage for ``tui_gateway.event_publisher.WsPublisherTransport`` in
its "dead" code paths (no websockets / connect failure).  We don't
exercise the live websocket — that needs a real dashboard."""
from __future__ import annotations

from unittest.mock import patch

import pytest


def _import_module():
    import tui_gateway.event_publisher as mod
    return mod


class TestWsPublisherTransportNoWebsockets:
    def test_marks_dead_when_ws_connect_unavailable(self):
        mod = _import_module()
        with patch("tui_gateway.event_publisher.ws_connect", None):
            t = mod.WsPublisherTransport("ws://example/x")
        assert t._dead is True
        # No worker thread was started.
        assert t._worker is None

    def test_write_returns_false_when_dead(self):
        mod = _import_module()
        with patch("tui_gateway.event_publisher.ws_connect", None):
            t = mod.WsPublisherTransport("ws://example/x")
        assert t.write({"type": "x"}) is False

    def test_close_safe_when_dead(self):
        mod = _import_module()
        with patch("tui_gateway.event_publisher.ws_connect", None):
            t = mod.WsPublisherTransport("ws://example/x")
        # Close must be a no-op safe.
        t.close()
        # Idempotent — second close also fine.
        t.close()


class TestWsPublisherTransportConnectError:
    def test_marks_dead_when_connect_raises(self):
        mod = _import_module()
        def boom(*args, **kwargs):
            raise OSError("simulated connect failure")
        with patch("tui_gateway.event_publisher.ws_connect", boom):
            t = mod.WsPublisherTransport("ws://example/x", connect_timeout=0.1)
        assert t._dead is True
        assert t._ws is None
        assert t.write({"type": "x"}) is False
