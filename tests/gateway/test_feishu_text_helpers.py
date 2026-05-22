"""Coverage for text-rendering pure helpers in gateway.platforms.feishu."""
from __future__ import annotations

import pytest

from gateway.platforms.feishu import (
    _escape_markdown_text,
    _to_boolean,
    _is_style_enabled,
    _wrap_inline_code,
    _sanitize_fence_language,
    _render_text_element,
    _render_code_block_element,
    _strip_markdown_to_plain_text,
    _coerce_int,
    _coerce_required_int,
)


class TestEscapeMarkdownText:
    def test_no_specials(self):
        assert _escape_markdown_text("hello") == "hello"

    def test_escapes_asterisk(self):
        assert "\\*" in _escape_markdown_text("a*b")

    def test_escapes_underscore(self):
        assert "\\_" in _escape_markdown_text("a_b")


class TestToBoolean:
    @pytest.mark.parametrize("value", [True, 1, "true"])
    def test_truthy(self, value):
        assert _to_boolean(value) is True

    @pytest.mark.parametrize("value", [False, 0, "false", "1", None, "yes"])
    def test_strict_only_three(self, value):
        # Implementation accepts only True / 1 / "true" — everything else False.
        assert _to_boolean(value) is False


class TestIsStyleEnabled:
    def test_none(self):
        assert _is_style_enabled(None, "bold") is False

    def test_empty(self):
        assert _is_style_enabled({}, "bold") is False

    def test_true_value(self):
        assert _is_style_enabled({"bold": True}, "bold") is True

    def test_string_true(self):
        assert _is_style_enabled({"bold": "true"}, "bold") is True


class TestWrapInlineCode:
    def test_no_backticks(self):
        assert _wrap_inline_code("hello") == "`hello`"

    def test_one_backtick_in_text(self):
        # Single backtick → fence uses 2 backticks
        out = _wrap_inline_code("a`b")
        assert out.startswith("``")
        assert "a`b" in out

    def test_padding_when_starts_with_backtick(self):
        # Body padded with leading/trailing space to avoid fence collision.
        out = _wrap_inline_code("`code")
        assert " `code " in out


class TestSanitizeFenceLanguage:
    def test_strip_whitespace(self):
        assert _sanitize_fence_language("  python  ") == "python"

    def test_newlines_replaced(self):
        assert _sanitize_fence_language("python\nfoo") == "python foo"

    def test_cr_replaced(self):
        assert _sanitize_fence_language("python\rbar") == "python bar"


class TestRenderTextElement:
    def test_plain_text(self):
        assert _render_text_element({"text": "hi"}) == "hi"

    def test_bold(self):
        out = _render_text_element({"text": "hi", "style": {"bold": True}})
        assert out == "**hi**"

    def test_italic(self):
        out = _render_text_element({"text": "hi", "style": {"italic": True}})
        assert out == "*hi*"

    def test_strikethrough(self):
        out = _render_text_element({"text": "hi", "style": {"strikethrough": True}})
        assert out == "~~hi~~"

    def test_underline_uses_u_tag(self):
        out = _render_text_element({"text": "hi", "style": {"underline": True}})
        assert out == "<u>hi</u>"

    def test_code_overrides_other_styles(self):
        out = _render_text_element({"text": "x", "style": {"code": True, "bold": True}})
        # Code wraps without bold markers.
        assert "`x`" in out
        assert "**" not in out

    def test_empty_text(self):
        assert _render_text_element({"text": ""}) == ""

    def test_combined_styles(self):
        out = _render_text_element({"text": "x", "style": {"bold": True, "italic": True}})
        # Both wrappers applied (in order: bold then italic).
        assert "**" in out
        assert "*x*" in out or "*x*" in out.replace("**", "")


class TestRenderCodeBlockElement:
    def test_basic_with_language(self):
        out = _render_code_block_element({"text": "print()", "language": "python"})
        assert out.startswith("```python\n")
        assert out.endswith("\n```")

    def test_no_language(self):
        out = _render_code_block_element({"text": "x", "language": ""})
        assert out.startswith("```\n")

    def test_crlf_normalised(self):
        out = _render_code_block_element({"text": "line1\r\nline2"})
        assert "\r\n" not in out
        assert "line1\nline2" in out

    def test_trailing_newline_preserved(self):
        out = _render_code_block_element({"text": "a\n", "language": "x"})
        # Should not double up the newline.
        assert "\n\n```" not in out

    def test_lang_alias(self):
        # "lang" is the fallback for "language"
        out = _render_code_block_element({"text": "x", "lang": "rust"})
        assert out.startswith("```rust\n")


class TestStripMarkdownToPlainText:
    def test_link_kept_with_url(self):
        out = _strip_markdown_to_plain_text("[click](http://x)")
        assert "click" in out

    def test_blockquote_stripped(self):
        out = _strip_markdown_to_plain_text("> quote line")
        assert out.startswith("quote")

    def test_horizontal_rule_normalised(self):
        out = _strip_markdown_to_plain_text("  ---  ")
        assert out == "---"

    def test_strikethrough_stripped(self):
        out = _strip_markdown_to_plain_text("~~gone~~")
        assert "~~" not in out

    def test_u_tag_stripped(self):
        out = _strip_markdown_to_plain_text("<u>under</u>")
        assert "<u>" not in out
        assert "under" in out

    def test_crlf_normalised(self):
        out = _strip_markdown_to_plain_text("a\r\nb")
        assert "\r" not in out


class TestCoerceInt:
    def test_int_passthrough(self):
        assert _coerce_int(7) == 7

    def test_numeric_string(self):
        assert _coerce_int("42") == 42

    def test_none(self):
        assert _coerce_int(None) is None
        assert _coerce_int(None, default=5) == 5

    def test_below_min_value(self):
        assert _coerce_int(-1, default=0, min_value=0) == 0

    def test_garbage(self):
        assert _coerce_int("bad", default=3) == 3


class TestCoerceRequiredInt:
    def test_int(self):
        assert _coerce_required_int(7, default=0) == 7

    def test_none_returns_default(self):
        assert _coerce_required_int(None, default=99) == 99

    def test_garbage_returns_default(self):
        assert _coerce_required_int("x", default=5) == 5
