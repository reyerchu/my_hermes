"""Coverage for ``_parse_response`` in ``agent.shell_hooks``.

Translates a hook script's stdout JSON into a Hermes-shaped result dict.
The most important contract: pre_tool_call's Claude-Code-style
``{"decision": "block", "reason": ...}`` must translate to
``{"action": "block", "message": ...}``."""
from __future__ import annotations

import json

import pytest

from agent.shell_hooks import _parse_response


class TestParseResponseEmpty:
    def test_empty_stdout_returns_none(self):
        assert _parse_response("pre_tool_call", "") is None
        assert _parse_response("pre_tool_call", "   \n") is None

    def test_invalid_json_returns_none(self):
        assert _parse_response("pre_tool_call", "not json") is None

    def test_non_dict_json_returns_none(self):
        assert _parse_response("pre_tool_call", json.dumps([1, 2, 3])) is None


class TestParseResponsePreToolCall:
    def test_claude_code_block_decision_translated(self):
        stdout = json.dumps({"decision": "block", "reason": "no perms"})
        out = _parse_response("pre_tool_call", stdout)
        assert out == {"action": "block", "message": "no perms"}

    def test_decision_block_with_message_field(self):
        # Some hooks use "message" instead of "reason".
        stdout = json.dumps({"decision": "block", "message": "stop"})
        out = _parse_response("pre_tool_call", stdout)
        assert out == {"action": "block", "message": "stop"}

    def test_decision_block_without_reason_returns_none(self):
        stdout = json.dumps({"decision": "block"})
        assert _parse_response("pre_tool_call", stdout) is None

    def test_decision_other_than_block_ignored(self):
        stdout = json.dumps({"decision": "allow"})
        assert _parse_response("pre_tool_call", stdout) is None

    def test_dict_without_decision_key_returns_none(self):
        stdout = json.dumps({"reason": "no decision here"})
        assert _parse_response("pre_tool_call", stdout) is None


class TestParseResponsePreLlmCall:
    def test_context_string_passed_through(self):
        stdout = json.dumps({"context": "extra system note"})
        out = _parse_response("pre_llm_call", stdout)
        assert out == {"context": "extra system note"}

    def test_empty_context_returns_none(self):
        stdout = json.dumps({"context": ""})
        assert _parse_response("pre_llm_call", stdout) is None

    def test_whitespace_only_context_returns_none(self):
        stdout = json.dumps({"context": "   "})
        assert _parse_response("pre_llm_call", stdout) is None

    def test_non_string_context_returns_none(self):
        stdout = json.dumps({"context": 42})
        assert _parse_response("pre_llm_call", stdout) is None


class TestParseResponseUnknownEvent:
    def test_unknown_event_with_block_decision_returns_none(self):
        # The block translation is only for pre_tool_call.  Other event
        # types should fall through to the context branch and return None
        # for non-string content.
        stdout = json.dumps({"decision": "block", "reason": "x"})
        assert _parse_response("post_tool_call", stdout) is None
