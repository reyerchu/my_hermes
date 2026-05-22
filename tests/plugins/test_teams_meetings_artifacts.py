"""Coverage for artifact-related pure helpers in
plugins.teams_pipeline.meetings."""
from __future__ import annotations

import pytest

from plugins.teams_pipeline.meetings import (
    _normalize_artifact,
    _transcript_sort_key,
    _recording_download_path,
    _transcript_download_path,
    select_preferred_transcript,
)
from plugins.teams_pipeline.models import MeetingArtifact, TeamsMeetingRef


def _ref(meeting_id="m1"):
    return TeamsMeetingRef(meeting_id=meeting_id)


class TestNormalizeArtifact:
    def test_download_url_prefers_graph_field(self):
        payload = {
            "id": "a1",
            "@microsoft.graph.downloadUrl": "https://graph/download",
            "downloadUrl": "https://other",
        }
        out = _normalize_artifact("recording", payload)
        assert out.download_url == "https://graph/download"

    def test_download_url_fallback_chain(self):
        # No graph download → falls back to downloadUrl → recordingContentUrl
        out = _normalize_artifact(
            "recording",
            {"id": "a1", "recordingContentUrl": "https://rec"},
        )
        assert out.download_url == "https://rec"

    def test_transcript_content_url_fallback(self):
        out = _normalize_artifact(
            "transcript",
            {"id": "a1", "transcriptContentUrl": "https://tr"},
        )
        assert out.download_url == "https://tr"

    def test_source_url_prefers_web_url(self):
        out = _normalize_artifact(
            "recording",
            {"id": "a", "webUrl": "https://w", "contentUrl": "https://c"},
        )
        assert out.source_url == "https://w"

    def test_default_source_url_used(self):
        out = _normalize_artifact(
            "recording", {"id": "a"},
            default_source_url="https://default",
        )
        assert out.source_url == "https://default"

    def test_display_name_or_name(self):
        a = _normalize_artifact("transcript", {"id": "a", "displayName": "DN"})
        b = _normalize_artifact("transcript", {"id": "a", "name": "N"})
        assert a.display_name == "DN"
        assert b.display_name == "N"

    def test_content_type_fallback(self):
        out = _normalize_artifact(
            "recording", {"id": "a", "fileMimeType": "video/mp4"}
        )
        assert out.content_type == "video/mp4"

    def test_id_whitespace_stripped(self):
        out = _normalize_artifact("transcript", {"id": "  a1  "})
        assert out.artifact_id == "a1"

    def test_metadata_includes_full_payload(self):
        payload = {"id": "a", "extraField": 42}
        out = _normalize_artifact("transcript", payload)
        assert out.metadata["extraField"] == 42


class TestTranscriptSortKey:
    def _artifact(self, **overrides):
        base = {
            "artifact_type": "transcript",
            "artifact_id": "a",
        }
        base.update(overrides)
        return MeetingArtifact(**base)

    def test_completed_status_sorts_high(self):
        completed = self._artifact(metadata={"status": "available"})
        pending = self._artifact(metadata={"status": "pending"})
        # The "is_completed" flag should make the first tuple element 1 vs 0.
        assert _transcript_sort_key(completed)[0] == 1
        assert _transcript_sort_key(pending)[0] == 0

    def test_has_download_when_url_present(self):
        with_dl = self._artifact(download_url="https://x")
        without = self._artifact()
        assert _transcript_sort_key(with_dl)[1] == 1
        assert _transcript_sort_key(without)[1] == 0

    def test_source_url_also_counts_as_downloadable(self):
        out = self._artifact(source_url="https://y")
        assert _transcript_sort_key(out)[1] == 1

    def test_empty_metadata_sort_low(self):
        out = self._artifact()
        assert _transcript_sort_key(out) == (0, 0, "")


class TestDownloadPaths:
    def test_recording_uses_download_url_when_present(self):
        art = MeetingArtifact(
            artifact_type="recording",
            artifact_id="r1",
            download_url="https://direct",
        )
        out = _recording_download_path(_ref(), art)
        assert out == "https://direct"

    def test_recording_constructs_path_otherwise(self):
        art = MeetingArtifact(artifact_type="recording", artifact_id="r1")
        out = _recording_download_path(_ref("M"), art)
        assert "onlineMeetings/M/recordings/r1/content" in out

    def test_transcript_uses_download_url_when_present(self):
        art = MeetingArtifact(
            artifact_type="transcript",
            artifact_id="t1",
            download_url="https://direct",
        )
        out = _transcript_download_path(_ref(), art)
        assert out == "https://direct"

    def test_transcript_constructs_path_otherwise(self):
        art = MeetingArtifact(artifact_type="transcript", artifact_id="t1")
        out = _transcript_download_path(_ref("M"), art)
        assert "onlineMeetings/M/transcripts/t1/content" in out

    def test_url_encoded_artifact_id(self):
        # Slashes in id get quoted with safe=''.
        art = MeetingArtifact(artifact_type="recording", artifact_id="r/foo")
        out = _recording_download_path(_ref("M"), art)
        assert "r%2Ffoo" in out


class TestSelectPreferredTranscript:
    def test_none_when_no_transcripts(self):
        rec = MeetingArtifact(artifact_type="recording", artifact_id="r1")
        out = select_preferred_transcript([rec])
        assert out is None

    def test_returns_only_transcript(self):
        t = MeetingArtifact(artifact_type="transcript", artifact_id="t1")
        out = select_preferred_transcript([t])
        assert out is t

    def test_prefers_completed_over_pending(self):
        pending = MeetingArtifact(
            artifact_type="transcript", artifact_id="pending",
            metadata={"status": "pending"},
        )
        complete = MeetingArtifact(
            artifact_type="transcript", artifact_id="complete",
            metadata={"status": "available"}, download_url="https://x",
        )
        out = select_preferred_transcript([pending, complete])
        assert out.artifact_id == "complete"

    def test_non_transcripts_filtered(self):
        rec = MeetingArtifact(artifact_type="recording", artifact_id="r")
        t = MeetingArtifact(artifact_type="transcript", artifact_id="t")
        out = select_preferred_transcript([rec, t])
        assert out is t
