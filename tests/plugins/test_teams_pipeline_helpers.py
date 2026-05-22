"""Coverage for pure helpers in plugins.teams_pipeline.pipeline."""
from __future__ import annotations

import pytest

from plugins.teams_pipeline.pipeline import (
    _collect_call_metrics,
    _collect_participants,
    _extract_meeting_id_from_resource,
    _build_summary_prompt,
    _parse_summary_json,
    _heuristic_summary,
    _render_summary_markdown,
)
from plugins.teams_pipeline.models import (
    MeetingArtifact,
    TeamsMeetingRef,
    TeamsMeetingSummaryPayload,
)


def _make_artifact(artifact_type, metadata=None) -> MeetingArtifact:
    return MeetingArtifact(
        artifact_type=artifact_type,
        artifact_id=f"id-{artifact_type}",
        metadata=metadata or {},
    )


class TestCollectCallMetrics:
    def test_no_call_record(self):
        artifacts = [_make_artifact("transcript"), _make_artifact("recording")]
        m = _collect_call_metrics(artifacts)
        assert m["artifact_count"] == 2

    def test_call_record_metrics_merged(self):
        artifacts = [
            _make_artifact("call_record", {"metrics": {"duration_s": 120}}),
            _make_artifact("transcript"),
        ]
        m = _collect_call_metrics(artifacts)
        assert m["artifact_count"] == 2
        assert m["duration_s"] == 120

    def test_metrics_none_safe(self):
        artifacts = [_make_artifact("call_record", {"metrics": None})]
        m = _collect_call_metrics(artifacts)
        # Doesn't crash; only artifact_count present.
        assert m["artifact_count"] == 1

    def test_empty_artifacts_just_count(self):
        m = _collect_call_metrics([])
        assert m == {"artifact_count": 0}


class TestCollectParticipants:
    def test_displayname_top_level(self):
        ref = TeamsMeetingRef(
            meeting_id="m",
            metadata={"participants": [{"displayName": "Alice"}, {"displayName": "Bob"}]},
        )
        assert _collect_participants(ref) == ["Alice", "Bob"]

    def test_nested_identity_user_displayname(self):
        ref = TeamsMeetingRef(
            meeting_id="m",
            metadata={
                "participants": [
                    {"identity": {"user": {"displayName": "Charlie"}}}
                ]
            },
        )
        assert _collect_participants(ref) == ["Charlie"]

    def test_missing_returns_empty_list(self):
        ref = TeamsMeetingRef(meeting_id="m")
        assert _collect_participants(ref) == []

    def test_non_list_returns_empty(self):
        ref = TeamsMeetingRef(meeting_id="m", metadata={"participants": "not-a-list"})
        assert _collect_participants(ref) == []

    def test_non_dict_items_skipped(self):
        ref = TeamsMeetingRef(
            meeting_id="m",
            metadata={"participants": [None, 42, {"displayName": "Eve"}]},
        )
        assert _collect_participants(ref) == ["Eve"]


class TestExtractMeetingIdFromResource:
    def test_empty(self):
        assert _extract_meeting_id_from_resource("") is None

    def test_online_meetings_pair(self):
        out = _extract_meeting_id_from_resource(
            "communications/onlineMeetings/abc-123/transcripts/1"
        )
        assert out == "abc-123"

    def test_falls_back_to_last_segment(self):
        out = _extract_meeting_id_from_resource("users/u-1/calendar/event-42")
        assert out == "event-42"

    def test_only_slashes(self):
        # All-empty parts → None
        assert _extract_meeting_id_from_resource("////") is None


class TestBuildSummaryPrompt:
    def test_basic(self):
        ref = TeamsMeetingRef(meeting_id="m1", metadata={"subject": "Sprint planning"})
        artifacts = [_make_artifact("transcript")]
        out = _build_summary_prompt(ref, "transcript-text", artifacts)
        assert "Meeting ID: m1" in out
        assert "Sprint planning" in out
        assert "transcript-text" in out

    def test_no_artifacts_shows_none(self):
        ref = TeamsMeetingRef(meeting_id="m1")
        out = _build_summary_prompt(ref, "t", [])
        assert "- none" in out

    def test_transcript_truncated_at_18000(self):
        ref = TeamsMeetingRef(meeting_id="m1")
        long = "x" * 20000
        out = _build_summary_prompt(ref, long, [])
        # Up to 18000 chars of transcript, total prompt > 18000 but transcript capped.
        assert out.count("x") == 18000


