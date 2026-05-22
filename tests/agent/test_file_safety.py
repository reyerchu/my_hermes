"""Coverage for ``agent.file_safety`` — the write/read denylist that gates
every tool's file-touching path.  No existing direct tests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from agent.file_safety import (
    build_write_denied_paths,
    build_write_denied_prefixes,
    get_read_block_error,
    get_safe_write_root,
    is_write_denied,
)


class TestBuildWriteDeniedPaths:
    def test_contains_etc_sensitive_files(self):
        paths = build_write_denied_paths("/home/test")
        # /etc paths exist on the host so realpath maps to themselves.
        assert any(p.endswith("/etc/sudoers") for p in paths)
        assert any(p.endswith("/etc/passwd") for p in paths)
        assert any(p.endswith("/etc/shadow") for p in paths)

    def test_contains_ssh_keys_for_supplied_home(self):
        paths = build_write_denied_paths("/home/test")
        assert any(p.endswith("/test/.ssh/authorized_keys") for p in paths)
        assert any(p.endswith("/test/.ssh/id_rsa") for p in paths)
        assert any(p.endswith("/test/.ssh/id_ed25519") for p in paths)
        assert any(p.endswith("/test/.ssh/config") for p in paths)

    def test_contains_shell_init_files(self):
        paths = build_write_denied_paths("/home/test")
        for tail in (".bashrc", ".zshrc", ".profile", ".bash_profile"):
            assert any(p.endswith(f"/test/{tail}") for p in paths)


class TestBuildWriteDeniedPrefixes:
    def test_each_prefix_ends_with_a_separator(self):
        prefixes = build_write_denied_prefixes("/home/test")
        assert prefixes  # non-empty
        for p in prefixes:
            assert p.endswith(os.sep)

    def test_contains_ssh_aws_gnupg_kube(self):
        prefixes = build_write_denied_prefixes("/home/test")
        tails = [".ssh", ".aws", ".gnupg", ".kube"]
        for tail in tails:
            assert any(p.endswith(f"/{tail}{os.sep}") for p in prefixes)


class TestGetSafeWriteRoot:
    def test_returns_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("HERMES_WRITE_SAFE_ROOT", raising=False)
        assert get_safe_write_root() is None

    def test_empty_string_returns_none(self, monkeypatch):
        monkeypatch.setenv("HERMES_WRITE_SAFE_ROOT", "")
        assert get_safe_write_root() is None

    def test_expanded_real_path(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_WRITE_SAFE_ROOT", str(tmp_path))
        assert get_safe_write_root() == str(tmp_path.resolve())

    def test_tilde_expansion(self, monkeypatch):
        monkeypatch.setenv("HERMES_WRITE_SAFE_ROOT", "~")
        root = get_safe_write_root()
        assert root == os.path.realpath(os.path.expanduser("~"))


class TestIsWriteDenied:
    def test_etc_passwd_blocked(self, monkeypatch):
        monkeypatch.delenv("HERMES_WRITE_SAFE_ROOT", raising=False)
        assert is_write_denied("/etc/passwd") is True

    def test_ssh_dir_blocked_via_prefix(self, monkeypatch):
        monkeypatch.delenv("HERMES_WRITE_SAFE_ROOT", raising=False)
        # Any path beneath ~/.ssh/ is blocked.
        path = os.path.expanduser("~/.ssh/anything.txt")
        assert is_write_denied(path) is True

    def test_random_path_outside_denylist_allowed(self, tmp_path, monkeypatch):
        monkeypatch.delenv("HERMES_WRITE_SAFE_ROOT", raising=False)
        assert is_write_denied(str(tmp_path / "foo.txt")) is False

    def test_safe_root_blocks_paths_outside(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_WRITE_SAFE_ROOT", str(tmp_path / "allowed"))
        (tmp_path / "allowed").mkdir()
        outside = tmp_path / "elsewhere" / "x.txt"
        assert is_write_denied(str(outside)) is True

    def test_safe_root_allows_paths_inside(self, tmp_path, monkeypatch):
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        monkeypatch.setenv("HERMES_WRITE_SAFE_ROOT", str(allowed))
        assert is_write_denied(str(allowed / "x.txt")) is False

    def test_safe_root_path_equal_is_allowed(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_WRITE_SAFE_ROOT", str(tmp_path))
        assert is_write_denied(str(tmp_path)) is False


class TestGetReadBlockError:
    def test_returns_none_for_random_path(self, tmp_path):
        assert get_read_block_error(str(tmp_path / "foo.txt")) is None

    def test_blocks_internal_skills_hub_paths(self, monkeypatch, tmp_path):
        # Pretend HERMES_HOME points at tmp_path so the blocked dirs
        # resolve to predictable locations.
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        blocked = tmp_path / "skills" / ".hub" / "index-cache" / "x.json"
        blocked.parent.mkdir(parents=True, exist_ok=True)
        blocked.write_text("y")
        err = get_read_block_error(str(blocked))
        assert err is not None
        assert "internal Hermes cache file" in err
        assert "skills_list" in err

    def test_blocks_skills_hub_parent_too(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        blocked = tmp_path / "skills" / ".hub" / "some-file.yaml"
        blocked.parent.mkdir(parents=True, exist_ok=True)
        blocked.write_text("y")
        err = get_read_block_error(str(blocked))
        assert err is not None
