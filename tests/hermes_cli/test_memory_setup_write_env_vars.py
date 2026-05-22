"""Coverage for ``hermes_cli.memory_setup._write_env_vars``."""
from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli.memory_setup import _write_env_vars


class TestWriteEnvVars:
    def test_creates_file_when_missing(self, tmp_path: Path):
        target = tmp_path / "new" / ".env"
        _write_env_vars(target, {"FOO": "bar"})
        assert target.exists()
        assert "FOO=bar" in target.read_text(encoding="utf-8")

    def test_appends_to_existing_file(self, tmp_path: Path):
        target = tmp_path / ".env"
        target.write_text("EXISTING=value\n", encoding="utf-8")
        _write_env_vars(target, {"NEW": "key"})
        content = target.read_text(encoding="utf-8")
        assert "EXISTING=value" in content
        assert "NEW=key" in content

    def test_updates_existing_key_in_place(self, tmp_path: Path):
        target = tmp_path / ".env"
        target.write_text("FOO=old\nBAR=keep\n", encoding="utf-8")
        _write_env_vars(target, {"FOO": "new"})
        content = target.read_text(encoding="utf-8")
        assert "FOO=new" in content
        assert "FOO=old" not in content
        # Unrelated keys survive.
        assert "BAR=keep" in content

    def test_handles_lines_without_equals_sign(self, tmp_path: Path):
        target = tmp_path / ".env"
        target.write_text("# This is a comment\n\nFOO=1\n", encoding="utf-8")
        _write_env_vars(target, {"FOO": "2"})
        content = target.read_text(encoding="utf-8")
        # Comment and blank line preserved.
        assert "# This is a comment" in content
        assert "FOO=2" in content

    def test_multiple_writes_in_one_call(self, tmp_path: Path):
        target = tmp_path / ".env"
        _write_env_vars(target, {"A": "1", "B": "2", "C": "3"})
        content = target.read_text(encoding="utf-8")
        assert "A=1" in content
        assert "B=2" in content
        assert "C=3" in content

    def test_parent_directories_created(self, tmp_path: Path):
        target = tmp_path / "deep" / "nested" / ".env"
        _write_env_vars(target, {"X": "y"})
        assert target.exists()
        assert target.parent.is_dir()
