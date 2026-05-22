"""Coverage for extract_skill_config_vars in agent.skill_utils."""
from __future__ import annotations

import pytest

from agent.skill_utils import extract_skill_config_vars


def _frontmatter(config):
    return {"metadata": {"hermes": {"config": config}}}


class TestExtractSkillConfigVars:
    def test_no_metadata(self):
        assert extract_skill_config_vars({}) == []

    def test_metadata_not_dict(self):
        assert extract_skill_config_vars({"metadata": "string"}) == []

    def test_hermes_not_dict(self):
        assert extract_skill_config_vars({"metadata": {"hermes": "string"}}) == []

    def test_missing_config(self):
        assert extract_skill_config_vars({"metadata": {"hermes": {}}}) == []

    def test_falsy_config(self):
        assert extract_skill_config_vars(_frontmatter(None)) == []
        assert extract_skill_config_vars(_frontmatter([])) == []

    def test_basic_list(self):
        out = extract_skill_config_vars(_frontmatter([
            {"key": "wiki.path", "description": "Wiki dir", "default": "~/wiki"},
        ]))
        assert out == [
            {
                "key": "wiki.path",
                "description": "Wiki dir",
                "default": "~/wiki",
                "prompt": "Wiki dir",  # Default to description
            },
        ]

    def test_single_dict_auto_wrapped(self):
        # A single dict (not list) is allowed.
        out = extract_skill_config_vars(_frontmatter(
            {"key": "x", "description": "X"},
        ))
        assert len(out) == 1
        assert out[0]["key"] == "x"

    def test_non_list_non_dict_returns_empty(self):
        assert extract_skill_config_vars(_frontmatter("not a list")) == []

    def test_non_dict_entries_skipped(self):
        out = extract_skill_config_vars(_frontmatter([
            "not a dict",
            42,
            {"key": "x", "description": "X"},
        ]))
        assert [e["key"] for e in out] == ["x"]

    def test_blank_key_skipped(self):
        out = extract_skill_config_vars(_frontmatter([
            {"key": "  ", "description": "x"},
        ]))
        assert out == []

    def test_dedup_by_key(self):
        out = extract_skill_config_vars(_frontmatter([
            {"key": "x", "description": "first"},
            {"key": "x", "description": "second"},
        ]))
        # Only the first is kept.
        assert len(out) == 1
        assert out[0]["description"] == "first"

    def test_missing_description_skipped(self):
        out = extract_skill_config_vars(_frontmatter([
            {"key": "x"},
        ]))
        assert out == []

    def test_custom_prompt(self):
        out = extract_skill_config_vars(_frontmatter([
            {"key": "x", "description": "desc", "prompt": "  ask me!  "},
        ]))
        assert out[0]["prompt"] == "ask me!"

    def test_blank_prompt_falls_back_to_description(self):
        out = extract_skill_config_vars(_frontmatter([
            {"key": "x", "description": "desc", "prompt": "  "},
        ]))
        assert out[0]["prompt"] == "desc"

    def test_default_value_preserved(self):
        out = extract_skill_config_vars(_frontmatter([
            {"key": "x", "description": "d", "default": 42},
        ]))
        assert out[0]["default"] == 42

    def test_none_default_omitted(self):
        out = extract_skill_config_vars(_frontmatter([
            {"key": "x", "description": "d", "default": None},
        ]))
        assert "default" not in out[0]

    def test_key_whitespace_stripped(self):
        out = extract_skill_config_vars(_frontmatter([
            {"key": "  x  ", "description": "d"},
        ]))
        assert out[0]["key"] == "x"
