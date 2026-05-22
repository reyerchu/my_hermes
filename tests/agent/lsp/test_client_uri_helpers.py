"""Coverage for file_uri / uri_to_path / _end_position in
agent.lsp.client."""
from __future__ import annotations

import os

import pytest

from agent.lsp.client import file_uri, uri_to_path, _end_position


class TestFileUri:
    def test_absolute_path(self):
        out = file_uri("/etc/hosts")
        assert out == "file:///etc/hosts"

    def test_relative_path_resolved(self):
        # cwd-relative path gets absolutized.
        out = file_uri("foo.py")
        assert out.startswith("file://")
        assert out.endswith("/foo.py")

    def test_spaces_encoded(self):
        out = file_uri("/tmp/with space.txt")
        assert "%20" in out

    def test_unicode_encoded(self):
        out = file_uri("/tmp/café.txt")
        # Quote with safe="/:" — non-ASCII bytes percent-encoded.
        assert "%" in out


class TestUriToPath:
    def test_basic_inverse(self):
        if os.name == "nt":
            pytest.skip("POSIX-specific assertion")
        assert uri_to_path("file:///etc/hosts") == "/etc/hosts"

    def test_percent_decoded(self):
        out = uri_to_path("file:///tmp/with%20space.txt")
        assert "with space" in out

    def test_non_file_uri_passthrough(self):
        out = uri_to_path("https://example.com/x")
        assert out == "https://example.com/x"

    def test_round_trip(self):
        if os.name == "nt":
            pytest.skip("POSIX paths only")
        original = "/tmp/hello world.txt"
        assert uri_to_path(file_uri(original)) == os.path.normpath(original)


class TestEndPosition:
    def test_empty(self):
        assert _end_position("") == {"line": 0, "character": 0}

    def test_single_line(self):
        out = _end_position("hello")
        # line 0, character at end (5)
        assert out == {"line": 0, "character": 5}

    def test_two_lines_no_trailing_newline(self):
        out = _end_position("hi\nworld")
        # line 1 (zero-indexed), character at end of "world" (5)
        assert out == {"line": 1, "character": 5}

    def test_trailing_newline_starts_next_line(self):
        out = _end_position("hi\n")
        # Trailing newline → next line, column 0
        assert out["line"] == 1
        assert out["character"] == 0

    def test_trailing_cr_handled(self):
        out = _end_position("x\r")
        # \r alone is also treated as trailing.
        assert out["line"] >= 1
        assert out["character"] == 0

    def test_multiline_with_trailing_newline(self):
        out = _end_position("a\nb\n")
        # Lines "a", "b"; trailing \n → next line (index 2).
        assert out == {"line": 2, "character": 0}
