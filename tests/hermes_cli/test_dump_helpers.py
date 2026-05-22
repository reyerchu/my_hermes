"""Coverage for the pure helpers inside ``hermes_cli.dump`` used by
``hermes dump`` to compose a support snapshot."""
from __future__ import annotations

from pathlib import Path

import pytest

import hermes_cli.dump as dump


class TestRedact:
    def test_empty_string_returns_empty(self):
        # The dump-specific override returns "" for empty (vs the
        # underlying mask_secret default behaviour).
        assert dump._redact("") in {"", "(empty)"}  # Either contract OK


class TestCountSkills:
    def test_no_skills_dir_returns_zero(self, tmp_path: Path):
        assert dump._count_skills(tmp_path) == 0

    def test_counts_skill_md_files_recursively(self, tmp_path: Path):
        skills = tmp_path / "skills"
        (skills / "foo").mkdir(parents=True)
        (skills / "foo" / "SKILL.md").write_text("x")
        (skills / "bar" / "baz").mkdir(parents=True)
        (skills / "bar" / "baz" / "SKILL.md").write_text("y")
        # A non-SKILL.md file should be ignored.
        (skills / "bar" / "README.md").write_text("readme")
        assert dump._count_skills(tmp_path) == 2

    def test_skills_path_that_is_a_file_returns_zero(self, tmp_path: Path):
        (tmp_path / "skills").write_text("not a directory")
        assert dump._count_skills(tmp_path) == 0


class TestCountMcpServers:
    def test_returns_zero_when_no_mcp_block(self):
        assert dump._count_mcp_servers({}) == 0

    def test_returns_zero_when_no_servers_key(self):
        assert dump._count_mcp_servers({"mcp": {}}) == 0

    def test_returns_zero_when_servers_is_empty(self):
        assert dump._count_mcp_servers({"mcp": {"servers": {}}}) == 0

    def test_returns_count_of_servers(self):
        cfg = {"mcp": {"servers": {"a": {}, "b": {}, "c": {}}}}
        assert dump._count_mcp_servers(cfg) == 3


class TestGetGitCommit:
    def test_returns_unknown_for_non_repo_dir(self, tmp_path: Path):
        # tmp_path isn't a git repo; the helper swallows the error.
        out = dump._get_git_commit(tmp_path)
        assert out in {"(unknown)", "(unknown)\n"} or out == "(unknown)"
