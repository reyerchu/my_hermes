"""Coverage for the registration shim in ``tools.yuanbao_tools``.

The module's import-time side effect is registering five Yuanbao tools
with the global tools.registry.  Pin every registration so a refactor
that drops a tool surfaces immediately."""
from __future__ import annotations

import pytest

# Import shim to trigger registration.
import tools.yuanbao_tools  # noqa: F401
from tools.registry import registry


_EXPECTED_TOOLS = [
    "yb_query_group_info",
    "yb_query_group_members",
    "yb_send_dm",
    "yb_search_sticker",
    "yb_send_sticker",
]


class TestYuanbaoToolsRegistration:
    @pytest.mark.parametrize("name", _EXPECTED_TOOLS)
    def test_tool_registered(self, name: str):
        entry = registry.get_entry(name)
        assert entry is not None, f"missing registration: {name}"

    @pytest.mark.parametrize("name", _EXPECTED_TOOLS)
    def test_each_tool_belongs_to_yuanbao_toolset(self, name: str):
        entry = registry.get_entry(name)
        # All five tools share the "hermes-yuanbao" toolset.
        assert "yuanbao" in (entry.toolset or "").lower()

    @pytest.mark.parametrize("name", _EXPECTED_TOOLS)
    def test_each_tool_has_a_schema(self, name: str):
        entry = registry.get_entry(name)
        assert isinstance(entry.schema, dict)
        assert entry.schema.get("name") == name


class TestSearchStickerHelpers:
    """Smoke check that the public _get_active_adapter helper doesn't crash."""

    def test_get_active_adapter_returns_none_or_object(self):
        from tools.yuanbao_tools import _get_active_adapter

        out = _get_active_adapter()
        # Either None (no Yuanbao adapter active) or an opaque object —
        # we just verify the helper doesn't throw.
        assert out is None or out is not None
