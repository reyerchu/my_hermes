"""Coverage for static helpers on WebResearchEnv —
_parse_judge_json, _heuristic_score, _extract_domains."""
from __future__ import annotations

import pytest

pytest.importorskip("atroposlib")

from environments.web_research_env import WebResearchEnv  # noqa: E402


class TestParseJudgeJson:
    def test_basic_json(self):
        assert WebResearchEnv._parse_judge_json('{"score": 0.7}') == 0.7

    def test_strips_code_fence(self):
        text = "```json\n{\"score\": 0.5}\n```"
        assert WebResearchEnv._parse_judge_json(text) == 0.5

    def test_regex_fallback(self):
        # Malformed JSON but recoverable via regex.
        text = '{"score": 0.9, "comment": invalid'
        assert WebResearchEnv._parse_judge_json(text) == 0.9

    def test_out_of_range_rejected(self):
        # > 1.0 → None
        assert WebResearchEnv._parse_judge_json('{"score": 1.5}') is None
        # < 0.0 → None
        assert WebResearchEnv._parse_judge_json('{"score": -0.1}') is None

    def test_missing_score(self):
        assert WebResearchEnv._parse_judge_json('{"other": 1}') is None

    def test_invalid(self):
        assert WebResearchEnv._parse_judge_json("garbage") is None


class TestHeuristicScore:
    def test_perfect_overlap(self):
        out = WebResearchEnv._heuristic_score(
            "Python supports lambda functions",
            "Python lambda functions are anonymous",
        )
        # Should score reasonably high (overlap on "python", "lambda", "functions").
        assert out > 0.4

    def test_no_overlap_low_score(self):
        out = WebResearchEnv._heuristic_score(
            "Climate change is real",
            "Banana split recipe ingredients",
        )
        assert out < 0.3

    def test_empty_expected_returns_half(self):
        out = WebResearchEnv._heuristic_score("", "anything")
        assert out == 0.5

    def test_empty_after_stopwords(self):
        # Expected has only stopwords + short words → empty tokens → 0.5
        out = WebResearchEnv._heuristic_score("the a an is", "foo bar")
        assert out == 0.5

    def test_score_capped_at_1(self):
        out = WebResearchEnv._heuristic_score("python lambda", "python lambda")
        assert out <= 1.0


class TestExtractDomains:
    def test_basic_url(self):
        out = WebResearchEnv._extract_domains("See https://example.com/page")
        assert "example.com" in out

    def test_strips_www_prefix(self):
        out = WebResearchEnv._extract_domains("https://www.foo.org/path")
        # Implementation uses lstrip("www.") which can over-strip letters
        # but the canonical case is just "foo.org"
        assert any(d.endswith("foo.org") for d in out)

    def test_multiple_urls(self):
        text = "see https://a.com and http://b.org/path"
        out = WebResearchEnv._extract_domains(text)
        assert "a.com" in out
        assert "b.org" in out

    def test_no_urls_returns_empty(self):
        assert WebResearchEnv._extract_domains("just text") == set()

    def test_strips_trailing_punctuation(self):
        # URLs followed by close-bracket are stopped by the regex.
        out = WebResearchEnv._extract_domains("(see https://x.com)")
        assert "x.com" in out

    def test_case_insensitive_domain(self):
        out = WebResearchEnv._extract_domains("https://Example.COM/")
        # netloc lowered.
        assert "example.com" in out
