"""Coverage for ``agent.skill_preprocessing`` — the SKILL.md template
variable + inline-shell substitution helpers.  No existing direct tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from agent.skill_preprocessing import (
    expand_inline_shell,
    preprocess_skill_content,
    run_inline_shell,
    substitute_template_vars,
)


class TestSubstituteTemplateVars:
    def test_empty_content_unchanged(self):
        assert substitute_template_vars("", Path("/x"), "sid") == ""

    def test_substitutes_skill_dir(self):
        out = substitute_template_vars(
            "Path is ${HERMES_SKILL_DIR}/foo",
            Path("/my/skill"),
            None,
        )
        assert out == "Path is /my/skill/foo"

    def test_substitutes_session_id(self):
        out = substitute_template_vars(
            "Session: ${HERMES_SESSION_ID}",
            None,
            "abc-123",
        )
        assert out == "Session: abc-123"

    def test_leaves_unresolved_tokens_in_place(self):
        out = substitute_template_vars(
            "dir=${HERMES_SKILL_DIR} session=${HERMES_SESSION_ID}",
            None,
            None,
        )
        # Both tokens are unresolved so the literal text survives.
        assert out == "dir=${HERMES_SKILL_DIR} session=${HERMES_SESSION_ID}"

    def test_partial_resolution_leaves_other_token(self):
        out = substitute_template_vars(
            "dir=${HERMES_SKILL_DIR} session=${HERMES_SESSION_ID}",
            Path("/s"),
            None,
        )
        assert "dir=/s" in out
        assert "${HERMES_SESSION_ID}" in out

    def test_unknown_token_is_not_matched(self):
        # The regex is a fixed alternation — unknown tokens pass through.
        out = substitute_template_vars(
            "${HERMES_OTHER}", Path("/x"), "sid"
        )
        assert out == "${HERMES_OTHER}"


class TestRunInlineShell:
    def test_simple_echo(self, tmp_path):
        assert run_inline_shell("echo hello", tmp_path, timeout=5) == "hello"

    def test_uses_cwd_argument(self, tmp_path):
        (tmp_path / "marker.txt").write_text("inside")
        out = run_inline_shell("cat marker.txt", tmp_path, timeout=5)
        assert out == "inside"

    def test_stdout_trim_strips_trailing_newline(self, tmp_path):
        # echo emits a trailing \n which the helper rstrips.
        assert run_inline_shell("echo trim", tmp_path, timeout=5) == "trim"

    def test_falls_back_to_stderr_when_stdout_empty(self, tmp_path):
        out = run_inline_shell("echo only-err >&2", tmp_path, timeout=5)
        assert out == "only-err"

    def test_truncation_for_oversized_output(self, tmp_path):
        # head -c 5000 emits 5000 chars; helper caps at 4000.
        out = run_inline_shell(
            "head -c 5000 /dev/zero | tr '\\0' 'a'", tmp_path, timeout=5,
        )
        assert out.endswith("...[truncated]")
        # Cap is 4000 chars + "...[truncated]" suffix.
        assert len(out) <= 4000 + len("...[truncated]")

    def test_timeout_returns_marker(self, tmp_path):
        out = run_inline_shell("sleep 5", tmp_path, timeout=1)
        assert "timeout" in out

    def test_nonzero_exit_is_not_fatal(self, tmp_path):
        # A failing command still returns its output (no exception).
        out = run_inline_shell("false; echo done", tmp_path, timeout=5)
        assert out == "done"


class TestExpandInlineShell:
    def test_no_snippets_passes_through(self, tmp_path):
        text = "no shell here"
        assert expand_inline_shell(text, tmp_path, timeout=5) == text

    def test_single_snippet_substituted(self, tmp_path):
        out = expand_inline_shell("date: !`echo today`", tmp_path, timeout=5)
        assert out == "date: today"

    def test_multiple_snippets_all_substituted(self, tmp_path):
        out = expand_inline_shell(
            "a=!`echo one` b=!`echo two`", tmp_path, timeout=5,
        )
        assert out == "a=one b=two"

    def test_empty_backticks_do_not_match_regex(self, tmp_path):
        # The inline-shell pattern requires at least one char between
        # backticks, so an empty form `!\`\`` passes through unchanged.
        text = "foo!``bar"
        assert expand_inline_shell(text, tmp_path, timeout=5) == text


class TestPreprocessSkillContent:
    def test_empty_content_unchanged(self, tmp_path):
        assert (
            preprocess_skill_content("", tmp_path, "sid", skills_cfg={}) == ""
        )

    def test_template_vars_only_by_default(self, tmp_path):
        # Default skills_cfg={template_vars: True} but inline_shell off.
        out = preprocess_skill_content(
            "dir=${HERMES_SKILL_DIR} run=!`echo x`",
            tmp_path,
            None,
            skills_cfg={"template_vars": True, "inline_shell": False},
        )
        assert "dir=" + str(tmp_path) in out
        # The inline shell snippet survives untouched.
        assert "!`echo x`" in out

    def test_template_vars_off_leaves_tokens(self, tmp_path):
        out = preprocess_skill_content(
            "dir=${HERMES_SKILL_DIR}",
            tmp_path,
            None,
            skills_cfg={"template_vars": False},
        )
        assert out == "dir=${HERMES_SKILL_DIR}"

    def test_inline_shell_enabled_runs_snippet(self, tmp_path):
        out = preprocess_skill_content(
            "out: !`echo five`",
            tmp_path,
            None,
            skills_cfg={"inline_shell": True, "template_vars": False},
        )
        assert out == "out: five"
