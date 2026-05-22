"""Coverage for ``tools.binary_extensions`` — the read/write skip list
shared across every file-tool implementation."""
from __future__ import annotations

import pytest

from tools.binary_extensions import BINARY_EXTENSIONS, has_binary_extension


class TestBinaryExtensions:
    def test_set_is_frozenset_for_immutability(self):
        assert isinstance(BINARY_EXTENSIONS, frozenset)

    def test_includes_common_image_formats(self):
        for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
            assert ext in BINARY_EXTENSIONS

    def test_includes_common_archive_formats(self):
        for ext in (".zip", ".tar", ".gz", ".7z", ".rar"):
            assert ext in BINARY_EXTENSIONS

    def test_excludes_pdf_intentionally(self):
        # Per the module's docstring: PDFs are text-inspectable so excluded.
        assert ".pdf" not in BINARY_EXTENSIONS

    def test_excludes_common_text_formats(self):
        for ext in (".txt", ".md", ".json", ".yaml", ".py", ".ts", ".js"):
            assert ext not in BINARY_EXTENSIONS


class TestHasBinaryExtension:
    @pytest.mark.parametrize("path", [
        "image.png", "/tmp/photo.JPG", "/home/u/x.wasm",
        "deep/path/archive.tar.gz", "track.mp3",
    ])
    def test_known_binary_paths_match(self, path: str):
        assert has_binary_extension(path) is True

    @pytest.mark.parametrize("path", [
        "file.txt", "README.md", "config.yaml", "main.py",
        "code.ts", "data.json", "doc.pdf",
    ])
    def test_known_text_paths_do_not_match(self, path: str):
        assert has_binary_extension(path) is False

    def test_case_insensitive(self):
        assert has_binary_extension("Photo.JPG") is True
        assert has_binary_extension("photo.JPEG") is True

    def test_no_extension_returns_false(self):
        assert has_binary_extension("README") is False
        assert has_binary_extension("Dockerfile") is False

    def test_empty_string_returns_false(self):
        assert has_binary_extension("") is False

    def test_double_extension_uses_last_dot(self):
        # archive.tar.gz → ".gz" is the relevant extension.
        assert has_binary_extension("archive.tar.gz") is True

    def test_dotfile_with_binary_suffix_matches(self):
        # ".pyc" alone is the extension of a hidden compiled-python file.
        assert has_binary_extension(".cache.pyc") is True

    def test_unknown_extension_returns_false(self):
        assert has_binary_extension("file.totally-made-up") is False
