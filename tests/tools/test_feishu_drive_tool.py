"""Coverage for the schemas + thread-local client store in
``tools.feishu_drive_tool``."""
from __future__ import annotations

import threading

import pytest

from tools.feishu_drive_tool import (
    FEISHU_DRIVE_ADD_COMMENT_SCHEMA,
    FEISHU_DRIVE_LIST_COMMENTS_SCHEMA,
    FEISHU_DRIVE_LIST_REPLIES_SCHEMA,
    FEISHU_DRIVE_REPLY_SCHEMA,
    get_client,
    set_client,
)


_SCHEMAS = [
    FEISHU_DRIVE_LIST_COMMENTS_SCHEMA,
    FEISHU_DRIVE_LIST_REPLIES_SCHEMA,
    FEISHU_DRIVE_REPLY_SCHEMA,
    FEISHU_DRIVE_ADD_COMMENT_SCHEMA,
]


class TestSchemas:
    def test_every_schema_has_name_and_description(self):
        for schema in _SCHEMAS:
            assert isinstance(schema["name"], str) and schema["name"]
            assert isinstance(schema["description"], str)
            assert schema["description"].strip()

    def test_every_schema_has_object_parameters(self):
        for schema in _SCHEMAS:
            params = schema["parameters"]
            assert params["type"] == "object"
            assert "properties" in params

    def test_list_comments_requires_file_token(self):
        params = FEISHU_DRIVE_LIST_COMMENTS_SCHEMA["parameters"]
        assert "file_token" in params["required"]

    def test_reply_requires_comment_and_content(self):
        params = FEISHU_DRIVE_REPLY_SCHEMA["parameters"]
        for field in ("file_token", "comment_id", "content"):
            assert field in params["required"]

    def test_add_comment_requires_file_and_content(self):
        params = FEISHU_DRIVE_ADD_COMMENT_SCHEMA["parameters"]
        for field in ("file_token", "content"):
            assert field in params["required"]


class TestThreadLocalClient:
    def test_get_returns_none_when_unset(self):
        set_client(None)
        assert get_client() is None

    def test_set_then_get_round_trip(self):
        sentinel = object()
        set_client(sentinel)
        try:
            assert get_client() is sentinel
        finally:
            set_client(None)

    def test_storage_is_thread_local(self):
        set_client("main")
        seen: list = []

        def worker():
            seen.append(get_client())

        t = threading.Thread(target=worker)
        t.start()
        t.join()
        assert seen == [None]
        assert get_client() == "main"
        set_client(None)
