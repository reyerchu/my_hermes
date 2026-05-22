"""Coverage for command-template helpers in tools.tts_tool —
shell quoting context, placeholder quoting, template rendering."""
from __future__ import annotations

import os

import pytest

from tools.tts_tool import (
    _shell_quote_context,
    _quote_command_tts_placeholder,
    _render_command_tts_template,
)


class TestShellQuoteContext:
    def test_bare_context_returns_none(self):
        assert _shell_quote_context("echo {text}", 5) is None

    def test_inside_single_quotes(self):
        # 'hello {text}' — position inside single quotes.
        cmd = "echo 'hello {text}'"
        # Find position of '{' inside the single-quote region.
        pos = cmd.index("{text}")
        assert _shell_quote_context(cmd, pos) == "'"

    def test_inside_double_quotes(self):
        cmd = 'echo "hello {text}"'
        pos = cmd.index("{text}")
        assert _shell_quote_context(cmd, pos) == '"'

    def test_quote_closes(self):
        # After the closing quote, context is bare.
        cmd = "echo 'a' {text}"
        pos = cmd.index("{text}")
        assert _shell_quote_context(cmd, pos) is None

    def test_backslash_inside_double_quotes_skips_next(self):
        # \" inside double quotes shouldn't close it.
        cmd = 'echo "x\\"y {text}"'
        pos = cmd.index("{text}")
        assert _shell_quote_context(cmd, pos) == '"'

    def test_position_zero(self):
        # No prior characters → bare.
        assert _shell_quote_context("anything", 0) is None


class TestQuoteCommandTtsPlaceholder:
    def test_single_quote_context_escapes_quotes(self):
        out = _quote_command_tts_placeholder("it's me", quote_context="'")
        # Embedded ' is closed-then-reopened.
        assert out == "it'\\''s me"

    def test_double_quote_context_escapes_special(self):
        out = _quote_command_tts_placeholder('hello "$X"', quote_context='"')
        # $ and " escaped.
        assert "\\$" in out
        assert '\\"' in out

    def test_bare_context_uses_shlex(self):
        out = _quote_command_tts_placeholder("hello world", quote_context=None)
        # Whitespace forces shlex.quote to wrap in single quotes (POSIX).
        if os.name != "nt":
            assert out == "'hello world'"

    def test_backslash_double_quoted(self):
        out = _quote_command_tts_placeholder("a\\b", quote_context='"')
        assert "\\\\" in out


class TestRenderCommandTtsTemplate:
    def test_single_brace_placeholder(self):
        out = _render_command_tts_template(
            "say {text}", {"text": "hi"},
        )
        # On POSIX shlex wraps in single quotes for safety.
        assert "say " in out
        assert "hi" in out

    def test_double_brace_kept_as_literal_brace(self):
        out = _render_command_tts_template(
            "say {{literal}} {text}", {"text": "hi"},
        )
        # {{literal}} should render to {literal} — not be substituted.
        assert "{literal}" in out

    def test_dollar_brace_not_substituted(self):
        # ${text} (bash variable syntax) is preserved.
        out = _render_command_tts_template(
            "say ${text} {text}", {"text": "VAL"},
        )
        # The bash-style ${text} should NOT be replaced.
        assert "${text}" in out
        # But the bare {text} should be.
        assert "VAL" in out

    def test_quote_context_picked_up(self):
        # Inside single quotes, the placeholder should be escaped using
        # the closed-then-reopened pattern.
        out = _render_command_tts_template(
            "echo 'it {text}'", {"text": "is's"},
        )
        # Look for the escape sequence.
        assert "'\\''" in out

    def test_no_placeholders_kept_as_is(self):
        out = _render_command_tts_template(
            "say hello", {"text": "ignored"},
        )
        assert out == "say hello"

    def test_multiple_placeholders(self):
        out = _render_command_tts_template(
            "tool {text} {voice}", {"text": "hi", "voice": "alice"},
        )
        assert "hi" in out
        assert "alice" in out
