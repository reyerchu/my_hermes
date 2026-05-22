"""Extended coverage for plugins.teams_pipeline.subscriptions —
sync_graph_subscription_record, expected_client_state, and
is_managed_subscription."""
from __future__ import annotations

import json

import pytest

from plugins.teams_pipeline.subscriptions import (
    expected_client_state,
    is_managed_subscription,
    sync_graph_subscription_record,
    resolve_store_path,
    build_store,
)
from plugins.teams_pipeline.store import TeamsPipelineStore


@pytest.fixture
def store(tmp_path):
    return TeamsPipelineStore(tmp_path / "store.json")


def _payload(**overrides):
    base = {
        "id": "sub-1",
        "resource": "/me/onlineMeetings",
        "changeType": "created,updated",
        "notificationUrl": "https://x.example/cb",
        "expirationDateTime": "2027-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


class TestExpectedClientState:
    def test_explicit_value(self):
        assert expected_client_state("hello") == "hello"

    def test_explicit_blank_returns_none(self):
        assert expected_client_state("   ") is None

    def test_env_fallback(self, monkeypatch):
        monkeypatch.setenv("MSGRAPH_WEBHOOK_CLIENT_STATE", "from-env")
        assert expected_client_state() == "from-env"

    def test_env_blank_returns_none(self, monkeypatch):
        monkeypatch.setenv("MSGRAPH_WEBHOOK_CLIENT_STATE", "  ")
        assert expected_client_state() is None

    def test_env_missing_returns_none(self, monkeypatch):
        monkeypatch.delenv("MSGRAPH_WEBHOOK_CLIENT_STATE", raising=False)
        assert expected_client_state() is None


class TestIsManagedSubscription:
    def test_known_id_returns_true(self, store):
        # Plant a record for sub-1 in the store
        store.upsert_subscription("sub-1", {"resource": "/x"})
        out = is_managed_subscription(
            store, {"subscription_id": "sub-1"}, expected_client_state_value=None
        )
        assert out is True

    def test_unknown_id_no_state_returns_false(self, store):
        out = is_managed_subscription(
            store, {"subscription_id": "sub-x"}, expected_client_state_value=None
        )
        assert out is False

    def test_matching_client_state_returns_true(self, store):
        out = is_managed_subscription(
            store,
            {"subscription_id": "sub-x", "client_state": "expected"},
            expected_client_state_value="expected",
        )
        assert out is True

    def test_clientstate_alias_camelcase(self, store):
        out = is_managed_subscription(
            store,
            {"clientState": "expected"},
            expected_client_state_value="expected",
        )
        assert out is True

    def test_mismatched_client_state_false(self, store):
        out = is_managed_subscription(
            store,
            {"client_state": "different"},
            expected_client_state_value="expected",
        )
        assert out is False

    def test_blank_client_state_false(self, store):
        out = is_managed_subscription(
            store,
            {"client_state": ""},
            expected_client_state_value="expected",
        )
        assert out is False

    def test_id_field_alias(self, store):
        store.upsert_subscription("sub-x", {})
        # Payload uses "id" instead of "subscription_id"
        out = is_managed_subscription(
            store, {"id": "sub-x"}, expected_client_state_value=None
        )
        assert out is True


class TestSyncGraphSubscriptionRecord:
    def test_active_when_future_expiration(self, store):
        out = sync_graph_subscription_record(store, _payload(
            expirationDateTime="2099-01-01T00:00:00Z",
        ))
        assert out["status"] == "active"

    def test_expired_when_past_expiration(self, store):
        out = sync_graph_subscription_record(store, _payload(
            expirationDateTime="2020-01-01T00:00:00Z",
        ))
        assert out["status"] == "expired"

    def test_explicit_status_wins(self, store):
        out = sync_graph_subscription_record(
            store,
            _payload(expirationDateTime="2099-01-01T00:00:00Z"),
            status="custom",
        )
        assert out["status"] == "custom"

    def test_renewed_sets_latest_renewal_at(self, store):
        out = sync_graph_subscription_record(
            store, _payload(), renewed=True,
        )
        assert "latest_renewal_at" in out

    def test_record_persisted_to_store(self, store):
        sync_graph_subscription_record(store, _payload(id="sub-A"))
        assert store.get_subscription("sub-A") is not None


class TestResolveStorePathHelper:
    def test_returns_str(self, tmp_path):
        out = resolve_store_path(str(tmp_path / "custom.json"))
        assert isinstance(out, str)
        assert "custom.json" in out


class TestBuildStore:
    def test_returns_teams_pipeline_store(self, tmp_path):
        s = build_store(str(tmp_path / "x.json"))
        assert isinstance(s, TeamsPipelineStore)
