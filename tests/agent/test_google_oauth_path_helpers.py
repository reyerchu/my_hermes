"""Coverage for path helpers and the _is_headless predicate in
``agent.google_oauth``."""
from __future__ import annotations

import pytest

from agent.google_oauth import (
    _credentials_path,
    _is_headless,
    _lock_path,
)


class TestCredentialsPath:
    def test_under_hermes_home_auth(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        p = _credentials_path()
        assert p == tmp_path / "auth" / "google_oauth.json"

    def test_returns_path_object(self):
        from pathlib import Path
        assert isinstance(_credentials_path(), Path)


class TestLockPath:
    def test_derived_from_credentials_path(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        cred = _credentials_path()
        lock = _lock_path()
        # The lock sits next to the credentials file with .json.lock suffix.
        assert lock.parent == cred.parent
        assert str(lock).endswith(".json.lock")


class TestIsHeadless:
    @pytest.fixture(autouse=True)
    def _clean_env(self, monkeypatch):
        for k in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY", "HERMES_HEADLESS"):
            monkeypatch.delenv(k, raising=False)

    def test_default_no_ssh_vars_means_not_headless(self):
        assert _is_headless() is False

    @pytest.mark.parametrize("env_var", [
        "SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY", "HERMES_HEADLESS",
    ])
    def test_any_marker_triggers_headless(self, monkeypatch, env_var):
        monkeypatch.setenv(env_var, "1")
        assert _is_headless() is True

    def test_explicit_empty_value_treated_as_not_set(self, monkeypatch):
        monkeypatch.setenv("SSH_CONNECTION", "")
        # os.getenv returns ""; falsy → not headless.
        assert _is_headless() is False
