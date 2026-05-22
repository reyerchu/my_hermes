"""Coverage for the pure helpers in ``gateway.platforms.helpers``.

``MessageDeduplicator`` is covered by test_message_deduplicator.py; this
file pins ``strip_markdown`` and ``redact_phone`` (both used by every
plain-text adapter for outbound formatting + log safety)."""
from __future__ import annotations

import pytest

from gateway.platforms.helpers import redact_phone, strip_markdown


class TestStripMarkdown:
    def test_plain_text_passes_through(self):
        assert strip_markdown("hello world") == "hello world"

    def test_strips_bold_asterisks(self):
        assert "important" in strip_markdown("this is **important**")
        assert "**" not in strip_markdown("this is **important**")

    def test_strips_italic_asterisks(self):
        assert "emph" in strip_markdown("an *emph* word")

    def test_strips_inline_code(self):
        out = strip_markdown("use `foo()` here")
        assert "foo()" in out
        assert "`" not in out

    def test_strips_fenced_code_blocks(self):
        out = strip_markdown("before\n```python\ncode here\n```\nafter")
        # The block + fences are removed entirely.
        assert "```" not in out

    def test_strips_atx_headings(self):
        out = strip_markdown("# Title\nbody")
        assert "Title" not in out or "#" not in out

    def test_strips_bold_underscores(self):
        assert "**" not in strip_markdown("__bold__")
        assert "__" not in strip_markdown("__bold__")


class TestRedactPhone:
    def test_none_or_empty_returns_placeholder(self):
        assert redact_phone("") == "<none>"
        assert redact_phone(None) == "<none>"  # type: ignore[arg-type]

    def test_short_phone_fully_masked(self):
        assert redact_phone("1234") == "****"

    def test_short_phone_keeps_two_at_each_end(self):
        # 5-8 char phones keep 2 chars on each side.
        assert redact_phone("12345") == "12****45"
        assert redact_phone("12345678") == "12****78"

    def test_longer_phone_keeps_four_each_side(self):
        assert redact_phone("12345678901") == "1234****8901"
        assert redact_phone("12345678") == "12****78"

    def test_e164_format_first_four_and_last_four_preserved(self):
        # The redactor preserves the first 4 chars (which include the leading
        # "+" and the country-code digits) and the last 4 — not the country
        # code as a separate group.
        assert redact_phone("+12025550123") == "+120****0123"
