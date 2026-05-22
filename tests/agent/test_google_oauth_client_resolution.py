"""Coverage for ``_get_client_id`` / ``_get_client_secret`` in
``agent.google_oauth`` — the OAuth client credential resolution chain."""
from __future__ import annotations

import pytest

from agent.google_oauth import (
    ENV_CLIENT_ID,
    ENV_CLIENT_SECRET,
    _get_client_id,
    _get_client_secret,
)


class TestGetClientId:
    def test_env_override_wins(self, monkeypatch):
        monkeypatch.setenv(ENV_CLIENT_ID, "custom-client-id.apps.googleusercontent.com")
        assert _get_client_id() == "custom-client-id.apps.googleusercontent.com"

    def test_strips_whitespace_from_env(self, monkeypatch):
        monkeypatch.setenv(ENV_CLIENT_ID, "  custom-id  ")
        assert _get_client_id() == "custom-id"

    def test_falls_back_to_public_default(self, monkeypatch):
        monkeypatch.delenv(ENV_CLIENT_ID, raising=False)
        out = _get_client_id()
        # The public gemini-cli desktop client id ends with this suffix.
        assert out.endswith(".apps.googleusercontent.com")

    def test_empty_env_falls_back(self, monkeypatch):
        monkeypatch.setenv(ENV_CLIENT_ID, "")
        out = _get_client_id()
        assert out.endswith(".apps.googleusercontent.com")


class TestGetClientSecret:
    def test_env_override_wins(self, monkeypatch):
        monkeypatch.setenv(ENV_CLIENT_SECRET, "GOCSPX-OVERRIDE")
        assert _get_client_secret() == "GOCSPX-OVERRIDE"

    def test_strips_whitespace_from_env(self, monkeypatch):
        monkeypatch.setenv(ENV_CLIENT_SECRET, "  GOCSPX-X  ")
        assert _get_client_secret() == "GOCSPX-X"

    def test_falls_back_to_public_default(self, monkeypatch):
        monkeypatch.delenv(ENV_CLIENT_SECRET, raising=False)
        out = _get_client_secret()
        # The shipped default starts with the well-known prefix.
        assert out.startswith("GOCSPX-")

    def test_empty_env_falls_back(self, monkeypatch):
        monkeypatch.setenv(ENV_CLIENT_SECRET, "")
        out = _get_client_secret()
        assert out.startswith("GOCSPX-")
