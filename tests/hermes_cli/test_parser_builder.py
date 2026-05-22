"""Coverage for hermes_cli._parser.build_top_level_parser — verifies
the top-level argparse surface stays stable and that
``inherit_on_relaunch`` is properly tagged on inherited flags."""
from __future__ import annotations

import argparse

import pytest

from hermes_cli import _parser as p


@pytest.fixture(scope="module")
def built():
    parser, subparsers, chat_parser = p.build_top_level_parser()
    return parser, subparsers, chat_parser


class TestBuildTopLevelParserShape:
    def test_returns_three_tuple(self, built):
        parser, subparsers, chat_parser = built
        assert isinstance(parser, argparse.ArgumentParser)
        # subparsers is the special action created by add_subparsers
        assert hasattr(subparsers, "add_parser")
        assert isinstance(chat_parser, argparse.ArgumentParser)

    def test_prog_is_hermes(self, built):
        parser, _, _ = built
        assert parser.prog == "hermes"

    def test_version_flag_present(self, built):
        parser, _, _ = built
        flags = {opt for action in parser._actions for opt in action.option_strings}
        assert "--version" in flags or "-V" in flags

    def test_oneshot_flag_present(self, built):
        parser, _, _ = built
        flags = {opt for action in parser._actions for opt in action.option_strings}
        assert "-z" in flags
        assert "--oneshot" in flags

    def test_model_provider_toolsets_present(self, built):
        parser, _, _ = built
        flags = {opt for action in parser._actions for opt in action.option_strings}
        assert "--model" in flags
        assert "--provider" in flags
        assert "--toolsets" in flags

    def test_resume_and_continue_flags(self, built):
        parser, _, _ = built
        flags = {opt for action in parser._actions for opt in action.option_strings}
        assert "--resume" in flags
        assert "--continue" in flags

    def test_chat_parser_is_subparser(self, built):
        # chat parser registered under subparsers
        _, _, chat_parser = built
        assert isinstance(chat_parser, argparse.ArgumentParser)


class TestInheritOnRelaunchMetadata:
    def test_model_action_marked_inherit(self, built):
        parser, _, _ = built
        action = next(
            a for a in parser._actions if "--model" in a.option_strings
        )
        assert getattr(action, "inherit_on_relaunch", False) is True

    def test_provider_action_marked_inherit(self, built):
        parser, _, _ = built
        action = next(
            a for a in parser._actions if "--provider" in a.option_strings
        )
        assert getattr(action, "inherit_on_relaunch", False) is True

    def test_skills_action_marked_inherit(self, built):
        parser, _, _ = built
        action = next(
            a for a in parser._actions if "--skills" in a.option_strings
        )
        assert getattr(action, "inherit_on_relaunch", False) is True

    def test_yolo_action_marked_inherit(self, built):
        parser, _, _ = built
        action = next(
            a for a in parser._actions if "--yolo" in a.option_strings
        )
        assert getattr(action, "inherit_on_relaunch", False) is True

    def test_accept_hooks_marked_inherit(self, built):
        parser, _, _ = built
        action = next(
            a for a in parser._actions if "--accept-hooks" in a.option_strings
        )
        assert getattr(action, "inherit_on_relaunch", False) is True

    def test_version_NOT_marked_inherit(self, built):
        parser, _, _ = built
        action = next(
            a for a in parser._actions if "--version" in a.option_strings
        )
        # --version is parser-builtin add_argument — should not be tagged.
        assert getattr(action, "inherit_on_relaunch", False) is False


class TestPreArgparseInheritedFlags:
    def test_profile_flag_listed(self):
        flags = {f for f, _ in p.PRE_ARGPARSE_INHERITED_FLAGS}
        assert "--profile" in flags
        assert "-p" in flags

    def test_profile_takes_value(self):
        # both entries should be "value-taking" (True)
        for flag, takes_value in p.PRE_ARGPARSE_INHERITED_FLAGS:
            if flag in {"--profile", "-p"}:
                assert takes_value is True


class TestParserParsesBasics:
    def test_parser_accepts_empty_argv(self, built):
        parser, _, _ = built
        # Top-level parser permits no subcommand (defaults to interactive chat).
        ns = parser.parse_args([])
        assert ns.oneshot is None

    def test_parser_accepts_oneshot(self, built):
        parser, _, _ = built
        ns = parser.parse_args(["-z", "hello"])
        assert ns.oneshot == "hello"

    def test_parser_accepts_model(self, built):
        parser, _, _ = built
        ns = parser.parse_args(["--model", "anthropic/claude-sonnet-4.6"])
        assert ns.model == "anthropic/claude-sonnet-4.6"

    def test_worktree_is_store_true(self, built):
        parser, _, _ = built
        ns = parser.parse_args(["-w"])
        assert ns.worktree is True

    def test_continue_no_arg(self, built):
        parser, _, _ = built
        ns = parser.parse_args(["-c"])
        # const=True when no value passed
        assert ns.continue_last is True

    def test_continue_with_arg(self, built):
        parser, _, _ = built
        ns = parser.parse_args(["-c", "my-project"])
        assert ns.continue_last == "my-project"
