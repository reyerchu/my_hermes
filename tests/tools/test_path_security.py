"""Coverage for ``tools.path_security`` — the validate_within_dir +
has_traversal_component helpers reused across every file-touching tool."""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.path_security import has_traversal_component, validate_within_dir


class TestValidateWithinDir:
    def test_returns_none_for_a_path_inside_root(self, tmp_path: Path):
        root = tmp_path
        inner = root / "subdir" / "file.txt"
        inner.parent.mkdir(parents=True)
        inner.write_text("x")
        assert validate_within_dir(inner, root) is None

    def test_returns_none_for_a_path_equal_to_root(self, tmp_path: Path):
        assert validate_within_dir(tmp_path, tmp_path) is None

    def test_returns_error_for_a_path_outside_root(self, tmp_path: Path):
        root = tmp_path / "inside"
        root.mkdir()
        outside = tmp_path / "outside.txt"
        outside.write_text("x")
        err = validate_within_dir(outside, root)
        assert err is not None
        assert "escapes" in err

    def test_traversal_via_parent_segments_caught(self, tmp_path: Path):
        root = tmp_path / "inside"
        root.mkdir()
        traversal = root / ".." / "secret.txt"
        err = validate_within_dir(traversal, root)
        # After .resolve() this points outside root.
        assert err is not None

    def test_symlinks_pointing_outside_root_are_caught(self, tmp_path: Path):
        root = tmp_path / "vault"
        root.mkdir()
        secret = tmp_path / "secret.txt"
        secret.write_text("nope")
        link = root / "link"
        link.symlink_to(secret)
        err = validate_within_dir(link, root)
        assert err is not None

    def test_nonexistent_path_inside_root_still_valid(self, tmp_path: Path):
        # Path.resolve() works on paths that don't exist yet.
        future = tmp_path / "not-yet" / "file.txt"
        assert validate_within_dir(future, tmp_path) is None


class TestHasTraversalComponent:
    def test_plain_relative_path_no_traversal(self):
        assert has_traversal_component("foo/bar.txt") is False

    def test_dot_dot_segment_detected(self):
        assert has_traversal_component("foo/../bar") is True

    def test_dot_dot_at_start(self):
        assert has_traversal_component("../escape") is True

    def test_dot_dot_at_end(self):
        assert has_traversal_component("foo/..") is True

    def test_single_dot_not_traversal(self):
        # Only ``..`` is flagged; a single ``.`` segment is not.
        assert has_traversal_component("./foo") is False

    def test_filename_containing_dots_not_traversal(self):
        # "..foo" and "foo.." are single segments, not parent references.
        assert has_traversal_component("..foo/bar") is False
        assert has_traversal_component("foo/bar..") is False

    def test_absolute_path_with_no_traversal_is_false(self):
        assert has_traversal_component("/etc/passwd") is False

    def test_absolute_path_with_traversal_is_true(self):
        assert has_traversal_component("/etc/../etc/passwd") is True

    def test_empty_string(self):
        assert has_traversal_component("") is False

    def test_root_only(self):
        assert has_traversal_component("/") is False
