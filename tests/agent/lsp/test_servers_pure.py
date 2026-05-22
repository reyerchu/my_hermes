"""Coverage for pure helpers in ``agent.lsp.servers``."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from agent.lsp.servers import _file_ext_or_basename, _which, LANGUAGE_BY_EXT


class TestFileExtOrBasename:
    def test_normal_file_returns_lowercase_extension(self):
        assert _file_ext_or_basename("/path/to/foo.PY") == ".py"
        assert _file_ext_or_basename("foo.ts") == ".ts"

    def test_extensionless_returns_full_basename(self):
        assert _file_ext_or_basename("/path/Dockerfile") == "Dockerfile"
        assert _file_ext_or_basename("Makefile") == "Makefile"

    def test_hidden_dotfile_with_no_other_extension(self):
        # ".env" — splitext treats "" as root and ".env" as ext.
        out = _file_ext_or_basename("/x/.env")
        # Either ".env" extension or ".env" basename — both reasonable.
        assert out in {".env", ""}

    def test_double_extension_uses_last(self):
        assert _file_ext_or_basename("archive.tar.gz") == ".gz"


class TestWhich:
    def test_returns_first_found(self):
        # Linux always has /bin/sh; we should get its absolute path.
        out = _which("definitely-missing-binary-xyz", "sh")
        assert out is not None
        assert out.endswith("/sh")

    def test_returns_none_when_nothing_found(self):
        out = _which("definitely-missing-1", "definitely-missing-2")
        assert out is None

    def test_empty_args_returns_none(self):
        assert _which() is None


class TestLanguageByExt:
    def test_python_maps(self):
        assert LANGUAGE_BY_EXT[".py"] == "python"
        assert LANGUAGE_BY_EXT[".pyi"] == "python"

    def test_typescript_split_by_jsx(self):
        assert LANGUAGE_BY_EXT[".ts"] == "typescript"
        assert LANGUAGE_BY_EXT[".tsx"] == "typescriptreact"

    def test_javascript_split_by_jsx(self):
        assert LANGUAGE_BY_EXT[".js"] == "javascript"
        assert LANGUAGE_BY_EXT[".jsx"] == "javascriptreact"

    def test_module_extensions_mapped(self):
        assert LANGUAGE_BY_EXT[".mjs"] == "javascript"
        assert LANGUAGE_BY_EXT[".cjs"] == "javascript"
        assert LANGUAGE_BY_EXT[".mts"] == "typescript"
        assert LANGUAGE_BY_EXT[".cts"] == "typescript"
