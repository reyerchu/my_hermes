"""Coverage for ``utils.atomic_roundtrip_yaml_update`` — the comment-
preserving config writer used for user-edited YAML files."""
from __future__ import annotations

from pathlib import Path

import pytest

from utils import atomic_roundtrip_yaml_update


class TestAtomicRoundtripYamlUpdate:
    def test_creates_a_new_yaml_file_when_target_missing(self, tmp_path: Path):
        target = tmp_path / "config.yaml"
        atomic_roundtrip_yaml_update(target, "model.default", "claude-sonnet-4-6")
        assert target.exists()
        text = target.read_text(encoding="utf-8")
        assert "model:" in text
        assert "default: claude-sonnet-4-6" in text

    def test_updates_an_existing_top_level_key(self, tmp_path: Path):
        target = tmp_path / "config.yaml"
        target.write_text("foo: bar\nlast: keep\n", encoding="utf-8")
        atomic_roundtrip_yaml_update(target, "foo", "qux")
        text = target.read_text(encoding="utf-8")
        assert "foo: qux" in text
        # The unrelated sibling key survives.
        assert "last: keep" in text

    def test_creates_nested_path_when_intermediate_missing(self, tmp_path: Path):
        target = tmp_path / "config.yaml"
        atomic_roundtrip_yaml_update(target, "display.busy_input_mode", "queue")
        text = target.read_text(encoding="utf-8")
        assert "display:" in text
        assert "busy_input_mode: queue" in text

    def test_updates_a_deep_existing_key(self, tmp_path: Path):
        target = tmp_path / "config.yaml"
        target.write_text(
            "display:\n  busy_input_mode: interrupt\n",
            encoding="utf-8",
        )
        atomic_roundtrip_yaml_update(target, "display.busy_input_mode", "queue")
        text = target.read_text(encoding="utf-8")
        assert "busy_input_mode: queue" in text
        assert "interrupt" not in text

    def test_preserves_comments_around_updated_key(self, tmp_path: Path):
        target = tmp_path / "config.yaml"
        target.write_text(
            "# Top-level comment\n"
            "model:\n"
            "  # Default model used when no override is set.\n"
            "  default: claude-opus-4-7\n",
            encoding="utf-8",
        )
        atomic_roundtrip_yaml_update(
            target, "model.default", "claude-sonnet-4-6"
        )
        text = target.read_text(encoding="utf-8")
        assert "# Top-level comment" in text
        assert "# Default model used when no override is set." in text
        assert "default: claude-sonnet-4-6" in text

    def test_replaces_a_non_map_intermediate_value(self, tmp_path: Path):
        target = tmp_path / "config.yaml"
        target.write_text("a: scalar\n", encoding="utf-8")
        atomic_roundtrip_yaml_update(target, "a.b", 99)
        text = target.read_text(encoding="utf-8")
        # The scalar is replaced by a map containing the new leaf.
        assert "a:" in text
        assert "b: 99" in text

    def test_preserves_unicode_values(self, tmp_path: Path):
        target = tmp_path / "config.yaml"
        atomic_roundtrip_yaml_update(target, "greeting", "你好，世界 🌏")
        text = target.read_text(encoding="utf-8")
        assert "你好，世界 🌏" in text

    def test_writes_atomically_no_leftover_tmp_files(self, tmp_path: Path):
        target = tmp_path / "config.yaml"
        atomic_roundtrip_yaml_update(target, "key", "value")
        leftovers = [
            p.name
            for p in tmp_path.iterdir()
            if p.name.startswith(".config") and p.suffix == ".tmp"
        ]
        assert leftovers == []

    def test_creates_parent_directories_when_missing(self, tmp_path: Path):
        target = tmp_path / "nested" / "deep" / "config.yaml"
        atomic_roundtrip_yaml_update(target, "key", "value")
        assert target.exists()

    def test_existing_permission_bits_preserved(self, tmp_path: Path):
        import os
        import stat
        target = tmp_path / "config.yaml"
        target.write_text("foo: bar\n", encoding="utf-8")
        os.chmod(target, 0o644)
        before = stat.S_IMODE(target.stat().st_mode)
        assert before == 0o644
        atomic_roundtrip_yaml_update(target, "foo", "baz")
        after = stat.S_IMODE(target.stat().st_mode)
        assert after == 0o644
