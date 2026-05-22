"""Coverage for ``tools.computer_use.schema.COMPUTER_USE_SCHEMA``.

The schema is the OpenAI tool definition that gates every model's
computer-use call — a regression in shape silently downgrades reliability
across every vision-capable model that drives the tool."""
from __future__ import annotations

import pytest

from tools.computer_use.schema import COMPUTER_USE_SCHEMA


class TestSchemaShape:
    def test_top_level_name_and_description(self):
        assert COMPUTER_USE_SCHEMA["name"] == "computer_use"
        assert isinstance(COMPUTER_USE_SCHEMA["description"], str)
        assert COMPUTER_USE_SCHEMA["description"].strip()

    def test_parameters_object_type(self):
        params = COMPUTER_USE_SCHEMA["parameters"]
        assert params["type"] == "object"
        assert "properties" in params

    def test_action_discriminator_present(self):
        action = COMPUTER_USE_SCHEMA["parameters"]["properties"]["action"]
        assert action["type"] == "string"
        assert "enum" in action

    def test_action_enum_contains_capture_and_click(self):
        actions = COMPUTER_USE_SCHEMA["parameters"]["properties"]["action"]["enum"]
        for required in [
            "capture", "click", "double_click", "right_click",
            "middle_click", "drag", "scroll", "type", "key",
            "wait", "list_apps", "focus_app",
        ]:
            assert required in actions

    def test_action_enum_has_no_duplicates(self):
        actions = COMPUTER_USE_SCHEMA["parameters"]["properties"]["action"]["enum"]
        assert len(actions) == len(set(actions))

    def test_capture_mode_som_documented_in_description(self):
        # SOM (Set-Of-Marks) overlays are the recommended UX for vision
        # models — surface in the description so models discover the
        # workflow.
        assert "som" in COMPUTER_USE_SCHEMA["description"].lower()
