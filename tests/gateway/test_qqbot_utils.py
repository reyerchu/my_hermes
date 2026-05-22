"""Coverage for ``gateway.platforms.qqbot.utils``.

Three exported helpers, all pure: User-Agent builder, API-headers dict,
config-value coercer.  No direct tests previously."""
from __future__ import annotations

import platform
import sys

from gateway.platforms.qqbot.constants import QQBOT_VERSION
from gateway.platforms.qqbot.utils import (
    build_user_agent,
    coerce_list,
    get_api_headers,
)


class TestBuildUserAgent:
    def test_includes_qqbot_version_prefix(self):
        ua = build_user_agent()
        assert ua.startswith(f"QQBotAdapter/{QQBOT_VERSION}")

    def test_contains_python_version(self):
        ua = build_user_agent()
        py = f"{sys.version_info.major}.{sys.version_info.minor}"
        assert py in ua

    def test_contains_os_name(self):
        ua = build_user_agent()
        assert platform.system().lower() in ua

    def test_contains_hermes_tag(self):
        ua = build_user_agent()
        assert "Hermes/" in ua


class TestGetApiHeaders:
    def test_returns_required_keys(self):
        headers = get_api_headers()
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert headers["User-Agent"].startswith("QQBotAdapter/")


class TestCoerceList:
    def test_none_returns_empty_list(self):
        assert coerce_list(None) == []

    def test_comma_separated_string(self):
        assert coerce_list("a,b,c") == ["a", "b", "c"]

    def test_strips_whitespace_around_each_item(self):
        assert coerce_list(" a , b , c ") == ["a", "b", "c"]

    def test_drops_empty_items_from_csv(self):
        assert coerce_list("a, ,b,") == ["a", "b"]

    def test_list_input_passes_through_stripped(self):
        assert coerce_list([" a", "b "]) == ["a", "b"]

    def test_tuple_input_works(self):
        assert coerce_list(("x", "y")) == ["x", "y"]

    def test_set_input_works(self):
        # Sets are unordered — assert membership not order.
        result = coerce_list({"x", "y"})
        assert sorted(result) == ["x", "y"]

    def test_drops_empty_items_from_list(self):
        assert coerce_list(["a", "", "b", "  "]) == ["a", "b"]

    def test_scalar_value_wrapped_in_list(self):
        assert coerce_list(42) == ["42"]

    def test_scalar_value_empty_string_returns_empty_list(self):
        assert coerce_list("") == []
        assert coerce_list("   ") == []
