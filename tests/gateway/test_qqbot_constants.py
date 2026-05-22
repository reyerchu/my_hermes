"""Coverage for gateway.platforms.qqbot.constants — version pins,
endpoint shape, retry/timeout numerics, and message-type enums."""
from __future__ import annotations

import re

import pytest

from gateway.platforms.qqbot import constants as C


class TestVersion:
    def test_semver_shape(self):
        assert re.match(r"^\d+\.\d+\.\d+$", C.QQBOT_VERSION)


class TestApiEndpoints:
    def test_api_base_is_https(self):
        assert C.API_BASE.startswith("https://")
        assert "api.sgroup.qq.com" in C.API_BASE

    def test_token_url(self):
        assert C.TOKEN_URL == "https://bots.qq.com/app/getAppAccessToken"

    def test_gateway_path_is_root_relative(self):
        assert C.GATEWAY_URL_PATH.startswith("/")
        assert C.GATEWAY_URL_PATH == "/gateway"

    def test_portal_host_env_override(self, monkeypatch):
        monkeypatch.setenv("QQ_PORTAL_HOST", "stage.qq.example")
        # Constants module is evaluated at import time, so re-import to
        # capture the override.
        import importlib
        import gateway.platforms.qqbot.constants as fresh
        fresh = importlib.reload(fresh)
        try:
            assert fresh.PORTAL_HOST == "stage.qq.example"
        finally:
            monkeypatch.delenv("QQ_PORTAL_HOST", raising=False)
            importlib.reload(fresh)


class TestOnboardEndpoints:
    def test_onboard_paths_are_root_relative(self):
        assert C.ONBOARD_CREATE_PATH.startswith("/")
        assert C.ONBOARD_POLL_PATH.startswith("/")

    def test_qr_template_carries_task_id_placeholder(self):
        assert "{task_id}" in C.QR_URL_TEMPLATE
        # And the standard "source=hermes" identifier.
        assert "source=hermes" in C.QR_URL_TEMPLATE


class TestTimeouts:
    def test_default_api_timeout(self):
        assert C.DEFAULT_API_TIMEOUT == 30.0

    def test_file_upload_longer_than_default(self):
        assert C.FILE_UPLOAD_TIMEOUT >= C.DEFAULT_API_TIMEOUT

    def test_connect_timeout_positive(self):
        assert C.CONNECT_TIMEOUT_SECONDS > 0

    def test_onboard_poll_interval_positive(self):
        assert C.ONBOARD_POLL_INTERVAL > 0


class TestReconnect:
    def test_backoff_is_monotonic(self):
        # Backoff schedule must be strictly increasing.
        seq = C.RECONNECT_BACKOFF
        assert all(b < a for a, b in zip(seq[1:], seq))

    def test_max_attempts_bounded(self):
        assert isinstance(C.MAX_RECONNECT_ATTEMPTS, int)
        assert C.MAX_RECONNECT_ATTEMPTS > 0

    def test_quick_disconnect_threshold_seconds(self):
        assert isinstance(C.QUICK_DISCONNECT_THRESHOLD, float)
        assert C.QUICK_DISCONNECT_THRESHOLD > 0


class TestMessageLimits:
    def test_max_message_length(self):
        assert C.MAX_MESSAGE_LENGTH == 4000

    def test_dedup_window(self):
        assert C.DEDUP_WINDOW_SECONDS == 300

    def test_dedup_max_size_positive(self):
        assert C.DEDUP_MAX_SIZE > 0


class TestEnums:
    def test_message_types_distinct(self):
        types = {C.MSG_TYPE_TEXT, C.MSG_TYPE_MARKDOWN, C.MSG_TYPE_MEDIA, C.MSG_TYPE_INPUT_NOTIFY}
        assert len(types) == 4

    def test_message_types_pinned(self):
        # The QQ Bot API hardcodes these wire values — they must not drift.
        assert C.MSG_TYPE_TEXT == 0
        assert C.MSG_TYPE_MARKDOWN == 2
        assert C.MSG_TYPE_MEDIA == 7
        assert C.MSG_TYPE_INPUT_NOTIFY == 6

    def test_media_types_pinned(self):
        assert C.MEDIA_TYPE_IMAGE == 1
        assert C.MEDIA_TYPE_VIDEO == 2
        assert C.MEDIA_TYPE_VOICE == 3
        assert C.MEDIA_TYPE_FILE == 4

    def test_media_types_distinct(self):
        types = {C.MEDIA_TYPE_IMAGE, C.MEDIA_TYPE_VIDEO, C.MEDIA_TYPE_VOICE, C.MEDIA_TYPE_FILE}
        assert len(types) == 4
