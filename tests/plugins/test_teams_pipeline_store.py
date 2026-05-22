"""Coverage for ``plugins.teams_pipeline.store`` — the durable JSON
state for the Teams pipeline plugin."""
from __future__ import annotations

import json

import pytest

from plugins.teams_pipeline.store import (
    TeamsPipelineStore,
    resolve_teams_pipeline_store_path,
)


# ─── path resolution ──────────────────────────────────────────────────────


class TestResolveTeamsPipelineStorePath:
    def test_explicit_path_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MSGRAPH_WEBHOOK_STORE_PATH", "/from/env.json")
        resolved = resolve_teams_pipeline_store_path(tmp_path / "explicit.json")
        assert str(resolved) == str(tmp_path / "explicit.json")

    def test_empty_explicit_string_falls_through(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MSGRAPH_WEBHOOK_STORE_PATH", "/from/env.json")
        # An explicit whitespace-only path is treated as "unset" and the
        # env var wins.
        resolved = resolve_teams_pipeline_store_path("   ")
        assert str(resolved) == "/from/env.json"

    def test_env_var_when_no_explicit(self, monkeypatch):
        monkeypatch.setenv("MSGRAPH_WEBHOOK_STORE_PATH", "/env/store.json")
        resolved = resolve_teams_pipeline_store_path(None)
        assert str(resolved) == "/env/store.json"

    def test_falls_back_to_hermes_home_default(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        monkeypatch.delenv("MSGRAPH_WEBHOOK_STORE_PATH", raising=False)
        resolved = resolve_teams_pipeline_store_path(None)
        assert resolved == tmp_path / "teams_pipeline_store.json"


# ─── TeamsPipelineStore — subscriptions ────────────────────────────────────


class TestSubscriptions:
    def test_empty_store_has_no_subscriptions(self, tmp_path):
        store = TeamsPipelineStore(tmp_path / "x.json")
        assert store.list_subscriptions() == {}
        assert store.get_subscription("nope") is None

    def test_upsert_then_get_returns_deep_copy(self, tmp_path):
        store = TeamsPipelineStore(tmp_path / "x.json")
        merged = store.upsert_subscription("s1", {"foo": 1})
        assert merged["foo"] == 1
        # Mutating the returned dict does not bleed back into the store.
        merged["foo"] = 999
        assert store.get_subscription("s1")["foo"] == 1

    def test_upsert_is_a_merge_not_a_replace(self, tmp_path):
        store = TeamsPipelineStore(tmp_path / "x.json")
        store.upsert_subscription("s1", {"foo": 1, "bar": 2})
        store.upsert_subscription("s1", {"bar": 99})
        sub = store.get_subscription("s1")
        # The store may add bookkeeping fields (created_at/updated_at/etc.)
        # so assert the merged caller-supplied keys round-trip, not equality.
        assert sub["foo"] == 1
        assert sub["bar"] == 99

    def test_delete_subscription_returns_true_on_success(self, tmp_path):
        store = TeamsPipelineStore(tmp_path / "x.json")
        store.upsert_subscription("s1", {})
        assert store.delete_subscription("s1") is True
        assert store.get_subscription("s1") is None

    def test_delete_unknown_subscription_returns_false(self, tmp_path):
        store = TeamsPipelineStore(tmp_path / "x.json")
        assert store.delete_subscription("nope") is False


# ─── TeamsPipelineStore — notifications ────────────────────────────────────


class TestNotificationReceipts:
    def test_build_receipt_key_stable_and_unique(self, tmp_path):
        store = TeamsPipelineStore(tmp_path / "x.json")
        a = store.build_notification_receipt_key({"id": "x", "type": "msg"})
        b = store.build_notification_receipt_key({"id": "x", "type": "msg"})
        c = store.build_notification_receipt_key({"id": "y", "type": "msg"})
        assert a == b  # same input → same key
        assert a != c  # different input → different key

    def test_has_returns_false_before_record(self, tmp_path):
        store = TeamsPipelineStore(tmp_path / "x.json")
        assert store.has_notification_receipt("never-seen") is False

    def test_record_then_has_returns_true(self, tmp_path):
        store = TeamsPipelineStore(tmp_path / "x.json")
        store.record_notification_receipt("k", {"meta": "v"})
        assert store.has_notification_receipt("k") is True


# ─── TeamsPipelineStore — event timestamps ─────────────────────────────────


class TestEventTimestamps:
    def test_get_unknown_event_returns_none(self, tmp_path):
        store = TeamsPipelineStore(tmp_path / "x.json")
        assert store.get_event_timestamp("nope") is None

    def test_record_then_get_returns_value(self, tmp_path):
        store = TeamsPipelineStore(tmp_path / "x.json")
        recorded = store.record_event_timestamp("e1")
        assert isinstance(recorded, str) and recorded
        assert store.get_event_timestamp("e1") == recorded

    def test_explicit_timestamp_is_honoured(self, tmp_path):
        store = TeamsPipelineStore(tmp_path / "x.json")
        ts = "2026-01-01T00:00:00+00:00"
        assert store.record_event_timestamp("e1", ts) == ts
        assert store.get_event_timestamp("e1") == ts


# ─── TeamsPipelineStore — stats ───────────────────────────────────────────


class TestStats:
    def test_starts_zero_for_each_bucket(self, tmp_path):
        store = TeamsPipelineStore(tmp_path / "x.json")
        stats = store.stats()
        for key in ("subscriptions", "notification_receipts", "event_timestamps", "jobs", "sink_records"):
            assert stats[key] == 0

    def test_counts_buckets_after_writes(self, tmp_path):
        store = TeamsPipelineStore(tmp_path / "x.json")
        store.upsert_subscription("s1", {})
        store.upsert_subscription("s2", {})
        store.record_notification_receipt("k", {})
        store.record_event_timestamp("e")
        store.upsert_job("j1", {})
        store.upsert_sink_record("snk", {})
        stats = store.stats()
        assert stats["subscriptions"] == 2
        assert stats["notification_receipts"] == 1
        assert stats["event_timestamps"] == 1
        assert stats["jobs"] == 1
        assert stats["sink_records"] == 1


# ─── TeamsPipelineStore — jobs + sink records ─────────────────────────────


class TestJobsAndSinkRecords:
    def test_job_lifecycle(self, tmp_path):
        store = TeamsPipelineStore(tmp_path / "x.json")
        assert store.get_job("j1") is None
        merged = store.upsert_job("j1", {"status": "queued"})
        assert merged["status"] == "queued"
        merged = store.upsert_job("j1", {"status": "done"})
        assert merged["status"] == "done"
        assert store.list_jobs()["j1"]["status"] == "done"

    def test_sink_record_lifecycle(self, tmp_path):
        store = TeamsPipelineStore(tmp_path / "x.json")
        assert store.get_sink_record("k") is None
        merged = store.upsert_sink_record("k", {"x": 1})
        assert merged["x"] == 1
        merged = store.upsert_sink_record("k", {"y": 2})
        # Merge preserves the prior field.
        assert merged["x"] == 1
        assert merged["y"] == 2
