"""Coverage for the pure helpers in ``agent.google_code_assist``."""
from __future__ import annotations

import json

import pytest

from agent.google_code_assist import (
    CodeAssistError,
    ProjectIdRequiredError,
    _build_headers,
    _client_metadata,
    _is_vpc_sc_violation,
)


class TestBuildHeaders:
    def test_includes_bearer_authorization(self):
        h = _build_headers("tok-123")
        assert h["Authorization"] == "Bearer tok-123"

    def test_includes_required_static_headers(self):
        h = _build_headers("x")
        assert h["Content-Type"] == "application/json"
        assert h["Accept"] == "application/json"
        assert "User-Agent" in h
        assert "X-Goog-Api-Client" in h

    def test_request_id_is_uuid_like(self):
        h = _build_headers("x")
        rid = h["x-activity-request-id"]
        # Expect a UUID4 shape: 8-4-4-4-12 hex.
        parts = rid.split("-")
        assert len(parts) == 5

    def test_request_id_is_unique_per_call(self):
        a = _build_headers("x")["x-activity-request-id"]
        b = _build_headers("x")["x-activity-request-id"]
        assert a != b

    def test_user_agent_model_suffix_appended(self):
        h = _build_headers("x", user_agent_model="gemini-2.0-flash")
        assert "model/gemini-2.0-flash" in h["User-Agent"]


class TestClientMetadata:
    def test_returns_required_fields(self):
        meta = _client_metadata()
        assert meta["pluginType"] == "GEMINI"
        # ideType and platform are "UNSPECIFIED" by design.
        assert meta["ideType"] == "IDE_UNSPECIFIED"
        assert meta["platform"] == "PLATFORM_UNSPECIFIED"


class TestIsVpcScViolation:
    def test_empty_body_returns_false(self):
        assert _is_vpc_sc_violation("") is False

    def test_non_json_body_with_marker_returns_true(self):
        # Fallback: substring search when JSON parsing fails.
        assert _is_vpc_sc_violation("not json SECURITY_POLICY_VIOLATED") is True

    def test_non_json_body_without_marker_returns_false(self):
        assert _is_vpc_sc_violation("plain text error") is False

    def test_structured_error_with_violation_details(self):
        body = json.dumps({
            "error": {
                "details": [
                    {"reason": "SECURITY_POLICY_VIOLATED"},
                ],
            },
        })
        assert _is_vpc_sc_violation(body) is True

    def test_structured_error_without_violation_details(self):
        body = json.dumps({
            "error": {
                "details": [
                    {"reason": "RATE_LIMIT_EXCEEDED"},
                ],
            },
        })
        assert _is_vpc_sc_violation(body) is False

    def test_unrelated_dict_returns_false(self):
        assert _is_vpc_sc_violation(json.dumps({"ok": True})) is False


class TestExceptionHierarchy:
    def test_code_assist_error_is_a_runtime_error(self):
        assert issubclass(CodeAssistError, RuntimeError)

    def test_project_id_required_inherits_code_assist_error(self):
        assert issubclass(ProjectIdRequiredError, CodeAssistError)
