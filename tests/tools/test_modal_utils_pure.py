"""Coverage for the pure wrappers exposed by
``tools.environments.modal_utils`` (the rest of the module is a
transport base class with no clean unit-test seams)."""
from __future__ import annotations

from tools.environments.modal_utils import (
    wrap_modal_stdin_heredoc,
    wrap_modal_sudo_pipe,
)


class TestWrapModalStdinHeredoc:
    def test_appends_heredoc_with_marker(self):
        out = wrap_modal_stdin_heredoc("cat", "hello\nworld")
        # Output shape: "cat << 'HERMES_EOF_<8hex>'\nhello\nworld\nHERMES_EOF_<8hex>"
        assert out.startswith("cat << '")
        assert "HERMES_EOF_" in out
        assert "hello\nworld" in out

    def test_marker_appears_at_start_and_end(self):
        out = wrap_modal_stdin_heredoc("cmd", "body")
        lines = out.split("\n")
        # First line carries `<<` + marker; last line is the bare marker.
        first = lines[0]
        last = lines[-1]
        assert last and last == first.rsplit("'", 2)[1]

    def test_marker_does_not_collide_with_stdin_content(self):
        # If stdin_data happened to contain a marker pattern the helper
        # would loop until uuid avoids the collision.  Force a near-collision
        # and verify the output uses a marker absent from stdin_data.
        stdin = "HERMES_EOF_aaaaaaaa\nHERMES_EOF_bbbbbbbb\nbody"
        out = wrap_modal_stdin_heredoc("cmd", stdin)
        # The chosen marker (first line's quoted token) must not appear
        # inside the stdin_data block.
        marker = out.split("'", 2)[1]
        assert marker not in stdin

    def test_empty_stdin_still_produces_valid_heredoc(self):
        out = wrap_modal_stdin_heredoc("cmd", "")
        # Wrapping an empty body still produces a valid `cmd << 'MARKER'\n\nMARKER`.
        assert out.startswith("cmd << '")
        assert out.endswith(out.split("'", 2)[1])

    def test_command_passes_through_unchanged(self):
        out = wrap_modal_stdin_heredoc("/usr/bin/python -c 'pass'", "body")
        # The shell command itself is not modified.
        assert out.startswith("/usr/bin/python -c 'pass' << '")


class TestWrapModalSudoPipe:
    def test_shell_quotes_the_sudo_stdin(self):
        out = wrap_modal_sudo_pipe("sudo apt update", "secret-pw")
        assert "printf '%s\\n' secret-pw" in out

    def test_strips_trailing_newline_from_sudo_stdin(self):
        out = wrap_modal_sudo_pipe("sudo x", "pw\n\n")
        # printf '%s\n' pw  (the trailing \n is stripped before quoting)
        assert "printf '%s\\n' pw |" in out

    def test_quotes_password_with_special_chars(self):
        out = wrap_modal_sudo_pipe("sudo x", "p'w!$")
        # shlex.quote handles quoting; the literal "p'w!$" must NOT appear
        # unquoted in the result.
        assert "p'w!$" not in out.split("|", 1)[0].replace(
            "printf '%s\\n' ", ""
        )

    def test_pipes_into_the_command(self):
        out = wrap_modal_sudo_pipe("sudo whoami", "pw")
        assert out.endswith(" | sudo whoami")
