"""Edge-case coverage for DeliveryTarget.parse / to_string.

Complements the happy-path coverage in test_delivery.py with:
  * round-trip stability (parse → to_string → parse)
  * boundary inputs (whitespace, case, unicode, missing parts)
  * origin fallback semantics
"""
from gateway.config import Platform
from gateway.delivery import DeliveryTarget
from gateway.session import SessionSource


class TestParseEdgeCases:
    def test_leading_and_trailing_whitespace_is_stripped(self):
        t = DeliveryTarget.parse("   telegram:42   ")
        assert t.platform == Platform.TELEGRAM
        assert t.chat_id == "42"
        assert t.is_explicit is True

    def test_platform_name_is_case_insensitive(self):
        for value in ("Telegram", "TELEGRAM", "tELEgrAm"):
            t = DeliveryTarget.parse(value)
            assert t.platform == Platform.TELEGRAM
            assert t.is_explicit is False

    def test_explicit_chat_id_preserves_case(self):
        # Slack channel IDs are case-sensitive — parser must not lowercase them.
        t = DeliveryTarget.parse("slack:C012ABcDEF")
        assert t.chat_id == "C012ABcDEF"

    def test_origin_keyword_is_case_insensitive(self):
        origin = SessionSource(platform=Platform.DISCORD, chat_id="d1", thread_id=None)
        t = DeliveryTarget.parse("ORIGIN", origin=origin)
        assert t.is_origin is True
        assert t.platform == Platform.DISCORD

    def test_origin_keyword_without_source_falls_back_to_local(self):
        t = DeliveryTarget.parse("origin")
        assert t.platform == Platform.LOCAL
        assert t.is_origin is True
        assert t.chat_id is None

    def test_unknown_platform_falls_back_to_local(self):
        t = DeliveryTarget.parse("unknownplatform:123")
        assert t.platform == Platform.LOCAL
        assert t.is_explicit is False  # the local fallback is not "explicit"

    def test_unknown_bare_platform_also_falls_back_to_local(self):
        t = DeliveryTarget.parse("nope")
        assert t.platform == Platform.LOCAL

    def test_unicode_chat_id_is_preserved(self):
        t = DeliveryTarget.parse("telegram:聊天室42")
        assert t.chat_id == "聊天室42"

    def test_three_part_target_parses_thread_id(self):
        t = DeliveryTarget.parse("telegram:42:101")
        assert t.platform == Platform.TELEGRAM
        assert t.chat_id == "42"
        assert t.thread_id == "101"
        assert t.is_explicit is True

    def test_chat_id_can_contain_extra_colon_via_split_limit(self):
        # split(":", 2) caps at 3 parts → trailing colons belong to thread_id.
        t = DeliveryTarget.parse("telegram:room:abc:xyz")
        assert t.chat_id == "room"
        assert t.thread_id == "abc:xyz"

    def test_explicit_origin_target_is_marked(self):
        origin = SessionSource(platform=Platform.TELEGRAM, chat_id="777", thread_id=None)
        t = DeliveryTarget.parse("origin", origin=origin)
        assert t.is_origin is True
        # origin is NOT the same as "explicit chat_id specified by the user"
        assert t.is_explicit is False


class TestToStringRoundTrip:
    def test_local(self):
        t = DeliveryTarget(platform=Platform.LOCAL)
        assert t.to_string() == "local"

    def test_platform_only(self):
        t = DeliveryTarget(platform=Platform.SLACK)
        assert t.to_string() == "slack"

    def test_platform_with_chat_id(self):
        t = DeliveryTarget(platform=Platform.TELEGRAM, chat_id="42")
        assert t.to_string() == "telegram:42"

    def test_platform_with_chat_and_thread(self):
        t = DeliveryTarget(
            platform=Platform.TELEGRAM, chat_id="42", thread_id="7"
        )
        assert t.to_string() == "telegram:42:7"

    def test_origin_wins_over_chat_id_in_serialisation(self):
        # The to_string short-circuit returns "origin" even when chat_id is set.
        t = DeliveryTarget(
            platform=Platform.TELEGRAM, chat_id="42", is_origin=True
        )
        assert t.to_string() == "origin"

    def test_round_trip_for_three_part(self):
        round_trip = DeliveryTarget.parse(
            DeliveryTarget(
                platform=Platform.SLACK, chat_id="C1", thread_id="T2"
            ).to_string()
        )
        assert round_trip.platform == Platform.SLACK
        assert round_trip.chat_id == "C1"
        assert round_trip.thread_id == "T2"
