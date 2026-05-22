"""Coverage for ``_command_script_path`` in ``agent.shell_hooks`` —
the script-path extractor used by ``hermes doctor`` to spot drifted
hook scripts."""
from __future__ import annotations

import pytest

from agent.shell_hooks import _command_script_path


class TestCommandScriptPath:
    def test_bare_script_path(self):
        assert _command_script_path("/usr/local/bin/hook.sh") == "/usr/local/bin/hook.sh"

    def test_interpreter_plus_script(self):
        assert (
            _command_script_path("python3 /path/to/hook.py")
            == "/path/to/hook.py"
        )

    def test_env_shim_plus_script(self):
        assert (
            _command_script_path("/usr/bin/env bash hook.sh") == "hook.sh"
        )

    def test_no_known_extension_falls_back_to_slashed_token(self):
        # No recognised script extension; helper picks a token containing
        # a slash.
        assert _command_script_path("run /opt/hermes/runner") == "/opt/hermes/runner"

    def test_no_slash_no_extension_returns_first_token(self):
        assert _command_script_path("hookcmd") == "hookcmd"

    def test_tilde_prefix_treated_as_path_marker(self):
        assert _command_script_path("python ~/hooks/run") == "~/hooks/run"

    def test_unparseable_command_returned_unchanged(self):
        # An unclosed quote makes shlex.split() raise ValueError.
        raw = "python 'unterminated"
        out = _command_script_path(raw)
        assert out == raw

    def test_empty_string_returns_empty_string(self):
        # shlex.split("") yields []; helper falls through to "command".
        assert _command_script_path("") == ""

    @pytest.mark.parametrize("ext", [
        ".sh", ".bash", ".zsh", ".py", ".rb", ".pl", ".lua", ".js", ".ts",
    ])
    def test_each_extension_recognised(self, ext: str):
        cmd = f"runner /opt/hermes/hook{ext}"
        assert _command_script_path(cmd) == f"/opt/hermes/hook{ext}"
