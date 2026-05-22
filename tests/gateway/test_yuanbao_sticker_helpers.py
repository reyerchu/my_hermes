"""Coverage for pure scoring helpers in gateway.platforms.yuanbao_sticker."""
from __future__ import annotations

import pytest

from gateway.platforms.yuanbao_sticker import (
    _normalize_text,
    _compact_text,
    _multiset_char_hit_ratio,
    _bigram_jaccard,
    _longest_subsequence_ratio,
    _score_field,
)


class TestNormalizeText:
    def test_basic_lower(self):
        assert _normalize_text("HeLLo") == "hello"

    def test_strip_whitespace(self):
        assert _normalize_text("  hi  ") == "hi"

    def test_nfkc_normalize(self):
        # Full-width digit "１" normalises to ASCII "1".
        assert _normalize_text("１２") == "12"

    def test_none(self):
        assert _normalize_text(None) == ""

    def test_empty(self):
        assert _normalize_text("") == ""


class TestCompactText:
    def test_strips_punctuation(self):
        out = _compact_text("Hello, World!")
        # No spaces, commas, exclam marks.
        assert " " not in out
        assert "," not in out
        assert "!" not in out
        assert "helloworld" in out

    def test_chinese_punct(self):
        out = _compact_text("你好，世界。")
        assert "，" not in out
        assert "。" not in out

    def test_already_compact(self):
        assert _compact_text("abc") == "abc"


class TestMultisetCharHitRatio:
    def test_empty_needle(self):
        assert _multiset_char_hit_ratio("", "anything") == 0.0

    def test_full_match(self):
        assert _multiset_char_hit_ratio("abc", "cab") == 1.0

    def test_partial(self):
        out = _multiset_char_hit_ratio("abc", "axx")
        # Only 'a' matches → 1/3
        assert out == pytest.approx(1.0 / 3.0)

    def test_uses_multiset_count(self):
        # Two 'a' in needle but only one available in haystack → 1/2
        out = _multiset_char_hit_ratio("aab", "ab")
        assert out == pytest.approx(2.0 / 3.0)


class TestBigramJaccard:
    def test_short_strings_zero(self):
        assert _bigram_jaccard("a", "b") == 0.0
        assert _bigram_jaccard("", "abc") == 0.0

    def test_identical_strings_full(self):
        assert _bigram_jaccard("hello", "hello") == 1.0

    def test_no_overlap(self):
        assert _bigram_jaccard("ab", "cd") == 0.0

    def test_partial_overlap(self):
        # "abc" → {ab, bc}; "abd" → {ab, bd}; intersection={ab}, union={ab,bc,bd}
        out = _bigram_jaccard("abc", "abd")
        assert out == pytest.approx(1.0 / 3.0)


class TestLongestSubsequenceRatio:
    def test_empty_needle(self):
        assert _longest_subsequence_ratio("", "hay") == 0.0

    def test_full_subsequence(self):
        assert _longest_subsequence_ratio("abc", "axbxc") == 1.0

    def test_partial(self):
        # Find 'a' and 'b' in 'axb..' but not 'c' → 2/3
        out = _longest_subsequence_ratio("abc", "axb")
        assert out == pytest.approx(2.0 / 3.0)

    def test_no_match(self):
        assert _longest_subsequence_ratio("xyz", "abc") == 0.0


class TestScoreField:
    def test_exact_match_100(self):
        assert _score_field("hello", "hello") == 100.0

    def test_substring_match_boost(self):
        # Query contained in haystack but not equal → score ≥ 92
        out = _score_field("hello world", "hello")
        assert out >= 92

    def test_prefix_match(self):
        # 2+ char prefix → at least 88
        out = _score_field("hello world", "he")
        assert out >= 88

    def test_compact_substring_match(self):
        # "Hello, World" → compact "helloworld"; query "lowo" appears
        out = _score_field("Hello, World", "lo, Wo")
        assert out >= 86

    def test_no_match_returns_low(self):
        out = _score_field("hello", "xyz")
        # Some non-zero fallback through fuzzy scores but clearly below 86.
        assert out < 86

    def test_empty_inputs_zero(self):
        assert _score_field("", "x") == 0.0
        assert _score_field("y", "") == 0.0

    def test_single_char_in_haystack(self):
        # len(q) == 1 and present → score ≥ 68
        out = _score_field("apple", "a")
        assert out >= 68
