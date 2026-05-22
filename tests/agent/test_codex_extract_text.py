"""Coverage for _extract_responses_message_text and
_extract_responses_reasoning_text in agent.codex_responses_adapter."""
from __future__ import annotations

import pytest

from agent.codex_responses_adapter import (
    _extract_responses_message_text,
    _extract_responses_reasoning_text,
)


class _Part:
    def __init__(self, *, type=None, text=None):
        self.type = type
        self.text = text


class _Item:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestExtractResponsesMessageText:
    def test_no_content(self):
        item = _Item()
        assert _extract_responses_message_text(item) == ""

    def test_content_not_list(self):
        item = _Item(content="hi")
        assert _extract_responses_message_text(item) == ""

    def test_output_text_extracted(self):
        item = _Item(content=[
            _Part(type="output_text", text="Hello "),
            _Part(type="output_text", text="World"),
        ])
        assert _extract_responses_message_text(item) == "Hello World"

    def test_text_type_also_accepted(self):
        item = _Item(content=[_Part(type="text", text="A")])
        assert _extract_responses_message_text(item) == "A"

    def test_unknown_type_skipped(self):
        item = _Item(content=[
            _Part(type="output_text", text="keep"),
            _Part(type="reasoning", text="skip"),
        ])
        assert _extract_responses_message_text(item) == "keep"

    def test_non_string_text_skipped(self):
        item = _Item(content=[_Part(type="output_text", text=42)])
        assert _extract_responses_message_text(item) == ""

    def test_empty_text_skipped(self):
        item = _Item(content=[_Part(type="output_text", text="")])
        assert _extract_responses_message_text(item) == ""

    def test_whitespace_stripped(self):
        item = _Item(content=[_Part(type="output_text", text="  hi  ")])
        # Outer whitespace stripped at join.
        assert _extract_responses_message_text(item) == "hi"


class TestExtractResponsesReasoningText:
    def test_summary_list(self):
        item = _Item(summary=[
            _Part(text="step 1"),
            _Part(text="step 2"),
        ])
        assert _extract_responses_reasoning_text(item) == "step 1\nstep 2"

    def test_summary_list_drops_non_string(self):
        item = _Item(summary=[
            _Part(text="keep"),
            _Part(text=42),
        ])
        assert _extract_responses_reasoning_text(item) == "keep"

    def test_falls_back_to_text_field(self):
        # summary missing → fall back to item.text directly.
        item = _Item(text="reasoning")
        assert _extract_responses_reasoning_text(item) == "reasoning"

    def test_non_list_summary_falls_back(self):
        item = _Item(summary="ignored", text="from_text")
        assert _extract_responses_reasoning_text(item) == "from_text"

    def test_empty_summary_falls_back_to_text(self):
        item = _Item(summary=[], text="from_text")
        assert _extract_responses_reasoning_text(item) == "from_text"

    def test_text_whitespace_stripped(self):
        item = _Item(text="  hi  ")
        assert _extract_responses_reasoning_text(item) == "hi"

    def test_no_summary_or_text(self):
        item = _Item()
        assert _extract_responses_reasoning_text(item) == ""

    def test_non_string_text_returns_empty(self):
        item = _Item(text=42)
        assert _extract_responses_reasoning_text(item) == ""
