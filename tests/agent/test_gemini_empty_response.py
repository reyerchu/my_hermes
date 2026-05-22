"""Coverage for _tool_call_extra_from_part + _empty_response in
agent.gemini_native_adapter."""
from __future__ import annotations

import time

import pytest

from agent.gemini_native_adapter import (
    _tool_call_extra_from_part,
    _empty_response,
)


class TestToolCallExtraFromPart:
    def test_with_signature(self):
        out = _tool_call_extra_from_part({"thoughtSignature": "sig-blob"})
        assert out == {"google": {"thought_signature": "sig-blob"}}

    def test_no_signature(self):
        assert _tool_call_extra_from_part({}) is None

    def test_blank_signature(self):
        assert _tool_call_extra_from_part({"thoughtSignature": ""}) is None

    def test_non_string_signature(self):
        assert _tool_call_extra_from_part({"thoughtSignature": 42}) is None


class TestEmptyResponse:
    def test_basic_shape(self):
        resp = _empty_response("test-model")
        assert resp.model == "test-model"
        assert resp.object == "chat.completion"
        assert resp.id.startswith("chatcmpl-")
        assert len(resp.id) == 9 + 12  # "chatcmpl-" + 12 hex chars

    def test_choices(self):
        resp = _empty_response("m")
        assert len(resp.choices) == 1
        choice = resp.choices[0]
        assert choice.index == 0
        assert choice.finish_reason == "stop"
        msg = choice.message
        assert msg.role == "assistant"
        assert msg.content == ""
        assert msg.tool_calls is None

    def test_usage_zero_tokens(self):
        resp = _empty_response("m")
        usage = resp.usage
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0
        assert usage.prompt_tokens_details.cached_tokens == 0

    def test_created_close_to_now(self):
        resp = _empty_response("m")
        # Created timestamp should be close to current time.
        assert abs(resp.created - int(time.time())) < 5

    def test_unique_ids(self):
        ids = {_empty_response("m").id for _ in range(10)}
        # 12-hex UUIDs → should be unique.
        assert len(ids) == 10
