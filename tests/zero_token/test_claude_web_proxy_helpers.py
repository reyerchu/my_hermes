"""Coverage for the pure helpers inside ``zero-token/claude_web_proxy.py``.

The browser/SSE-driving code path needs a live CDP Chrome to test;
these helpers (``render_tool_block``, ``extract_text_and_tool_calls``,
``parse_sse``) are pure and worth pinning.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


_MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "zero-token"
    / "claude_web_proxy.py"
)


@pytest.fixture(scope="module")
def proxy():
    # The module imports playwright at the top level; stub it before
    # importing so the test environment doesn't need the heavy dep.
    if "playwright" not in sys.modules:
        playwright_stub = type(sys)("playwright")
        async_api_stub = type(sys)("playwright.async_api")
        async_api_stub.async_playwright = lambda: None
        async_api_stub.BrowserContext = object
        async_api_stub.Page = object
        async_api_stub.Playwright = object
        sys.modules["playwright"] = playwright_stub
        sys.modules["playwright.async_api"] = async_api_stub
    spec = importlib.util.spec_from_file_location(
        "claude_web_proxy_under_test", _MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


class TestRenderToolBlock:
    def test_empty_list_returns_empty_string(self, proxy):
        assert proxy.render_tool_block([]) == ""

    def test_includes_tool_name_and_description(self, proxy):
        out = proxy.render_tool_block([
            {"function": {
                "name": "read_file",
                "description": "Read a file from disk",
                "parameters": {"type": "object"},
            }},
        ])
        assert "read_file" in out
        assert "Read a file from disk" in out
        assert "Available Tools" in out

    def test_skips_entries_without_function_block(self, proxy):
        out = proxy.render_tool_block([
            {"function": {"name": "ok"}},
            {},
            {"not_function": True},
        ])
        assert "ok" in out
        assert "Available Tools" in out


class TestExtractTextAndToolCalls:
    def test_no_tool_blocks_returns_original_text(self, proxy):
        text, calls = proxy.extract_text_and_tool_calls("plain text")
        assert text == "plain text"
        assert calls == []

    def test_single_tool_call_extracted(self, proxy):
        raw = '<tool_call name="foo">{"x": 1}</tool_call>'
        text, calls = proxy.extract_text_and_tool_calls(raw)
        assert text == ""
        assert len(calls) == 1
        assert calls[0]["type"] == "function"
        assert calls[0]["function"]["name"] == "foo"
        assert json.loads(calls[0]["function"]["arguments"]) == {"x": 1}

    def test_invalid_json_body_wrapped_in_raw_envelope(self, proxy):
        raw = '<tool_call name="x">not json</tool_call>'
        _, calls = proxy.extract_text_and_tool_calls(raw)
        args = json.loads(calls[0]["function"]["arguments"])
        assert args == {"_raw": "not json"}

    def test_assigns_synthetic_id_when_missing(self, proxy):
        raw = '<tool_call name="x">{}</tool_call>'
        _, calls = proxy.extract_text_and_tool_calls(raw)
        assert calls[0]["id"].startswith("call_")

    def test_explicit_id_preserved(self, proxy):
        raw = '<tool_call id="my-id" name="x">{}</tool_call>'
        _, calls = proxy.extract_text_and_tool_calls(raw)
        assert calls[0]["id"] == "my-id"

    def test_surrounding_text_preserved_and_trimmed(self, proxy):
        raw = 'Let me search.\n<tool_call name="x">{}</tool_call>\n'
        text, _ = proxy.extract_text_and_tool_calls(raw)
        assert text == "Let me search."


class TestParseSse:
    def test_returns_empty_for_only_done_marker(self, proxy):
        # parse_sse returns the assembled text content from delta blocks.
        # A "[DONE]" alone produces nothing.
        out = proxy.parse_sse("data: [DONE]\n")
        assert out == ""

    def test_ignores_non_data_lines(self, proxy):
        # Comments, blank lines, retry directives all skipped.
        out = proxy.parse_sse(
            ":heartbeat\n\nevent: ping\n"
        )
        assert out == ""

    def test_swallows_invalid_json_payloads(self, proxy):
        # parse_sse silently drops lines whose payload doesn't decode.
        out = proxy.parse_sse("data: not json\ndata: also not\n")
        assert out == ""

    def test_normalises_crlf_line_endings(self, proxy):
        # \r\n line endings shouldn't trip parsing.
        out = proxy.parse_sse("data: [DONE]\r\n")
        assert out == ""