class TestParseSummaryJson:
    def test_empty_falls_back_to_heuristic(self):
        out = _parse_summary_json("")
        # Heuristic with empty text → confidence "low".
        assert out["confidence"] == "low"

    def test_blank_falls_back_to_heuristic(self):
        out = _parse_summary_json("   \n  ")
        assert out["confidence"] == "low"

    def test_basic_json_object(self):
        text = '{"summary": "did stuff", "key_decisions": ["a", "b"], "action_items": [], "risks": [], "confidence": "high"}'
        out = _parse_summary_json(text)
        assert out["summary"] == "did stuff"
        assert out["key_decisions"] == ["a", "b"]
        assert out["confidence"] == "high"

    def test_strips_surrounding_text(self):
        text = "Some chatter before {\n\"summary\": \"x\"\n} and after"
        out = _parse_summary_json(text)
        assert out["summary"] == "x"

    def test_drops_blank_list_items(self):
        text = '{"summary":"s","action_items":["", "real one", "  "]}'
        out = _parse_summary_json(text)
        assert out["action_items"] == ["real one"]

    def test_default_confidence_is_medium(self):
        out = _parse_summary_json('{"summary":"x"}')
        assert out["confidence"] == "medium"


class TestHeuristicSummary:
    def test_empty(self):
        out = _heuristic_summary("")
        assert "unavailable" in out["summary"].lower() or "sparse" in out["summary"].lower()
        assert out["confidence"] == "low"

    def test_short_text_is_low_confidence(self):
        out = _heuristic_summary("just a quick note")
        assert out["confidence"] == "low"

    def test_long_text_is_medium_confidence(self):
        out = _heuristic_summary("x" * 400)
        assert out["confidence"] == "medium"

    def test_action_items_detected(self):
        text = "Action: ship feature\nfollow up: write docs\nNot an action"
        out = _heuristic_summary(text)
        # Bullets stripped of leading "-* " characters; action keyword preserved.
        assert any("ship feature" in item for item in out["action_items"])
        assert any("docs" in item for item in out["action_items"])

    def test_risks_detected(self):
        out = _heuristic_summary("Risk: budget overrun\nBlocker: missing approvals")
        assert any("budget" in r for r in out["risks"])
        assert any("approvals" in r for r in out["risks"])


class TestRenderSummaryMarkdown:
    def test_basic_render(self):
        payload = TeamsMeetingSummaryPayload(
            meeting_ref=TeamsMeetingRef(meeting_id="m1"),
            title="Weekly",
            summary="we shipped",
            key_decisions=["ship friday"],
            action_items=["a1", "a2"],
            risks=[],
            confidence="high",
            confidence_notes="LLM",
        )
        md = _render_summary_markdown(payload)
        assert md.startswith("# Weekly")
        assert "## Summary\nwe shipped" in md
        assert "- ship friday" in md
        assert "- a1" in md
        assert "Confidence: high" in md

    def test_empty_sections_show_none(self):
        payload = TeamsMeetingSummaryPayload(
            meeting_ref=TeamsMeetingRef(meeting_id="m1"),
        )
        md = _render_summary_markdown(payload)
        # Empty list sections render with "- None" placeholder.
        assert "## Key Decisions\n- None" in md
        assert "## Action Items\n- None" in md
        assert "## Risks\n- None" in md

    def test_title_defaults_to_meeting_id(self):
        payload = TeamsMeetingSummaryPayload(
            meeting_ref=TeamsMeetingRef(meeting_id="m-xyz"),
        )
        md = _render_summary_markdown(payload)
        assert md.startswith("# Meeting m-xyz")

    def test_confidence_defaults_to_unknown(self):
        payload = TeamsMeetingSummaryPayload(
            meeting_ref=TeamsMeetingRef(meeting_id="m"),
        )
        md = _render_summary_markdown(payload)
        assert "Confidence: unknown" in md
