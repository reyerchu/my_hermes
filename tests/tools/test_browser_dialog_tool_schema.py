"""Coverage for the schema + check gate in ``tools.browser_dialog_tool``."""
from __future__ import annotations

import pytest

from tools.browser_dialog_tool import (
    BROWSER_DIALOG_SCHEMA,
    _browser_dialog_check,
)


class TestSchema:
    def test_top_level_name(self):
        assert BROWSER_DIALOG_SCHEMA["name"] == "browser_dialog"

    def test_description_non_empty(self):
        d = BROWSER_DIALOG_SCHEMA["description"]
        assert isinstance(d, str)
        assert d.strip()

    def test_parameters_object_type(self):
        params = BROWSER_DIALOG_SCHEMA["parameters"]
        assert params["type"] == "object"
        assert "properties" in params

    def test_action_property_present(self):
        params = BROWSER_DIALOG_SCHEMA["parameters"]
        assert "action" in params["properties"]

    def test_action_enum_includes_accept_and_dismiss(self):
        action = BROWSER_DIALOG_SCHEMA["parameters"]["properties"]["action"]
        enum = action.get("enum") or []
        assert "accept" in enum
        assert "dismiss" in enum


class TestBrowserDialogCheck:
    def test_returns_bool(self):
        out = _browser_dialog_check()
        assert isinstance(out, bool)
