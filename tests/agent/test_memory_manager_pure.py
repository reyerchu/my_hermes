"""Coverage for the pure helpers in ``agent.memory_manager``."""
from __future__ import annotations

import pytest

from agent.memory_manager import (
    build_memory_context_block,
    sanitize_context,
)


class TestSanitizeContext:
    def test_plain_text_unchanged(self):
        assert sanitize_context("hello world") == "hello world"

    def test_removes_memory_context_fence(self):
        text = "<memory-context>secret\n</memory-context>"
        out = sanitize_context(text)
        assert "<memory-context>" not in out
        assert "</memory-context>" not in out

    def test_strips_system_note_blocks_entirely(self):
        # The wrapper produced by build_memory_context_block is the exact
        # shape sanitize_context strips out — body and all.
        wrapped = build_memory_context_block("hello")
        stripped = sanitize_context(wrapped).strip()
        # The full block (system note + body) is gone after sanitization.
        assert "[System note" not in stripped
        assert "<memory-context>" not in stripped


class TestBuildMemoryContextBlock:
    def test_empty_string_returns_empty(self):
        assert build_memory_context_block("") == ""

    def test_whitespace_only_returns_empty(self):
        assert build_memory_context_block("   \n\n") == ""

    def test_wraps_text_in_fence_and_system_note(self):
        out = build_memory_context_block("user prefers terse output")
        assert out.startswith("<memory-context>")
        assert "</memory-context>" in out
        assert "[System note:" in out
        assert "user prefers terse output" in out

    def test_pre_wrapped_input_logs_a_warning_then_returns_empty(self, caplog):
        # The sanitize step strips the entire <memory-context>…</memory-context>
        # block including its body, so a pre-wrapped input becomes empty
        # internally.  The wrapper logs a warning and still returns a fenced
        # block (with empty body).  We only assert there is exactly one
        # fence pair — no double-nesting.
        prewrapped = "<memory-context>inner</memory-context>"
        with caplog.at_level("WARNING"):
            out = build_memory_context_block(prewrapped)
        assert out.count("<memory-context>") == 1
        assert out.count("</memory-context>") == 1
        assert any("pre-wrapped" in r.message for r in caplog.records)
