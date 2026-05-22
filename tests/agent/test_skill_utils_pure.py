"""Coverage for the pure helpers in ``agent.skill_utils``: parse_frontmatter,
skill_matches_platform, _normalize_string_set, extract_skill_description."""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from agent.skill_utils import (
    _normalize_string_set,
    extract_skill_description,
    parse_frontmatter,
    skill_matches_platform,
)


class TestParseFrontmatter:
    def test_no_frontmatter_returns_empty_dict_and_full_body(self):
        body = "Just a body, no frontmatter\n"
        fm, rest = parse_frontmatter(body)
        assert fm == {}
        assert rest == body

    def test_basic_frontmatter(self):
        text = "---\nname: foo\nversion: 1\n---\nBody here\n"
        fm, rest = parse_frontmatter(text)
        assert fm["name"] == "foo"
        assert fm["version"] == 1
        assert "Body here" in rest

    def test_unicode_in_frontmatter(self):
        text = "---\ntitle: 你好\n---\nbody"
        fm, rest = parse_frontmatter(text)
        assert fm.get("title") == "你好"
        assert rest.strip() == "body"

    def test_no_closing_delimiter_returns_empty_dict(self):
        # Frontmatter must be terminated by another --- line.  Unterminated
        # frontmatter is treated as plain body.
        text = "---\nname: foo\nno close"
        fm, rest = parse_frontmatter(text)
        assert fm == {}


class TestSkillMatchesPlatform:
    def test_missing_platforms_field_matches_all(self):
        assert skill_matches_platform({}) is True

    def test_empty_list_matches_all(self):
        assert skill_matches_platform({"platforms": []}) is True

    def test_string_value_normalised_to_list(self):
        # "linux" passed as a bare string still resolves.
        with patch("agent.skill_utils.sys.platform", "linux"):
            assert skill_matches_platform({"platforms": "linux"}) is True

    def test_macos_alias_maps_to_darwin(self):
        with patch("agent.skill_utils.sys.platform", "darwin"):
            assert skill_matches_platform({"platforms": ["macos"]}) is True

    def test_windows_alias_maps_to_win32(self):
        with patch("agent.skill_utils.sys.platform", "win32"):
            assert skill_matches_platform({"platforms": ["windows"]}) is True

    def test_mismatched_platform_returns_false(self):
        with patch("agent.skill_utils.sys.platform", "linux"):
            assert (
                skill_matches_platform({"platforms": ["macos"]}) is False
            )

    def test_multiple_platforms_any_match(self):
        with patch("agent.skill_utils.sys.platform", "linux"):
            assert (
                skill_matches_platform({"platforms": ["macos", "linux"]}) is True
            )

    def test_platform_is_case_insensitive(self):
        with patch("agent.skill_utils.sys.platform", "linux"):
            assert skill_matches_platform({"platforms": ["LINUX"]}) is True


class TestNormalizeStringSet:
    def test_none_returns_empty_set(self):
        assert _normalize_string_set(None) == set()

    def test_single_string_wraps_to_list(self):
        assert _normalize_string_set("foo") == {"foo"}

    def test_strips_whitespace_around_each_value(self):
        assert _normalize_string_set([" a ", "b "]) == {"a", "b"}

    def test_drops_empty_strings(self):
        assert _normalize_string_set(["a", "", "  "]) == {"a"}

    def test_coerces_non_string_to_str(self):
        assert _normalize_string_set([1, 2]) == {"1", "2"}

    def test_dedupes(self):
        assert _normalize_string_set(["a", "a", "a"]) == {"a"}


class TestExtractSkillDescription:
    def test_returns_description_field_when_present(self):
        assert extract_skill_description({"description": "Hello"}) == "Hello"

    def test_returns_empty_when_missing(self):
        assert extract_skill_description({}) == ""

    def test_strips_trailing_whitespace(self):
        # Whitespace is stripped to keep the prompt-injected description
        # compact.
        desc = extract_skill_description({"description": "  hi  "})
        assert desc.strip() == "hi"
