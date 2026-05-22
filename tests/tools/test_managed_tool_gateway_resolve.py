"""Coverage for ``tools.managed_tool_gateway.resolve_managed_tool_gateway``
and ``is_managed_tool_gateway_ready``.  We exercise these through the
public dependency-injection seams so we don't need real auth/env."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from tools.managed_tool_gateway import (
    ManagedToolGatewayConfig,
    is_managed_tool_gateway_ready,
    resolve_managed_tool_gateway,
)


def _patch_managed_enabled(value: bool):
    return patch(
        "tools.managed_tool_gateway.managed_nous_tools_enabled",
        return_value=value,
    )


class TestResolveManagedToolGateway:
    def test_returns_none_when_managed_mode_disabled(self):
        with _patch_managed_enabled(False):
            out = resolve_managed_tool_gateway("vercel")
        assert out is None

    def test_returns_none_when_token_missing(self):
        with _patch_managed_enabled(True):
            out = resolve_managed_tool_gateway(
                "vercel",
                gateway_builder=lambda v: f"https://{v}-gateway.example",
                token_reader=lambda: None,
            )
        assert out is None

    def test_returns_none_when_gateway_url_blank(self):
        with _patch_managed_enabled(True):
            out = resolve_managed_tool_gateway(
                "vercel",
                gateway_builder=lambda v: "",
                token_reader=lambda: "tok",
            )
        assert out is None

    def test_returns_config_when_all_inputs_present(self):
        with _patch_managed_enabled(True):
            out = resolve_managed_tool_gateway(
                "vercel",
                gateway_builder=lambda v: f"https://{v}-gateway.example",
                token_reader=lambda: "tok-123",
            )
        assert isinstance(out, ManagedToolGatewayConfig)
        assert out.vendor == "vercel"
        assert out.gateway_origin == "https://vercel-gateway.example"
        assert out.nous_user_token == "tok-123"
        assert out.managed_mode is True

    def test_config_is_frozen(self):
        with _patch_managed_enabled(True):
            cfg = resolve_managed_tool_gateway(
                "vercel",
                gateway_builder=lambda v: f"https://{v}-gateway.example",
                token_reader=lambda: "tok",
            )
        assert cfg is not None
        with pytest.raises(Exception):
            cfg.vendor = "other"  # type: ignore[misc]


class TestIsManagedToolGatewayReady:
    def test_true_when_resolve_returns_config(self):
        with _patch_managed_enabled(True):
            out = is_managed_tool_gateway_ready(
                "vercel",
                gateway_builder=lambda v: f"https://{v}-gateway.example",
                token_reader=lambda: "tok",
            )
        assert out is True

    def test_false_when_managed_disabled(self):
        with _patch_managed_enabled(False):
            out = is_managed_tool_gateway_ready("vercel")
        assert out is False
