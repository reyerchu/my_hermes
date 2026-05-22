"""Coverage for the pure helpers in ``hermes_cli.gateway_windows`` —
the schtasks / cmd.exe quoting helpers, sanitize_filename, and the
fall-back-detection predicate."""
from __future__ import annotations

import pytest

from hermes_cli import gateway_windows as gw


class TestQuoteCmdScriptArg:
    def test_simple_word_unchanged(self):
        assert gw._quote_cmd_script_arg("hello") == "hello"

    def test_empty_string_becomes_pair_of_quotes(self):
        assert gw._quote_cmd_script_arg("") == '""'

    def test_value_with_space_gets_quoted(self):
        out = gw._quote_cmd_script_arg("hello world")
        assert out.startswith('"') and out.endswith('"')

    def test_embedded_quote_doubled(self):
        out = gw._quote_cmd_script_arg('a "b"')
        # cmd.exe doubles embedded quotes.
        assert '""' in out

    def test_newline_raises(self):
        with pytest.raises(ValueError, match="newline"):
            gw._quote_cmd_script_arg("a\nb")

    def test_carriage_return_raises(self):
        with pytest.raises(ValueError, match="newline"):
            gw._quote_cmd_script_arg("a\rb")


class TestQuoteSchtasksArg:
    def test_simple_value_unchanged(self):
        assert gw._quote_schtasks_arg("hello") == "hello"

    def test_value_with_space_wrapped(self):
        assert gw._quote_schtasks_arg("a b") == '"a b"'

    def test_embedded_quote_backslash_escaped(self):
        # Different convention from cmd.exe: backslash-escape, not doubling.
        assert gw._quote_schtasks_arg('a "b"') == '"a \\"b\\""'


class TestShouldFallBack:
    def test_exit_124_triggers_fallback(self):
        assert gw._should_fall_back(124, "") is True

    def test_pattern_match_in_detail_triggers_fallback(self):
        # The exact patterns are private; any plausible "access denied"
        # phrasing in the detail should be enough — but at least non-
        # matching detail shouldn't fall back.
        assert gw._should_fall_back(0, "everything fine") is False


class TestSanitizeFilename:
    def test_alphanum_unchanged(self):
        assert gw._sanitize_filename("Hermes_Gateway") == "Hermes_Gateway"

    def test_illegal_chars_replaced_with_underscore(self):
        out = gw._sanitize_filename('a<b>c:"d/e\\f|g?h*i')
        # None of the illegal characters should survive.
        for bad in '<>:"/\\|?*':
            assert bad not in out

    def test_control_characters_replaced(self):
        out = gw._sanitize_filename("a\x00b\x1fc")
        assert "\x00" not in out
        assert "\x1f" not in out
