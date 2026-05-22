"""Coverage for the prompt_toolkit ANSI escape-sequence augmentations
in ``hermes_cli.pt_input_extras``."""
from __future__ import annotations

import pytest

prompt_toolkit = pytest.importorskip("prompt_toolkit")

from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES
from prompt_toolkit.keys import Keys

from hermes_cli.pt_input_extras import (
    install_ctrl_enter_alias,
    install_shift_enter_alias,
)


ALT_ENTER = (Keys.Escape, Keys.ControlM)


@pytest.fixture(autouse=True)
def _restore_sequences():
    # Snapshot the affected keys so test order doesn't matter — installs
    # are global and would otherwise leak between tests + into other
    # test files in the same run.
    affected = (
        "\x1b[13;2u", "\x1b[27;2;13~", "\x1b[27;2;13u",
        "\x1b[13;5u", "\x1b[27;5;13~", "\x1b[27;5;13u",
    )
    snapshot = {k: ANSI_SEQUENCES.get(k) for k in affected}
    try:
        yield
    finally:
        for k, v in snapshot.items():
            if v is None:
                ANSI_SEQUENCES.pop(k, None)
            else:
                ANSI_SEQUENCES[k] = v


class TestInstallShiftEnterAlias:
    def test_first_call_maps_all_three_shift_enter_sequences(self):
        for seq in ("\x1b[13;2u", "\x1b[27;2;13~", "\x1b[27;2;13u"):
            ANSI_SEQUENCES.pop(seq, None)
        changed = install_shift_enter_alias()
        assert changed >= 1
        for seq in ("\x1b[13;2u", "\x1b[27;2;13~", "\x1b[27;2;13u"):
            assert ANSI_SEQUENCES.get(seq) == ALT_ENTER

    def test_idempotent_after_first_install(self):
        install_shift_enter_alias()
        assert install_shift_enter_alias() == 0

    def test_overwrites_an_existing_wrong_mapping(self):
        ANSI_SEQUENCES["\x1b[13;2u"] = Keys.ControlM
        changed = install_shift_enter_alias()
        # At least the wrong-mapping entry was rewritten.
        assert changed >= 1
        assert ANSI_SEQUENCES["\x1b[13;2u"] == ALT_ENTER


class TestInstallCtrlEnterAlias:
    def test_first_call_maps_all_three_ctrl_enter_sequences(self):
        for seq in ("\x1b[13;5u", "\x1b[27;5;13~", "\x1b[27;5;13u"):
            ANSI_SEQUENCES.pop(seq, None)
        changed = install_ctrl_enter_alias()
        assert changed >= 1
        for seq in ("\x1b[13;5u", "\x1b[27;5;13~", "\x1b[27;5;13u"):
            assert ANSI_SEQUENCES.get(seq) == ALT_ENTER

    def test_idempotent_after_first_install(self):
        install_ctrl_enter_alias()
        assert install_ctrl_enter_alias() == 0

    def test_does_not_disturb_shift_enter_mappings(self):
        install_shift_enter_alias()
        before = {
            seq: ANSI_SEQUENCES[seq]
            for seq in ("\x1b[13;2u", "\x1b[27;2;13~", "\x1b[27;2;13u")
        }
        install_ctrl_enter_alias()
        after = {
            seq: ANSI_SEQUENCES[seq]
            for seq in ("\x1b[13;2u", "\x1b[27;2;13~", "\x1b[27;2;13u")
        }
        assert before == after
