"""Coverage for ``hermes_cli.vercel_auth.describe_vercel_auth``.

Surfaces the user-visible auth status for the Vercel Sandbox tool.  The
function has four distinct branches (OIDC, complete access-token,
partial, none) plus the "OIDC + extras" combination — all should be
pinned so a sandbox-setup CLI output regression is caught immediately.
"""
from __future__ import annotations

import pytest

from hermes_cli.vercel_auth import VercelAuthStatus, describe_vercel_auth


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in (
        "VERCEL_OIDC_TOKEN",
        "VERCEL_TOKEN",
        "VERCEL_PROJECT_ID",
        "VERCEL_TEAM_ID",
    ):
        monkeypatch.delenv(var, raising=False)


class TestDescribeVercelAuth:
    def test_not_configured_when_all_vars_absent(self):
        status = describe_vercel_auth()
        assert isinstance(status, VercelAuthStatus)
        assert status.ok is False
        assert status.label == "not configured"
        assert any("recommended" in line for line in status.detail_lines)

    def test_oidc_only_is_ok(self, monkeypatch):
        monkeypatch.setenv("VERCEL_OIDC_TOKEN", "t")
        status = describe_vercel_auth()
        assert status.ok is True
        assert "OIDC" in status.label
        assert any("development-only" in line for line in status.detail_lines)
        # No "also present:" line when no access-token vars are set.
        assert not any("also present" in line for line in status.detail_lines)

    def test_oidc_with_access_token_vars_lists_extras(self, monkeypatch):
        monkeypatch.setenv("VERCEL_OIDC_TOKEN", "t")
        monkeypatch.setenv("VERCEL_TOKEN", "v")
        monkeypatch.setenv("VERCEL_PROJECT_ID", "p")
        status = describe_vercel_auth()
        assert status.ok is True
        assert any("also present" in line for line in status.detail_lines)

    def test_complete_access_token_is_ok(self, monkeypatch):
        monkeypatch.setenv("VERCEL_TOKEN", "v")
        monkeypatch.setenv("VERCEL_PROJECT_ID", "p")
        monkeypatch.setenv("VERCEL_TEAM_ID", "team")
        status = describe_vercel_auth()
        assert status.ok is True
        assert "access token" in status.label
        assert any("VERCEL_TOKEN" in line for line in status.detail_lines)

    def test_partial_access_token_is_not_ok(self, monkeypatch):
        monkeypatch.setenv("VERCEL_TOKEN", "v")
        # Missing PROJECT_ID and TEAM_ID
        status = describe_vercel_auth()
        assert status.ok is False
        assert "partial" in status.label
        assert "VERCEL_PROJECT_ID" in status.label
        assert "VERCEL_TEAM_ID" in status.label

    def test_dataclass_is_frozen(self):
        status = describe_vercel_auth()
        with pytest.raises(Exception):
            status.ok = True  # type: ignore[misc]
