"""Coverage for _clean_discord_id in gateway.platforms.discord."""
from __future__ import annotations

import pytest

from gateway.platforms.discord import _clean_discord_id


class TestCleanDiscordId:
    def test_bare_id_unchanged(self):
        assert _clean_discord_id("123456789012345678") == "123456789012345678"

    def test_strips_mention_syntax(self):
        assert _clean_discord_id("<@123>") == "123"

    def test_strips_nickname_mention(self):
        # <@!123> for nickname mentions
        assert _clean_discord_id("<@!456>") == "456"

    def test_strips_user_prefix(self):
        assert _clean_discord_id("user:alice") == "alice"

    def test_user_prefix_case_insensitive(self):
        assert _clean_discord_id("USER:bob") == "bob"

    def test_outer_whitespace_stripped(self):
        assert _clean_discord_id("  123  ") == "123"

    def test_whitespace_after_strip(self):
        # After removing 'user:' the remaining whitespace is trimmed.
        assert _clean_discord_id("user:  bob  ") == "bob"

    def test_combo_mention_and_whitespace(self):
        assert _clean_discord_id("  <@!789>  ") == "789"

    def test_just_brackets_no_id(self):
        # "<@>" with empty id — lstrip+rstrip leaves "".
        assert _clean_discord_id("<@>") == ""

    def test_plain_username(self):
        assert _clean_discord_id("alice#1234") == "alice#1234"
