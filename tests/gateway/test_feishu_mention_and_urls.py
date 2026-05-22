"""Coverage for mention-hint, self-mention stripping, onboard URLs,
and bot-response parsing in gateway.platforms.feishu."""
from __future__ import annotations

import pytest

from gateway.platforms.feishu import (
    _build_mention_hint,
    _strip_edge_self_mentions,
    _accounts_base_url,
    _onboard_open_base_url,
    _parse_bot_response,
    FeishuMentionRef,
)


class TestBuildMentionHint:
    def test_empty(self):
        assert _build_mention_hint([]) == ""

    def test_skips_self_mentions(self):
        m = [FeishuMentionRef(name="Bot", is_self=True)]
        assert _build_mention_hint(m) == ""

    def test_at_all(self):
        m = [FeishuMentionRef(is_all=True)]
        out = _build_mention_hint(m)
        assert out == "[Mentioned: @all]"

    def test_named_with_open_id(self):
        m = [FeishuMentionRef(name="Alice", open_id="o1")]
        out = _build_mention_hint(m)
        assert "Alice" in out
        assert "open_id=o1" in out

    def test_named_without_open_id(self):
        m = [FeishuMentionRef(name="Bob")]
        out = _build_mention_hint(m)
        assert out == "[Mentioned: Bob]"

    def test_dedup_by_signature(self):
        # Two identical entries collapse to one.
        m = [
            FeishuMentionRef(name="A", open_id="o1"),
            FeishuMentionRef(name="A", open_id="o1"),
        ]
        out = _build_mention_hint(m)
        assert out.count("A (open_id=o1)") == 1

    def test_unknown_fallback(self):
        # No name + no open_id (and not @all) → "unknown".
        m = [FeishuMentionRef(open_id="")]
        out = _build_mention_hint(m)
        # open_id is "" so falls through to else branch → name or 'unknown'
        assert "unknown" in out

    def test_mix_self_and_other(self):
        m = [
            FeishuMentionRef(name="Bot", is_self=True),
            FeishuMentionRef(name="Alice"),
        ]
        out = _build_mention_hint(m)
        assert "Alice" in out
        assert "Bot" not in out


class TestStripEdgeSelfMentions:
    def test_empty_text(self):
        assert _strip_edge_self_mentions("", []) == ""

    def test_no_self_mentions(self):
        m = [FeishuMentionRef(name="Alice")]  # not self
        out = _strip_edge_self_mentions("@Alice hi", m)
        # Without self mentions, function returns unchanged.
        assert "@Alice" in out

    def test_leading_self_mention_stripped(self):
        m = [FeishuMentionRef(name="Bot", is_self=True)]
        out = _strip_edge_self_mentions("@Bot hello", m)
        assert out == "hello"

    def test_consecutive_leading(self):
        m = [FeishuMentionRef(name="Bot", is_self=True)]
        out = _strip_edge_self_mentions("@Bot @Bot do work", m)
        assert out == "do work"

    def test_trailing_self_mention_with_punct(self):
        m = [FeishuMentionRef(name="Bot", is_self=True)]
        out = _strip_edge_self_mentions("do work @Bot.", m)
        # Trailing self-mention before punctuation is stripped.
        assert "@Bot" not in out

    def test_mid_sentence_self_mention_kept(self):
        m = [FeishuMentionRef(name="Bot", is_self=True)]
        out = _strip_edge_self_mentions("don't @Bot again", m)
        # Mid-sentence stays put.
        assert "@Bot" in out

    def test_word_boundary_preserved(self):
        # @Al shouldn't eat @Alice.
        m = [FeishuMentionRef(name="Al", is_self=True)]
        out = _strip_edge_self_mentions("@Alice hi", m)
        # @Alice is not the self mention (Al ≠ Alice) — word boundary blocks.
        assert "@Alice" in out


class TestAccountsBaseUrl:
    def test_feishu(self):
        assert _accounts_base_url("feishu") == "https://accounts.feishu.cn"

    def test_lark(self):
        assert _accounts_base_url("lark") == "https://accounts.larksuite.com"

    def test_unknown_falls_back_to_feishu(self):
        assert _accounts_base_url("unknown") == "https://accounts.feishu.cn"


class TestOnboardOpenBaseUrl:
    def test_feishu(self):
        assert _onboard_open_base_url("feishu") == "https://open.feishu.cn"

    def test_lark(self):
        assert _onboard_open_base_url("lark") == "https://open.larksuite.com"

    def test_unknown_falls_back_to_feishu(self):
        assert _onboard_open_base_url("unknown") == "https://open.feishu.cn"


class TestParseBotResponse:
    def test_non_zero_code(self):
        assert _parse_bot_response({"code": 1}) is None

    def test_with_app_name(self):
        out = _parse_bot_response({"code": 0, "bot": {"app_name": "Alpha", "open_id": "o1"}})
        assert out == {"bot_name": "Alpha", "bot_open_id": "o1"}

    def test_legacy_bot_name(self):
        # Older API uses "bot_name" instead of "app_name".
        out = _parse_bot_response({"code": 0, "bot": {"bot_name": "Legacy", "open_id": "o2"}})
        assert out["bot_name"] == "Legacy"

    def test_nested_data_bot(self):
        out = _parse_bot_response(
            {"code": 0, "data": {"bot": {"app_name": "Nested", "open_id": "o3"}}}
        )
        assert out["bot_name"] == "Nested"
        assert out["bot_open_id"] == "o3"

    def test_missing_bot_returns_dict_with_nones(self):
        out = _parse_bot_response({"code": 0})
        assert out == {"bot_name": None, "bot_open_id": None}
