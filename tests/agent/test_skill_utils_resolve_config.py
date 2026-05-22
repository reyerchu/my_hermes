"""Coverage for _resolve_dotpath + resolve_skill_config_values in
agent.skill_utils."""
from __future__ import annotations

import os

import pytest

from agent.skill_utils import (
    _resolve_dotpath,
    resolve_skill_config_values,
)


class TestResolveDotpath:
    def test_top_level(self):
        assert _resolve_dotpath({"a": 1}, "a") == 1

    def test_nested(self):
        assert _resolve_dotpath({"a": {"b": {"c": 42}}}, "a.b.c") == 42

    def test_missing_top(self):
        assert _resolve_dotpath({}, "a") is None

    def test_missing_middle(self):
        assert _resolve_dotpath({"a": {}}, "a.b") is None

    def test_non_dict_intermediate(self):
        assert _resolve_dotpath({"a": "string"}, "a.b") is None

    def test_empty_dotted_key(self):
        # Empty key: split returns [""] → looks up "" key.
        out = _resolve_dotpath({"": "x"}, "")
        assert out == "x"


class TestResolveSkillConfigValues:
    @pytest.fixture
    def hermes_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        # get_config_path reads config.yaml under HERMES_HOME.
        return tmp_path

    def test_no_config_file_uses_defaults(self, hermes_home):
        out = resolve_skill_config_values([
            {"key": "wiki.path", "default": "/default/path"},
        ])
        assert out == {"wiki.path": "/default/path"}

    def test_explicit_value_wins(self, hermes_home):
        config = hermes_home / "config.yaml"
        config.write_text(
            "skills:\n  config:\n    wiki:\n      path: /set/value\n",
            encoding="utf-8",
        )
        out = resolve_skill_config_values([
            {"key": "wiki.path", "default": "/default"},
        ])
        assert out["wiki.path"] == "/set/value"

    def test_path_expansion(self, hermes_home):
        config = hermes_home / "config.yaml"
        config.write_text(
            "skills:\n  config:\n    wiki:\n      path: ~/wiki\n",
            encoding="utf-8",
        )
        out = resolve_skill_config_values([
            {"key": "wiki.path", "default": ""},
        ])
        # ~ should be expanded
        assert "~" not in out["wiki.path"]

    def test_blank_string_falls_back_to_default(self, hermes_home):
        config = hermes_home / "config.yaml"
        config.write_text(
            "skills:\n  config:\n    wiki:\n      path: '   '\n",
            encoding="utf-8",
        )
        out = resolve_skill_config_values([
            {"key": "wiki.path", "default": "/default"},
        ])
        assert out["wiki.path"] == "/default"

    def test_default_used_when_missing(self, hermes_home):
        out = resolve_skill_config_values([
            {"key": "missing.key"},
        ])
        # No default → empty string fallback
        assert out["missing.key"] == ""

    def test_multiple_vars(self, hermes_home):
        config = hermes_home / "config.yaml"
        config.write_text(
            "skills:\n  config:\n"
            "    a: 1\n"
            "    b: 2\n",
            encoding="utf-8",
        )
        out = resolve_skill_config_values([
            {"key": "a", "default": 0},
            {"key": "b", "default": 0},
            {"key": "c", "default": "x"},
        ])
        assert out["a"] == 1
        assert out["b"] == 2
        assert out["c"] == "x"  # default

    def test_corrupt_yaml_uses_defaults(self, hermes_home):
        config = hermes_home / "config.yaml"
        config.write_text("not: valid: yaml::", encoding="utf-8")
        out = resolve_skill_config_values([
            {"key": "key", "default": "fallback"},
        ])
        assert out["key"] == "fallback"
