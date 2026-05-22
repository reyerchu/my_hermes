"""Coverage for ``gateway.session_context`` — the contextvars-based
session state.  This module gates which session every concurrent
message-handler is running under, so a regression silently mis-routes
notifications.  No existing direct tests.
"""
from __future__ import annotations

import asyncio
import os

import pytest

from gateway.session_context import (
    clear_session_vars,
    get_session_env,
    set_session_vars,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    # Strip every legacy HERMES_SESSION_* env so the os.getenv fallback
    # is observable in test cases that exercise it.
    for var in (
        "HERMES_SESSION_PLATFORM",
        "HERMES_SESSION_CHAT_ID",
        "HERMES_SESSION_CHAT_NAME",
        "HERMES_SESSION_THREAD_ID",
        "HERMES_SESSION_USER_ID",
        "HERMES_SESSION_USER_NAME",
        "HERMES_SESSION_KEY",
        "HERMES_SESSION_ID",
        "HERMES_CRON_AUTO_DELIVER_PLATFORM",
        "HERMES_CRON_AUTO_DELIVER_CHAT_ID",
        "HERMES_CRON_AUTO_DELIVER_THREAD_ID",
    ):
        monkeypatch.delenv(var, raising=False)


class TestGetSessionEnvFallback:
    def test_returns_default_when_nothing_set(self):
        assert get_session_env("HERMES_SESSION_PLATFORM") == ""
        assert get_session_env("HERMES_SESSION_PLATFORM", "fb") == "fb"

    def test_falls_back_to_os_environ_when_contextvar_unset(self, monkeypatch):
        monkeypatch.setenv("HERMES_SESSION_PLATFORM", "telegram")
        assert get_session_env("HERMES_SESSION_PLATFORM") == "telegram"

    def test_unknown_name_uses_os_environ_directly(self, monkeypatch):
        monkeypatch.setenv("NOT_A_HERMES_VAR", "x")
        assert get_session_env("NOT_A_HERMES_VAR") == "x"
        assert get_session_env("MISSING_VAR", "fb") == "fb"


class TestSetSessionVars:
    def test_values_visible_via_get_session_env(self):
        async def main():
            set_session_vars(
                platform="telegram",
                chat_id="C1",
                chat_name="N",
                thread_id="T",
                user_id="U1",
                user_name="bob",
                session_key="sk",
            )
            assert get_session_env("HERMES_SESSION_PLATFORM") == "telegram"
            assert get_session_env("HERMES_SESSION_CHAT_ID") == "C1"
            assert get_session_env("HERMES_SESSION_USER_NAME") == "bob"

        asyncio.run(main())

    def test_contextvar_wins_over_os_environ(self, monkeypatch):
        monkeypatch.setenv("HERMES_SESSION_PLATFORM", "from_env")

        async def main():
            set_session_vars(platform="from_contextvar")
            assert get_session_env("HERMES_SESSION_PLATFORM") == (
                "from_contextvar"
            )

        asyncio.run(main())

    def test_empty_value_is_not_a_fallback_trigger(self, monkeypatch):
        # Explicit "" via set_session_vars must NOT fall through to env.
        monkeypatch.setenv("HERMES_SESSION_PLATFORM", "from_env")

        async def main():
            set_session_vars(platform="")
            assert get_session_env("HERMES_SESSION_PLATFORM") == ""

        asyncio.run(main())


class TestClearSessionVars:
    def test_clears_all_session_keys_to_empty_string(self):
        async def main():
            tokens = set_session_vars(
                platform="telegram", chat_id="C1", user_name="bob",
            )
            clear_session_vars(tokens)
            assert get_session_env("HERMES_SESSION_PLATFORM") == ""
            assert get_session_env("HERMES_SESSION_CHAT_ID") == ""
            assert get_session_env("HERMES_SESSION_USER_NAME") == ""

        asyncio.run(main())

    def test_after_clear_env_is_still_NOT_consulted(self, monkeypatch):
        monkeypatch.setenv("HERMES_SESSION_PLATFORM", "leaked")

        async def main():
            tokens = set_session_vars(platform="telegram")
            clear_session_vars(tokens)
            # Contextvar is now "" (explicit) → no env fallback.
            assert get_session_env("HERMES_SESSION_PLATFORM") == ""

        asyncio.run(main())


class TestConcurrencyIsolation:
    def test_two_concurrent_tasks_see_different_session_values(self):
        results: dict[str, str] = {}

        async def worker(name: str, platform: str):
            set_session_vars(platform=platform)
            # Yield control so the two workers interleave and prove the
            # contextvars are task-local.
            await asyncio.sleep(0)
            results[name] = get_session_env("HERMES_SESSION_PLATFORM")

        async def main():
            await asyncio.gather(
                worker("a", "telegram"),
                worker("b", "discord"),
            )

        asyncio.run(main())
        assert results["a"] == "telegram"
        assert results["b"] == "discord"
