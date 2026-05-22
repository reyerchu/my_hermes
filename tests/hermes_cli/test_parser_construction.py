"""Coverage for ``hermes_cli._parser.build_top_level_parser`` and the
``PRE_ARGPARSE_INHERITED_FLAGS`` table that the relauncher consults."""
from __future__ import annotations

import argparse

import pytest

from hermes_cli._parser import (
    PRE_ARGPARSE_INHERITED_FLAGS,
    build_top_level_parser,
)


class TestPreArgparseInheritedFlags:
    def test_table_is_a_non_empty_list(self):
        assert isinstance(PRE_ARGPARSE_INHERITED_FLAGS, list)
        assert PRE_ARGPARSE_INHERITED_FLAGS

    def test_each_entry_is_name_takes_value_pair(self):
        for entry in PRE_ARGPARSE_INHERITED_FLAGS:
            assert isinstance(entry, tuple) and len(entry) == 2
            name, takes_value = entry
            assert isinstance(name, str) and name.startswith("-")
            assert isinstance(takes_value, bool)

    def test_profile_is_in_the_table(self):
        # Documented invariant — --profile / -p strip themselves before
        # argparse, so they must be in the table for the relauncher.
        names = [name for name, _ in PRE_ARGPARSE_INHERITED_FLAGS]
        assert "--profile" in names
        assert "-p" in names


class TestBuildTopLevelParser:
    def test_returns_a_triple(self):
        parser, subparsers, chat_parser = build_top_level_parser()
        assert isinstance(parser, argparse.ArgumentParser)
        # subparsers action quacks like an Action.
        assert hasattr(subparsers, "add_parser")
        assert isinstance(chat_parser, argparse.ArgumentParser)

    def test_chat_parser_accepts_no_arguments(self):
        _, _, chat_parser = build_top_level_parser()
        # Parsing an empty argv via the chat subparser should not raise.
        args = chat_parser.parse_args([])
        assert isinstance(args, argparse.Namespace)

    def test_top_level_parser_has_help(self):
        parser, _, _ = build_top_level_parser()
        # -h / --help is registered by default; verify it doesn't get
        # silently removed.
        help_actions = [
            a for a in parser._actions if "-h" in a.option_strings
        ]
        assert help_actions
