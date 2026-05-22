"""Coverage for the registration shim ``tools.computer_use_tool``.

The module's whole purpose is to register ``computer_use`` with
tools.registry at import time."""
from __future__ import annotations

import pytest

# Importing the shim should be safe and idempotent.
import tools.computer_use_tool  # noqa: F401
from tools.registry import registry


class TestComputerUseToolShim:
    def test_registry_has_computer_use_entry(self):
        entry = registry.get_entry("computer_use")
        assert entry is not None

    def test_registered_schema_name_matches(self):
        entry = registry.get_entry("computer_use")
        # The registered schema is the one from tools.computer_use.schema.
        assert entry.schema["name"] == "computer_use"

    def test_registered_toolset_is_computer_use(self):
        entry = registry.get_entry("computer_use")
        assert entry.toolset == "computer_use"

    def test_description_mentions_macos(self):
        entry = registry.get_entry("computer_use")
        # The shim's description starts with "Universal macOS desktop control".
        desc = (entry.description or "").lower()
        assert "macos" in desc
