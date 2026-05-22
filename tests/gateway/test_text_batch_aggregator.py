"""Coverage for TextBatchAggregator in gateway.platforms.helpers.

We only test the synchronous surface (is_enabled, enqueue concat,
cancel_all). The async _flush behaviour is covered via the existing
adapter-level integration tests."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
import pytest_asyncio

from gateway.platforms.helpers import TextBatchAggregator


def _make_event(text: str):
    return SimpleNamespace(text=text)


class TestSynchronous:
    def test_is_enabled_with_default_delay(self):
        agg = TextBatchAggregator(handler=lambda e: None)
        assert agg.is_enabled() is True

    def test_is_enabled_false_when_delay_zero(self):
        agg = TextBatchAggregator(handler=lambda e: None, batch_delay=0)
        assert agg.is_enabled() is False

    def test_cancel_all_clears_state(self):
        agg = TextBatchAggregator(handler=lambda e: None)
        # Directly inject pending state to exercise the clear logic.
        agg._pending["k"] = _make_event("x")
        agg.cancel_all()
        assert agg._pending == {}
        assert agg._pending_tasks == {}


@pytest.mark.asyncio
async def test_enqueue_first_event_starts_task():
    agg = TextBatchAggregator(
        handler=lambda e: None,
        batch_delay=10,  # large delay so it doesn't fire during test
    )
    agg.enqueue(_make_event("hello"), "user1")
    assert "user1" in agg._pending
    assert "user1" in agg._pending_tasks
    # Clean up.
    agg.cancel_all()


@pytest.mark.asyncio
async def test_enqueue_second_event_concatenates():
    agg = TextBatchAggregator(handler=lambda e: None, batch_delay=10)
    agg.enqueue(_make_event("hello"), "user1")
    agg.enqueue(_make_event("world"), "user1")
    assert agg._pending["user1"].text == "hello\nworld"
    agg.cancel_all()


@pytest.mark.asyncio
async def test_flush_dispatches_handler():
    received = []

    async def handler(evt):
        received.append(evt.text)

    agg = TextBatchAggregator(handler=handler, batch_delay=0.05)
    agg.enqueue(_make_event("hi"), "user1")
    await asyncio.sleep(0.1)
    assert received == ["hi"]


@pytest.mark.asyncio
async def test_flush_handler_exception_swallowed():
    async def handler(evt):
        raise RuntimeError("boom")

    agg = TextBatchAggregator(handler=handler, batch_delay=0.05)
    agg.enqueue(_make_event("hi"), "user1")
    # Should not propagate the exception.
    await asyncio.sleep(0.1)
    # State cleaned up.
    assert "user1" not in agg._pending


@pytest.mark.asyncio
async def test_long_chunk_uses_split_delay():
    received = []

    async def handler(evt):
        received.append(evt.text)

    # batch_delay=0.05 but split_delay=0.3; split_threshold=10 so
    # 20-char event triggers the split branch.
    agg = TextBatchAggregator(
        handler=handler,
        batch_delay=0.05,
        split_delay=0.3,
        split_threshold=10,
    )
    agg.enqueue(_make_event("x" * 20), "user1")
    # After 0.1s the regular batch_delay hasn't fired due to long chunk.
    await asyncio.sleep(0.1)
    assert received == []
    # After enough additional time it should fire.
    await asyncio.sleep(0.3)
    assert received == ["x" * 20]
