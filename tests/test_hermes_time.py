"""Coverage for ``hermes_time`` — the timezone-aware clock helpers.

No existing direct tests; the module backs every "{{now}}" rendering in
the agent so a bad timezone resolution mis-stamps every log line and
tool response.
"""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def fresh_hermes_time(tmp_path, monkeypatch):
    """Provide a freshly-imported module with HERMES_HOME pointed at tmp.

    The module caches timezone resolution at the module level, so each test
    needs a clean slate.  We monkeypatch HERMES_HOME so config.yaml reads
    don't bleed from the developer's real install.
    """
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv("HERMES_TIMEZONE", raising=False)
    import hermes_time as _mod

    _mod = importlib.reload(_mod)
    return _mod


class TestResolveTimezoneName:
    def test_env_takes_priority(self, fresh_hermes_time, monkeypatch):
        monkeypatch.setenv("HERMES_TIMEZONE", "Asia/Taipei")
        assert fresh_hermes_time._resolve_timezone_name() == "Asia/Taipei"

    def test_env_strips_whitespace(self, fresh_hermes_time, monkeypatch):
        monkeypatch.setenv("HERMES_TIMEZONE", "  Asia/Taipei  ")
        assert fresh_hermes_time._resolve_timezone_name() == "Asia/Taipei"

    def test_empty_env_falls_through_to_config(
        self, fresh_hermes_time, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("HERMES_TIMEZONE", "")
        config_path = tmp_path / "config.yaml"
        config_path.write_text("timezone: Europe/Berlin\n")
        assert fresh_hermes_time._resolve_timezone_name() == "Europe/Berlin"

    def test_returns_empty_when_nothing_configured(self, fresh_hermes_time):
        assert fresh_hermes_time._resolve_timezone_name() == ""

    def test_malformed_config_yaml_does_not_crash(
        self, fresh_hermes_time, tmp_path
    ):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("not: [valid: yaml")
        # The helper swallows YAML errors and returns "".
        assert fresh_hermes_time._resolve_timezone_name() == ""


class TestGetZoneinfo:
    def test_valid_zone_returns_zoneinfo(self, fresh_hermes_time):
        z = fresh_hermes_time._get_zoneinfo("Asia/Taipei")
        assert z is not None

    def test_empty_string_returns_none(self, fresh_hermes_time):
        assert fresh_hermes_time._get_zoneinfo("") is None

    def test_invalid_zone_returns_none_and_logs(self, fresh_hermes_time, caplog):
        with caplog.at_level("WARNING"):
            result = fresh_hermes_time._get_zoneinfo("Mars/Olympus")
        assert result is None
        assert any("Mars/Olympus" in r.message for r in caplog.records)


class TestGetTimezone:
    def test_caches_resolution(self, fresh_hermes_time, monkeypatch):
        monkeypatch.setenv("HERMES_TIMEZONE", "Asia/Taipei")
        first = fresh_hermes_time.get_timezone()
        # Change the env after the first call — cache should win.
        monkeypatch.setenv("HERMES_TIMEZONE", "Europe/Berlin")
        second = fresh_hermes_time.get_timezone()
        assert first is second

    def test_returns_none_when_nothing_configured(self, fresh_hermes_time):
        assert fresh_hermes_time.get_timezone() is None


class TestNow:
    def test_returns_tz_aware_datetime_when_configured(
        self, fresh_hermes_time, monkeypatch
    ):
        monkeypatch.setenv("HERMES_TIMEZONE", "Asia/Taipei")
        dt = fresh_hermes_time.now()
        assert dt.tzinfo is not None
        # Taipei is UTC+8 with no DST.
        assert str(dt.tzinfo) == "Asia/Taipei"

    def test_returns_tz_aware_local_when_nothing_configured(
        self, fresh_hermes_time
    ):
        dt = fresh_hermes_time.now()
        # astimezone() with no argument uses server-local tz; result is aware.
        assert dt.tzinfo is not None

    def test_returns_tz_aware_when_configured_zone_is_invalid(
        self, fresh_hermes_time, monkeypatch, caplog
    ):
        monkeypatch.setenv("HERMES_TIMEZONE", "Mars/Olympus")
        with caplog.at_level("WARNING"):
            dt = fresh_hermes_time.now()
        assert dt.tzinfo is not None  # falls back to server-local
