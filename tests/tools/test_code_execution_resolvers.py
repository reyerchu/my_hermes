"""Coverage for _is_usable_python, _resolve_child_python, and
_resolve_child_cwd in tools.code_execution_tool."""
from __future__ import annotations

import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from tools.code_execution_tool import (
    _is_usable_python,
    _resolve_child_python,
    _resolve_child_cwd,
)


@pytest.fixture(autouse=True)
def _clear_caches():
    # Clear the lru_cache between tests so different stubbed paths
    # don't share state.
    _is_usable_python.cache_clear()
    yield
    _is_usable_python.cache_clear()


class TestIsUsablePython:
    def test_current_interpreter_passes(self):
        assert _is_usable_python(sys.executable) is True

    def test_missing_binary_returns_false(self):
        assert _is_usable_python("/definitely/not/here/python") is False

    def test_subprocess_timeout_returns_false(self, monkeypatch):
        def _raise(*a, **kw):
            raise subprocess.TimeoutExpired(cmd="x", timeout=5)
        monkeypatch.setattr(subprocess, "run", _raise)
        # Bust cache
        _is_usable_python.cache_clear()
        assert _is_usable_python("/usr/bin/python") is False

    def test_nonzero_return_code_means_unusable(self, monkeypatch):
        result = MagicMock(returncode=1)
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        _is_usable_python.cache_clear()
        assert _is_usable_python("/usr/bin/python") is False


class TestResolveChildPython:
    def test_strict_uses_sys_executable(self):
        assert _resolve_child_python("strict") == sys.executable

    def test_project_no_venv_uses_sys_executable(self, monkeypatch):
        monkeypatch.delenv("VIRTUAL_ENV", raising=False)
        monkeypatch.delenv("CONDA_PREFIX", raising=False)
        assert _resolve_child_python("project") == sys.executable

    def test_project_with_valid_venv_picks_venv_python(self, monkeypatch, tmp_path):
        # Build a fake venv layout pointing at the real sys.executable
        # so the version check passes.
        venv = tmp_path / "venv"
        bin_dir = venv / ("Scripts" if os.name == "nt" else "bin")
        bin_dir.mkdir(parents=True)
        # Symlink Python so it's executable.
        exe_name = "python.exe" if os.name == "nt" else "python"
        py_link = bin_dir / exe_name
        try:
            py_link.symlink_to(sys.executable)
        except OSError:
            pytest.skip("Cannot symlink in this environment")
        monkeypatch.setenv("VIRTUAL_ENV", str(venv))
        monkeypatch.delenv("CONDA_PREFIX", raising=False)
        out = _resolve_child_python("project")
        assert out == str(py_link)

    def test_project_with_broken_venv_falls_back(self, monkeypatch, tmp_path):
        # Venv path with no python binary.
        venv = tmp_path / "broken"
        (venv / "bin").mkdir(parents=True)
        monkeypatch.setenv("VIRTUAL_ENV", str(venv))
        monkeypatch.delenv("CONDA_PREFIX", raising=False)
        assert _resolve_child_python("project") == sys.executable


class TestResolveChildCwd:
    def test_strict_uses_staging_dir(self, tmp_path):
        assert _resolve_child_cwd("strict", str(tmp_path)) == str(tmp_path)

    def test_project_uses_terminal_cwd_when_set(self, tmp_path, monkeypatch):
        target = tmp_path / "project"
        target.mkdir()
        monkeypatch.setenv("TERMINAL_CWD", str(target))
        out = _resolve_child_cwd("project", staging_dir="/should/not/use")
        assert out == str(target)

    def test_project_expanduser_on_terminal_cwd(self, tmp_path, monkeypatch):
        # ~ should be expanded; we can't easily fake $HOME without
        # affecting other things, so just check non-tilde paths.
        target = tmp_path / "p2"
        target.mkdir()
        monkeypatch.setenv("TERMINAL_CWD", str(target))
        assert _resolve_child_cwd("project", staging_dir="/x") == str(target)

    def test_project_invalid_terminal_cwd_falls_back_to_getcwd(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TERMINAL_CWD", "/definitely/missing/dir")
        out = _resolve_child_cwd("project", staging_dir=str(tmp_path))
        # The current working directory is always a real dir on test
        # invocation, so we get it back.
        assert out == os.getcwd()

    def test_project_no_terminal_cwd_uses_getcwd(self, monkeypatch, tmp_path):
        monkeypatch.delenv("TERMINAL_CWD", raising=False)
        out = _resolve_child_cwd("project", staging_dir=str(tmp_path))
        assert out == os.getcwd()

    def test_blank_terminal_cwd_ignored(self, monkeypatch, tmp_path):
        monkeypatch.setenv("TERMINAL_CWD", "   ")
        out = _resolve_child_cwd("project", staging_dir=str(tmp_path))
        assert out == os.getcwd()
