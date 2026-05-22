"""Coverage for ``hermes_cli.cli_output`` — the print/prompt helpers
shared by the setup wizard and every CLI subcommand."""
from __future__ import annotations

import io

import pytest

from hermes_cli import cli_output as out


@pytest.fixture(autouse=True)
def _disable_color(monkeypatch):
    # Force the colour gate to return plain text so assertions are stable
    # regardless of the test runner's stdout TTY state.
    monkeypatch.setenv("NO_COLOR", "1")


class TestPrintHelpers:
    def test_print_info_uses_two_space_prefix(self, capsys):
        out.print_info("hello")
        captured = capsys.readouterr().out
        assert captured == "  hello\n"

    def test_print_success_prefixes_with_check(self, capsys):
        out.print_success("done")
        assert capsys.readouterr().out == "✓ done\n"

    def test_print_warning_prefixes_with_warn_glyph(self, capsys):
        out.print_warning("careful")
        assert capsys.readouterr().out == "⚠ careful\n"

    def test_print_error_prefixes_with_cross(self, capsys):
        out.print_error("nope")
        assert capsys.readouterr().out == "✗ nope\n"

    def test_print_header_includes_a_leading_blank_line(self, capsys):
        out.print_header("Section")
        captured = capsys.readouterr().out
        # color is disabled so output is "\n  Section\n"
        assert captured == "\n  Section\n"


class TestPrompt:
    def test_returns_stripped_input(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _prompt: "  hi  ")
        assert out.prompt("name?") == "hi"

    def test_blank_answer_returns_default(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _prompt: "")
        assert out.prompt("name?", default="alice") == "alice"

    def test_blank_answer_and_no_default_returns_empty_string(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _prompt: "")
        assert out.prompt("name?") == ""

    def test_password_uses_getpass(self, monkeypatch):
        called = {"hit": False}

        def fake_getpass(prompt):
            called["hit"] = True
            return "secret"

        monkeypatch.setattr("getpass.getpass", fake_getpass)
        # Also stub input() so a stray call would be detected.
        monkeypatch.setattr("builtins.input", lambda _: "NOT-CALLED")
        assert out.prompt("pwd?", password=True) == "secret"
        assert called["hit"] is True

    def test_ctrl_c_returns_empty_string(self, monkeypatch, capsys):
        def raise_kbi(_):
            raise KeyboardInterrupt
        monkeypatch.setattr("builtins.input", raise_kbi)
        assert out.prompt("q?") == ""
        # The handler prints a newline so the next CLI prompt isn't glued.
        assert capsys.readouterr().out == "\n"

    def test_eof_returns_empty_string(self, monkeypatch):
        def raise_eof(_):
            raise EOFError
        monkeypatch.setattr("builtins.input", raise_eof)
        assert out.prompt("q?") == ""


class TestPromptYesNo:
    def test_default_yes_with_empty_answer(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert out.prompt_yes_no("ok?", default=True) is True

    def test_default_no_with_empty_answer(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert out.prompt_yes_no("ok?", default=False) is False

    @pytest.mark.parametrize("answer", ["y", "Y", "yes", "YES", "yeah"])
    def test_yes_answers(self, monkeypatch, answer):
        monkeypatch.setattr("builtins.input", lambda _: answer)
        assert out.prompt_yes_no("ok?") is True

    @pytest.mark.parametrize("answer", ["n", "N", "no", "NOPE"])
    def test_no_answers(self, monkeypatch, answer):
        monkeypatch.setattr("builtins.input", lambda _: answer)
        assert out.prompt_yes_no("ok?") is False
