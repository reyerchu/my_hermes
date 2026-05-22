"""Coverage for the registration shim in ``tools.feishu_doc_tool``."""
from __future__ import annotations

import pytest

# Import triggers tool registration.
import tools.feishu_doc_tool  # noqa: F401
from tools.registry import registry


class TestFeishuDocToolRegistration:
    def test_feishu_doc_read_is_registered(self):
        assert registry.get_entry("feishu_doc_read") is not None

    def test_registered_with_feishu_doc_toolset(self):
        entry = registry.get_entry("feishu_doc_read")
        assert entry.toolset == "feishu_doc"

    def test_handler_is_callable(self):
        entry = registry.get_entry("feishu_doc_read")
        assert callable(entry.handler)

    def test_description_mentions_feishu(self):
        entry = registry.get_entry("feishu_doc_read")
        desc = (entry.description or "").lower()
        assert "feishu" in desc

    def test_schema_name_matches_entry_name(self):
        entry = registry.get_entry("feishu_doc_read")
        assert entry.schema["name"] == "feishu_doc_read"
