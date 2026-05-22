"""Coverage for the schema + thread-local client store in
``tools.feishu_doc_tool``."""
from __future__ import annotations

import threading

import pytest

from tools.feishu_doc_tool import (
    FEISHU_DOC_READ_SCHEMA,
    get_client,
    set_client,
)


class TestSchema:
    def test_top_level_name(self):
        assert FEISHU_DOC_READ_SCHEMA["name"] == "feishu_doc_read"

    def test_description_is_a_non_empty_string(self):
        d = FEISHU_DOC_READ_SCHEMA["description"]
        assert isinstance(d, str) and d.strip()

    def test_parameters_object_type(self):
        params = FEISHU_DOC_READ_SCHEMA["parameters"]
        assert params["type"] == "object"

    def test_doc_token_required(self):
        params = FEISHU_DOC_READ_SCHEMA["parameters"]
        assert "doc_token" in params["required"]
        assert params["properties"]["doc_token"]["type"] == "string"


class TestClientStorage:
    def test_get_client_returns_none_when_unset(self):
        # Reset thread-local for this test.
        set_client(None)
        assert get_client() is None

    def test_set_then_get_returns_same_object(self):
        sentinel = object()
        set_client(sentinel)
        try:
            assert get_client() is sentinel
        finally:
            set_client(None)

    def test_storage_is_thread_local(self):
        # Set a client on the test thread.
        set_client("main-thread-client")
        seen: list = []

        def worker():
            # In a fresh thread the stored value should NOT be visible.
            seen.append(get_client())

        t = threading.Thread(target=worker)
        t.start()
        t.join()
        assert seen == [None]
        # Test-thread value still intact.
        assert get_client() == "main-thread-client"
        set_client(None)
