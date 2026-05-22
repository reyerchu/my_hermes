"""Coverage for the pure helpers in ``agent.codex_responses_adapter``."""
from __future__ import annotations

import pytest

from agent.codex_responses_adapter import (
    _deterministic_call_id,
    _normalize_responses_message_status,
    _split_responses_tool_id,
)


class TestDeterministicCallId:
    def test_same_inputs_yield_same_id(self):
        a = _deterministic_call_id("read_file", '{"path":"/x"}', 0)
        b = _deterministic_call_id("read_file", '{"path":"/x"}', 0)
        assert a == b

    def test_call_id_starts_with_call_prefix(self):
        out = _deterministic_call_id("foo", "{}", 0)
        assert out.startswith("call_")

    def test_different_name_yields_different_id(self):
        a = _deterministic_call_id("foo", "{}", 0)
        b = _deterministic_call_id("bar", "{}", 0)
        assert a != b

    def test_different_arguments_yields_different_id(self):
        a = _deterministic_call_id("foo", '{"x":1}', 0)
        b = _deterministic_call_id("foo", '{"x":2}', 0)
        assert a != b

    def test_index_separates_collisions(self):
        a = _deterministic_call_id("foo", "{}", 0)
        b = _deterministic_call_id("foo", "{}", 1)
        assert a != b

    def test_id_is_short_enough_for_api_limits(self):
        out = _deterministic_call_id("foo", "{}", 0)
        # call_ + 12 hex chars = 17 chars
        assert len(out) == len("call_") + 12


class TestSplitResponsesToolId:
    def test_non_string_returns_none_pair(self):
        assert _split_responses_tool_id(None) == (None, None)
        assert _split_responses_tool_id(42) == (None, None)

    def test_empty_string_returns_none_pair(self):
        assert _split_responses_tool_id("") == (None, None)
        assert _split_responses_tool_id("   ") == (None, None)

    def test_pipe_separator_splits_into_call_and_response_item(self):
        assert _split_responses_tool_id("call_abc|fc_xyz") == (
            "call_abc",
            "fc_xyz",
        )

    def test_pipe_with_whitespace_trims_each_side(self):
        assert _split_responses_tool_id(" call_abc | fc_xyz ") == (
            "call_abc",
            "fc_xyz",
        )

    def test_fc_prefix_treated_as_response_item_only(self):
        assert _split_responses_tool_id("fc_abcdef") == (None, "fc_abcdef")

    def test_plain_string_treated_as_call_id_only(self):
        assert _split_responses_tool_id("call_xyz") == ("call_xyz", None)


class TestNormalizeResponsesMessageStatus:
    @pytest.mark.parametrize("value", ["completed", "incomplete", "in_progress"])
    def test_known_status_passes_through(self, value):
        assert _normalize_responses_message_status(value) == value

    def test_case_insensitive(self):
        assert (
            _normalize_responses_message_status("COMPLETED") == "completed"
        )

    def test_hyphen_to_underscore_normalisation(self):
        # "in-progress" → "in_progress"
        assert (
            _normalize_responses_message_status("in-progress") == "in_progress"
        )

    def test_space_to_underscore_normalisation(self):
        assert (
            _normalize_responses_message_status("in progress") == "in_progress"
        )

    def test_unknown_value_uses_default(self):
        assert _normalize_responses_message_status("weird") == "completed"
        assert (
            _normalize_responses_message_status("weird", default="incomplete")
            == "incomplete"
        )

    def test_non_string_value_uses_default(self):
        assert _normalize_responses_message_status(None) == "completed"
        assert _normalize_responses_message_status(42) == "completed"
