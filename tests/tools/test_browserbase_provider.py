"""Coverage for BrowserbaseProvider browser session lifecycle."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tools.browser_providers.browserbase import BrowserbaseProvider


@pytest.fixture
def provider():
    return BrowserbaseProvider()


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for var in (
        "BROWSERBASE_API_KEY", "BROWSERBASE_PROJECT_ID", "BROWSERBASE_BASE_URL",
        "BROWSERBASE_PROXIES", "BROWSERBASE_ADVANCED_STEALTH",
        "BROWSERBASE_KEEP_ALIVE", "BROWSERBASE_SESSION_TIMEOUT",
    ):
        monkeypatch.delenv(var, raising=False)


class TestIdentity:
    def test_name(self, provider):
        assert provider.provider_name() == "Browserbase"


class TestConfig:
    def test_requires_both_credentials(self, provider, monkeypatch):
        monkeypatch.setenv("BROWSERBASE_API_KEY", "k")
        # PROJECT_ID still missing → not configured
        assert provider.is_configured() is False

    def test_present_when_both_set(self, provider, monkeypatch):
        monkeypatch.setenv("BROWSERBASE_API_KEY", "k")
        monkeypatch.setenv("BROWSERBASE_PROJECT_ID", "p")
        assert provider.is_configured() is True

    def test_base_url_default(self, provider, monkeypatch):
        monkeypatch.setenv("BROWSERBASE_API_KEY", "k")
        monkeypatch.setenv("BROWSERBASE_PROJECT_ID", "p")
        cfg = provider._get_config_or_none()
        assert cfg["base_url"] == "https://api.browserbase.com"

    def test_base_url_override_strips_trailing_slash(self, provider, monkeypatch):
        monkeypatch.setenv("BROWSERBASE_API_KEY", "k")
        monkeypatch.setenv("BROWSERBASE_PROJECT_ID", "p")
        monkeypatch.setenv("BROWSERBASE_BASE_URL", "https://eu.browserbase.example/")
        cfg = provider._get_config_or_none()
        assert cfg["base_url"] == "https://eu.browserbase.example"

    def test_get_config_raises_when_missing(self, provider):
        with pytest.raises(ValueError, match="BROWSERBASE_API_KEY"):
            provider._get_config()


def _make_response(status=200, body=None, ok=None):
    r = MagicMock()
    r.status_code = status
    r.ok = ok if ok is not None else (status < 400)
    r.json.return_value = body or {"id": "sess-1", "connectUrl": "wss://cdp"}
    r.text = ""
    return r


class TestCreateSession:
    def _setup_creds(self, monkeypatch):
        monkeypatch.setenv("BROWSERBASE_API_KEY", "k")
        monkeypatch.setenv("BROWSERBASE_PROJECT_ID", "proj-1")

    def test_basic_create(self, provider, monkeypatch):
        self._setup_creds(monkeypatch)
        with patch(
            "tools.browser_providers.browserbase.requests.post",
            return_value=_make_response(),
        ):
            out = provider.create_session("t1")
        assert out["bb_session_id"] == "sess-1"
        assert out["cdp_url"] == "wss://cdp"
        assert out["session_name"].startswith("hermes_t1_")
        # features dict reports all enabled flags
        assert out["features"]["proxies"] is True  # proxies default-true
        assert out["features"]["keep_alive"] is True

    def test_proxies_disabled_via_env(self, provider, monkeypatch):
        self._setup_creds(monkeypatch)
        monkeypatch.setenv("BROWSERBASE_PROXIES", "false")
        captured = {}
        def _post(url, headers, json, timeout):
            captured.update(json)
            return _make_response()
        with patch("tools.browser_providers.browserbase.requests.post", side_effect=_post):
            out = provider.create_session("t1")
        assert "proxies" not in captured
        assert out["features"]["proxies"] is False

    def test_advanced_stealth_enabled(self, provider, monkeypatch):
        self._setup_creds(monkeypatch)
        monkeypatch.setenv("BROWSERBASE_ADVANCED_STEALTH", "true")
        captured = {}
        def _post(url, headers, json, timeout):
            captured.update(json)
            return _make_response()
        with patch("tools.browser_providers.browserbase.requests.post", side_effect=_post):
            out = provider.create_session("t1")
        assert captured.get("browserSettings", {}).get("advancedStealth") is True
        assert out["features"]["advanced_stealth"] is True

    def test_custom_timeout_positive(self, provider, monkeypatch):
        self._setup_creds(monkeypatch)
        monkeypatch.setenv("BROWSERBASE_SESSION_TIMEOUT", "600000")
        captured = {}
        def _post(url, headers, json, timeout):
            captured.update(json)
            return _make_response()
        with patch("tools.browser_providers.browserbase.requests.post", side_effect=_post):
            out = provider.create_session("t1")
        assert captured.get("timeout") == 600000
        assert out["features"]["custom_timeout"] is True

    def test_custom_timeout_invalid_warns_no_set(self, provider, monkeypatch):
        self._setup_creds(monkeypatch)
        monkeypatch.setenv("BROWSERBASE_SESSION_TIMEOUT", "not-a-number")
        captured = {}
        def _post(url, headers, json, timeout):
            captured.update(json)
            return _make_response()
        with patch("tools.browser_providers.browserbase.requests.post", side_effect=_post):
            out = provider.create_session("t1")
        assert "timeout" not in captured
        assert out["features"]["custom_timeout"] is False

    def test_402_falls_back_keepalive(self, provider, monkeypatch):
        self._setup_creds(monkeypatch)
        # Sequence: first POST 402 → drop keepAlive → 200
        responses = iter([_make_response(status=402), _make_response()])
        with patch(
            "tools.browser_providers.browserbase.requests.post",
            side_effect=lambda *a, **kw: next(responses),
        ):
            out = provider.create_session("t1")
        assert out["features"]["keep_alive"] is False

    def test_non_ok_raises(self, provider, monkeypatch):
        self._setup_creds(monkeypatch)
        bad = _make_response(status=500, ok=False)
        bad.text = "server error"
        with patch("tools.browser_providers.browserbase.requests.post", return_value=bad):
            with pytest.raises(RuntimeError, match="500"):
                provider.create_session("t1")


class TestCloseSession:
    def test_returns_false_no_creds(self, provider):
        assert provider.close_session("sess-1") is False

    def test_success(self, provider, monkeypatch):
        monkeypatch.setenv("BROWSERBASE_API_KEY", "k")
        monkeypatch.setenv("BROWSERBASE_PROJECT_ID", "p")
        with patch(
            "tools.browser_providers.browserbase.requests.post",
            return_value=_make_response(status=204),
        ):
            assert provider.close_session("sess-1") is True

    def test_failure_status(self, provider, monkeypatch):
        monkeypatch.setenv("BROWSERBASE_API_KEY", "k")
        monkeypatch.setenv("BROWSERBASE_PROJECT_ID", "p")
        with patch(
            "tools.browser_providers.browserbase.requests.post",
            return_value=_make_response(status=500, ok=False),
        ):
            assert provider.close_session("sess-1") is False

    def test_exception_returns_false(self, provider, monkeypatch):
        monkeypatch.setenv("BROWSERBASE_API_KEY", "k")
        monkeypatch.setenv("BROWSERBASE_PROJECT_ID", "p")
        with patch(
            "tools.browser_providers.browserbase.requests.post",
            side_effect=RuntimeError("net"),
        ):
            assert provider.close_session("sess-1") is False


class TestEmergencyCleanup:
    def test_no_creds_is_noop(self, provider):
        # Just must not raise.
        provider.emergency_cleanup("sess-1")

    def test_swallows_exception(self, provider, monkeypatch):
        monkeypatch.setenv("BROWSERBASE_API_KEY", "k")
        monkeypatch.setenv("BROWSERBASE_PROJECT_ID", "p")
        with patch(
            "tools.browser_providers.browserbase.requests.post",
            side_effect=RuntimeError("boom"),
        ):
            provider.emergency_cleanup("sess-1")

    def test_normal_post_called(self, provider, monkeypatch):
        monkeypatch.setenv("BROWSERBASE_API_KEY", "k")
        monkeypatch.setenv("BROWSERBASE_PROJECT_ID", "p")
        with patch("tools.browser_providers.browserbase.requests.post") as post:
            provider.emergency_cleanup("sess-x")
        post.assert_called_once()
        args, kwargs = post.call_args
        assert args[0].endswith("/v1/sessions/sess-x")
        body = kwargs["json"]
        assert body["status"] == "REQUEST_RELEASE"
        assert body["projectId"] == "p"
