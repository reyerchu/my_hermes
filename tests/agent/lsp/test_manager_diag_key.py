"""Coverage for ``_diag_key`` in ``agent.lsp.manager`` — the content
equality key used to filter LSP diagnostic deltas."""
from __future__ import annotations

import pytest

from agent.lsp.manager import _diag_key


def _diag(**overrides):
    base = {
        "severity": 1,
        "code": "E501",
        "source": "ruff",
        "message": "line too long",
        "range": {
            "start": {"line": 1, "character": 0},
            "end": {"line": 1, "character": 80},
        },
    }
    base.update(overrides)
    return base


class TestDiagKey:
    def test_same_dict_yields_same_key(self):
        a = _diag()
        b = _diag()
        assert _diag_key(a) == _diag_key(b)

    def test_different_severity_changes_key(self):
        assert _diag_key(_diag(severity=1)) != _diag_key(_diag(severity=2))

    def test_different_code_changes_key(self):
        assert _diag_key(_diag(code="E501")) != _diag_key(_diag(code="E502"))

    def test_different_source_changes_key(self):
        assert _diag_key(_diag(source="ruff")) != _diag_key(_diag(source="pyright"))

    def test_different_message_changes_key(self):
        assert _diag_key(_diag(message="a")) != _diag_key(_diag(message="b"))

    def test_message_whitespace_stripped(self):
        # Trailing whitespace doesn't change the key.
        a = _diag(message="line too long")
        b = _diag(message="line too long   ")
        assert _diag_key(a) == _diag_key(b)

    def test_int_code_coerced_to_string(self):
        assert _diag_key(_diag(code=42)) == _diag_key(_diag(code="42"))

    def test_missing_fields_use_defaults(self):
        # Diagnostic without severity falls back to 1; default message "".
        out1 = _diag_key({})
        out2 = _diag_key({"severity": 1, "message": "", "range": {}})
        assert out1 == out2

    def test_range_difference_changes_key(self):
        a = _diag(range={"start": {"line": 1, "character": 0},
                          "end": {"line": 1, "character": 80}})
        b = _diag(range={"start": {"line": 2, "character": 0},
                          "end": {"line": 2, "character": 80}})
        assert _diag_key(a) != _diag_key(b)

    def test_key_format_uses_null_byte_separator(self):
        # The implementation joins fields with \x00 so any field that
        # happens to contain another field's value can't collide.
        out = _diag_key(_diag())
        assert "\x00" in out
