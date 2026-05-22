"""Gap coverage for the small env/proxy/json helpers in ``utils.py``.

These functions are referenced from a dozen call sites (gateway, providers,
hermes_cli) but only ``is_truthy_value`` and the URL helpers were tested
directly.  This file covers ``env_int``, ``env_bool``, ``safe_json_loads``,
``normalize_proxy_url``, and ``normalize_proxy_env_vars`` end-to-end.
"""
from __future__ import annotations

import pytest

from utils import (
    env_bool,
    env_int,
    is_truthy_value,
    normalize_proxy_env_vars,
    normalize_proxy_url,
    safe_json_loads,
)


# ─── env_int ──────────────────────────────────────────────────────────────


class TestEnvInt:
    def test_returns_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("X_HERMES_TEST", raising=False)
        assert env_int("X_HERMES_TEST", default=42) == 42

    def test_returns_default_when_empty(self, monkeypatch):
        monkeypatch.setenv("X_HERMES_TEST", "")
        assert env_int("X_HERMES_TEST", default=7) == 7

    def test_returns_default_when_whitespace(self, monkeypatch):
        monkeypatch.setenv("X_HERMES_TEST", "   ")
        assert env_int("X_HERMES_TEST", default=7) == 7

    def test_parses_a_valid_integer(self, monkeypatch):
        monkeypatch.setenv("X_HERMES_TEST", "123")
        assert env_int("X_HERMES_TEST") == 123

    def test_negative_integers(self, monkeypatch):
        monkeypatch.setenv("X_HERMES_TEST", "-5")
        assert env_int("X_HERMES_TEST") == -5

    def test_strips_surrounding_whitespace(self, monkeypatch):
        monkeypatch.setenv("X_HERMES_TEST", "  42  ")
        assert env_int("X_HERMES_TEST") == 42

    def test_falls_back_on_non_integer(self, monkeypatch):
        monkeypatch.setenv("X_HERMES_TEST", "not-a-number")
        assert env_int("X_HERMES_TEST", default=99) == 99


# ─── env_bool ──────────────────────────────────────────────────────────────


class TestEnvBool:
    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " True "])
    def test_truthy_strings_evaluate_true(self, monkeypatch, value):
        monkeypatch.setenv("X_HERMES_TEST", value)
        assert env_bool("X_HERMES_TEST") is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", "asdf"])
    def test_falsy_or_unknown_strings_evaluate_false(self, monkeypatch, value):
        monkeypatch.setenv("X_HERMES_TEST", value)
        assert env_bool("X_HERMES_TEST") is False

    def test_unset_returns_false_regardless_of_default(self, monkeypatch):
        # env_bool defers to is_truthy_value with an empty-string default,
        # which only honours the `default` arg for `None` input.  An
        # unset env var therefore evaluates False even when default=True.
        monkeypatch.delenv("X_HERMES_TEST", raising=False)
        assert env_bool("X_HERMES_TEST", default=True) is False
        assert env_bool("X_HERMES_TEST", default=False) is False


# ─── is_truthy_value ───────────────────────────────────────────────────────


class TestIsTruthyValue:
    def test_native_booleans(self):
        assert is_truthy_value(True) is True
        assert is_truthy_value(False) is False

    def test_none_uses_default(self):
        assert is_truthy_value(None, default=True) is True
        assert is_truthy_value(None, default=False) is False

    @pytest.mark.parametrize("value", ["1", "true", "yes", "ON", "TRUE"])
    def test_truthy_strings(self, value):
        assert is_truthy_value(value) is True

    def test_unknown_strings_are_false(self):
        assert is_truthy_value("maybe") is False

    def test_numeric_values_coerce(self):
        assert is_truthy_value(1) is True
        assert is_truthy_value(0) is False


# ─── safe_json_loads ───────────────────────────────────────────────────────


class TestSafeJsonLoads:
    def test_valid_json_object(self):
        assert safe_json_loads('{"a": 1}') == {"a": 1}

    def test_valid_json_array(self):
        assert safe_json_loads("[1, 2, 3]") == [1, 2, 3]

    def test_valid_json_primitive(self):
        assert safe_json_loads("42") == 42
        assert safe_json_loads('"hi"') == "hi"
        assert safe_json_loads("true") is True
        assert safe_json_loads("null") is None

    def test_invalid_json_returns_default(self):
        assert safe_json_loads("not json", default="fallback") == "fallback"

    def test_none_default_is_returned_for_invalid_input(self):
        assert safe_json_loads("oh no") is None

    def test_non_string_input_returns_default(self):
        # json.loads on non-string raises TypeError, which the helper swallows.
        assert safe_json_loads(None, default={"x": 1}) == {"x": 1}  # type: ignore[arg-type]
        assert safe_json_loads(123, default=[]) == []  # type: ignore[arg-type]


# ─── normalize_proxy_url ───────────────────────────────────────────────────


class TestNormalizeProxyUrl:
    def test_none_returns_none(self):
        assert normalize_proxy_url(None) is None

    def test_empty_string_returns_none(self):
        assert normalize_proxy_url("") is None

    def test_whitespace_only_returns_none(self):
        assert normalize_proxy_url("   ") is None

    def test_socks_alias_rewritten_to_socks5(self):
        assert (
            normalize_proxy_url("socks://127.0.0.1:1080")
            == "socks5://127.0.0.1:1080"
        )

    def test_socks_alias_case_insensitive(self):
        assert (
            normalize_proxy_url("SOCKS://127.0.0.1:1080")
            == "socks5://127.0.0.1:1080"
        )

    def test_explicit_socks5_passthrough(self):
        assert (
            normalize_proxy_url("socks5://127.0.0.1:1080")
            == "socks5://127.0.0.1:1080"
        )

    def test_http_proxy_passthrough(self):
        assert (
            normalize_proxy_url("http://proxy.example:8080")
            == "http://proxy.example:8080"
        )

    def test_https_proxy_passthrough(self):
        assert (
            normalize_proxy_url("https://proxy.example:443")
            == "https://proxy.example:443"
        )

    def test_strips_surrounding_whitespace(self):
        assert (
            normalize_proxy_url("  http://proxy.example  ")
            == "http://proxy.example"
        )


class TestNormalizeProxyEnvVars:
    def test_rewrites_socks_alias_in_supported_keys(self, monkeypatch):
        monkeypatch.setenv("HTTPS_PROXY", "socks://1.2.3.4:1080")
        monkeypatch.setenv("http_proxy", "socks://5.6.7.8:1080")
        normalize_proxy_env_vars()
        import os
        assert os.environ["HTTPS_PROXY"] == "socks5://1.2.3.4:1080"
        assert os.environ["http_proxy"] == "socks5://5.6.7.8:1080"

    def test_leaves_canonical_values_alone(self, monkeypatch):
        monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example:8080")
        normalize_proxy_env_vars()
        import os
        assert os.environ["HTTPS_PROXY"] == "http://proxy.example:8080"

    def test_unset_env_remains_unset(self, monkeypatch):
        for key in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY",
                    "https_proxy", "http_proxy", "all_proxy"):
            monkeypatch.delenv(key, raising=False)
        # Function must not crash when nothing is set.
        normalize_proxy_env_vars()
        import os
        assert "HTTPS_PROXY" not in os.environ
