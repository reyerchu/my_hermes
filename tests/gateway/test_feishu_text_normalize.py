"""Coverage for text-normalisation helpers in gateway.platforms.feishu —
_normalize_feishu_text, _unique_lines, _walk_nodes, _find_header_title,
_find_first_text, _attachment_placeholder, _first_non_empty_text."""
from __future__ import annotations

import pytest

from gateway.platforms.feishu import (
    _normalize_feishu_text,
    _unique_lines,
    _walk_nodes,
    _find_header_title,
    _find_first_text,
    _attachment_placeholder,
    _first_non_empty_text,
    FALLBACK_ATTACHMENT_TEXT,
    FeishuMentionRef,
)


class TestNormalizeFeishuText:
    def test_collapses_whitespace(self):
        assert _normalize_feishu_text("hello    world") == "hello world"

    def test_crlf_normalised(self):
        assert _normalize_feishu_text("a\r\nb") == "a\nb"

    def test_blank_lines_stripped(self):
        assert _normalize_feishu_text("a\n\nb") == "a\nb"

    def test_at_underscore_all_to_at_all(self):
        assert _normalize_feishu_text("ping @_all") == "ping @all"

    def test_mention_placeholder_replaced(self):
        mentions = {
            "@_user_1": FeishuMentionRef(name="Alice", open_id="o1"),
        }
        out = _normalize_feishu_text("hi @_user_1 there", mentions_map=mentions)
        assert "@Alice" in out
        assert "@_user_1" not in out

    def test_unknown_mention_replaced_with_space(self):
        out = _normalize_feishu_text("hi @_user_99 there")
        # No mapping → replaced with single space (collapsed).
        assert "@_user_99" not in out
        assert "hi" in out
        assert "there" in out

    def test_empty(self):
        assert _normalize_feishu_text("") == ""


class TestUniqueLines:
    def test_dedup_preserves_order(self):
        out = _unique_lines(["a", "b", "a", "c", "b"])
        assert out == ["a", "b", "c"]

    def test_drops_empty(self):
        out = _unique_lines(["a", "", "b", ""])
        assert out == ["a", "b"]

    def test_empty_input(self):
        assert _unique_lines([]) == []


class TestWalkNodes:
    def test_dict(self):
        out = list(_walk_nodes({"a": 1, "b": {"c": 2}}))
        # Top-level dict yielded first, then nested dicts.
        assert {"a": 1, "b": {"c": 2}} in out
        assert {"c": 2} in out

    def test_list(self):
        out = list(_walk_nodes([{"a": 1}, {"b": 2}]))
        assert {"a": 1} in out and {"b": 2} in out

    def test_scalar(self):
        # Scalars yield nothing.
        assert list(_walk_nodes(42)) == []


class TestFindHeaderTitle:
    def test_string_title(self):
        out = _find_header_title({"header": {"title": "  My Title  "}})
        assert out == "My Title"

    def test_dict_title_with_content(self):
        out = _find_header_title({"header": {"title": {"content": "X"}}})
        assert out == "X"

    def test_no_header(self):
        assert _find_header_title({}) == ""

    def test_non_dict_payload(self):
        assert _find_header_title("oops") == ""

    def test_non_dict_header(self):
        assert _find_header_title({"header": "x"}) == ""


class TestFindFirstText:
    def test_finds_first_match(self):
        payload = {"a": {"text": "found"}, "b": "ignored"}
        assert _find_first_text(payload, keys=("text",)) == "found"

    def test_multiple_keys_tried(self):
        payload = {"a": {"content": "right"}}
        assert _find_first_text(payload, keys=("text", "content")) == "right"

    def test_returns_empty_when_missing(self):
        assert _find_first_text({"a": 1}, keys=("text",)) == ""


class TestAttachmentPlaceholder:
    def test_with_name(self):
        assert _attachment_placeholder("report.pdf") == "[Attachment: report.pdf]"

    def test_strips_filename_whitespace(self):
        assert _attachment_placeholder("  file.txt  ") == "[Attachment: file.txt]"

    def test_empty_uses_fallback(self):
        assert _attachment_placeholder("") == FALLBACK_ATTACHMENT_TEXT

    def test_whitespace_only_uses_fallback(self):
        assert _attachment_placeholder("   ") == FALLBACK_ATTACHMENT_TEXT


class TestFirstNonEmptyText:
    def test_first_string(self):
        assert _first_non_empty_text("first", "second") == "first"

    def test_skip_blank_strings(self):
        assert _first_non_empty_text("", "  ", "real") == "real"

    def test_coerce_non_str_non_dict(self):
        assert _first_non_empty_text(None, 42) == "42"

    def test_dict_and_list_skipped(self):
        # dicts and lists must not be considered.
        out = _first_non_empty_text({"x": 1}, [1, 2], "got it")
        assert out == "got it"

    def test_all_empty_returns_empty(self):
        assert _first_non_empty_text(None, "", "  ") == ""
