"""Coverage for pure helpers in tools.browser_providers.browser_use:
- _get_or_create_pending_create_key / _clear_pending_create_key
- _should_preserve_pending_create_key
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import tools.browser_providers.browser_use as bu


@pytest.fixture(autouse=True)
def _clear_pending():
    """Reset the module-level pending-keys map between tests."""
    with bu._pending_create_keys_lock:
        bu._pending_create_keys.clear()
    yield
    with bu._pending_create_keys_lock:
        bu._pending_create_keys.clear()


class TestPendingCreateKey:
    def test_first_call_creates_key(self):
        out = bu._get_or_create_pending_create_key("task-1")
        assert out.startswith("browser-use-session-create:")
        # 32-char hex suffix
        suffix = out.split(":", 1)[1]
        assert len(suffix) == 32

    def test_second_call_returns_same_key(self):
        a = bu._get_or_create_pending_create_key("task-1")
        b = bu._get_or_create_pending_create_key("task-1")
        assert a == b

    def test_different_tasks_get_different_keys(self):
        a = bu._get_or_create_pending_create_key("task-1")
        b = bu._get_or_create_pending_create_key("task-2")
        assert a != b

    def test_clear_pending_removes_entry(self):
        a = bu._get_or_create_pending_create_key("task-1")
        bu._clear_pending_create_key("task-1")
        b = bu._get_or_create_pending_create_key("task-1")
        # After clear, a fresh key is generated.
        assert a != b

    def test_clear_unknown_is_safe(self):
        # Doesn't raise on missing key.
        bu._clear_pending_create_key("nonexistent")


class TestShouldPreservePendingCreateKey:
    def _resp(self, status, body=None, json_raises=False):
        r = MagicMock()
        r.status_code = status
        if json_raises:
            r.json.side_effect = ValueError("bad")
        else:
            r.json.return_value = body or {}
        return r

    def test_500_preserved(self):
        assert bu._should_preserve_pending_create_key(self._resp(500)) is True

    def test_503_preserved(self):
        assert bu._should_preserve_pending_create_key(self._resp(503)) is True

    def test_400_not_preserved(self):
        assert bu._should_preserve_pending_create_key(self._resp(400)) is False

    def test_200_not_preserved(self):
        assert bu._should_preserve_pending_create_key(self._resp(200)) is False

    def test_409_already_in_progress_preserved(self):
        r = self._resp(
            409,
            body={"error": {"message": "Session already in progress for task X"}},
        )
        assert bu._should_preserve_pending_create_key(r) is True

    def test_409_other_message_not_preserved(self):
        r = self._resp(
            409,
            body={"error": {"message": "Conflict with quota"}},
        )
        assert bu._should_preserve_pending_create_key(r) is False

    def test_409_no_error_dict_not_preserved(self):
        r = self._resp(409, body={"error": "not-a-dict"})
        assert bu._should_preserve_pending_create_key(r) is False

    def test_409_json_raises_not_preserved(self):
        r = self._resp(409, json_raises=True)
        assert bu._should_preserve_pending_create_key(r) is False

    def test_409_non_dict_payload_not_preserved(self):
        r = self._resp(409, body=["unexpected", "list"])
        assert bu._should_preserve_pending_create_key(r) is False

    def test_409_case_insensitive_match(self):
        r = self._resp(
            409,
            body={"error": {"message": "REQUEST ALREADY IN PROGRESS"}},
        )
        assert bu._should_preserve_pending_create_key(r) is True


class TestProviderIdentity:
    def test_name(self):
        assert bu.BrowserUseProvider().provider_name() == "Browser Use"


class TestConstants:
    def test_default_managed_timeout(self):
        assert bu._DEFAULT_MANAGED_TIMEOUT_MINUTES == 5

    def test_default_proxy_country(self):
        assert bu._DEFAULT_MANAGED_PROXY_COUNTRY_CODE == "us"

    def test_base_url(self):
        assert bu._BASE_URL.endswith("/v3")
