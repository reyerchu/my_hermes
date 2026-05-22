"""Coverage for pure helpers in plugins.teams_pipeline.meetings."""
from __future__ import annotations

import pytest

from plugins.teams_pipeline.meetings import (
    TeamsMeetingError,
    TeamsMeetingNotFoundError,
    TeamsMeetingPermissionError,
    _meeting_path,
    _parse_organizer_user_id,
    _parse_thread_id,
    _wrap_graph_error,
    _normalize_meeting_ref,
)
from plugins.teams_pipeline.models import TeamsMeetingRef
from tools.microsoft_graph_client import MicrosoftGraphAPIError


class TestMeetingPath:
    def test_str_id_url_quoted(self):
        # Slashes etc are quoted with safe=''.
        assert _meeting_path("abc/def") == (
            "/communications/onlineMeetings/abc%2Fdef"
        )

    def test_simple_id(self):
        assert _meeting_path("xyz") == "/communications/onlineMeetings/xyz"

    def test_meeting_ref_uses_meeting_id(self):
        ref = TeamsMeetingRef(meeting_id="meet-1")
        assert _meeting_path(ref) == "/communications/onlineMeetings/meet-1"


def _err(status: int, msg: str = "boom") -> MicrosoftGraphAPIError:
    return MicrosoftGraphAPIError(status, "GET", "https://graph.example/x", msg)


class TestWrapGraphError:
    def test_401_to_permission_error(self):
        wrapped = _wrap_graph_error(_err(401, "unauthorized"), missing_message="x")
        assert isinstance(wrapped, TeamsMeetingPermissionError)

    def test_403_to_permission_error(self):
        wrapped = _wrap_graph_error(_err(403, "forbidden"), missing_message="x")
        assert isinstance(wrapped, TeamsMeetingPermissionError)

    def test_404_to_not_found(self):
        wrapped = _wrap_graph_error(_err(404, "not found"), missing_message="meeting missing")
        assert isinstance(wrapped, TeamsMeetingNotFoundError)
        assert "meeting missing" in str(wrapped)

    def test_500_to_generic_error(self):
        wrapped = _wrap_graph_error(_err(500, "server died"), missing_message="x")
        assert type(wrapped) is TeamsMeetingError  # exact class, not subclass


class TestParseOrganizerUserId:
    def test_full_path(self):
        payload = {"organizer": {"identity": {"user": {"id": "u-1"}}}}
        assert _parse_organizer_user_id(payload) == "u-1"

    def test_missing_organizer(self):
        assert _parse_organizer_user_id({}) is None

    def test_non_dict_organizer(self):
        assert _parse_organizer_user_id({"organizer": "string"}) is None

    def test_missing_identity(self):
        assert _parse_organizer_user_id({"organizer": {}}) is None

    def test_non_dict_identity(self):
        assert _parse_organizer_user_id({"organizer": {"identity": []}}) is None

    def test_missing_user(self):
        assert _parse_organizer_user_id({"organizer": {"identity": {}}}) is None

    def test_non_dict_user(self):
        out = _parse_organizer_user_id(
            {"organizer": {"identity": {"user": "x"}}}
        )
        assert out is None


class TestParseThreadId:
    def test_chat_info_thread_id(self):
        assert _parse_thread_id({"chatInfo": {"threadId": "T1"}}) == "T1"

    def test_chat_info_thread_id_coerced_to_str(self):
        assert _parse_thread_id({"chatInfo": {"threadId": 42}}) == "42"

    def test_fallback_to_top_level_thread_id(self):
        assert _parse_thread_id({"threadId": "FOO"}) == "FOO"

    def test_chat_info_not_dict_falls_back(self):
        assert _parse_thread_id(
            {"chatInfo": "weird", "threadId": "BAR"}
        ) == "BAR"

    def test_no_thread_returns_none(self):
        assert _parse_thread_id({}) is None


class TestNormalizeMeetingRef:
    def test_basic_payload(self):
        payload = {
            "id": "meet-7",
            "joinWebUrl": "https://teams.example/join/x",
            "calendarEventId": "evt-1",
            "chatInfo": {"threadId": "thr-1"},
            "organizer": {"identity": {"user": {"id": "u-9"}}},
            "subject": "Sync",
            "startDateTime": "2026-05-22T12:00:00Z",
            "endDateTime": "2026-05-22T13:00:00Z",
        }
        ref = _normalize_meeting_ref(payload, tenant_id="tenant-A")
        assert ref.meeting_id == "meet-7"
        assert ref.organizer_user_id == "u-9"
        assert ref.join_web_url == "https://teams.example/join/x"
        assert ref.calendar_event_id == "evt-1"
        assert ref.thread_id == "thr-1"
        assert ref.tenant_id == "tenant-A"
        assert ref.metadata["subject"] == "Sync"

    def test_tenant_id_from_payload_when_not_provided(self):
        payload = {"id": "m", "tenantId": "T-X"}
        ref = _normalize_meeting_ref(payload)
        assert ref.tenant_id == "T-X"

    def test_meeting_id_stripped(self):
        payload = {"id": "  m1  "}
        ref = _normalize_meeting_ref(payload)
        assert ref.meeting_id == "m1"

    def test_missing_id_raises(self):
        # TeamsMeetingRef.__post_init__ rejects empty meeting_id.
        with pytest.raises(ValueError):
            _normalize_meeting_ref({})

    def test_only_non_none_metadata_kept(self):
        payload = {"id": "m", "subject": "A", "startDateTime": None}
        ref = _normalize_meeting_ref(payload)
        # None-valued keys filtered out
        assert "startDateTime" not in ref.metadata
        assert ref.metadata.get("subject") == "A"
