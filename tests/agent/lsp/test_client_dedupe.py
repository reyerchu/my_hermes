"""Coverage for _dedupe + _diagnostic_key in agent.lsp.client."""
from __future__ import annotations

import pytest

from agent.lsp.client import _dedupe, _diagnostic_key


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


class TestDiagnosticKey:
    def test_same_dict_same_key(self):
        assert _diagnostic_key(_diag()) == _diagnostic_key(_diag())

    def test_int_code_coerced_to_str(self):
        assert _diagnostic_key(_diag(code=42)) == _diagnostic_key(_diag(code="42"))

    def test_severity_change_changes_key(self):
        assert _diagnostic_key(_diag(severity=1)) != _diagnostic_key(_diag(severity=2))

    def test_source_change_changes_key(self):
        assert _diagnostic_key(_diag(source="ruff")) != _diagnostic_key(_diag(source="pyright"))

    def test_range_change_changes_key(self):
        a = _diagnostic_key(_diag(range={"start": {"line": 1, "character": 0},
                                           "end": {"line": 1, "character": 80}}))
        b = _diagnostic_key(_diag(range={"start": {"line": 2, "character": 0},
                                           "end": {"line": 2, "character": 80}}))
        assert a != b

    def test_message_stripped(self):
        # Trailing whitespace in message doesn't change the key.
        a = _diagnostic_key(_diag(message="line too long"))
        b = _diagnostic_key(_diag(message="line too long    "))
        assert a == b

    def test_missing_severity_defaults_to_1(self):
        d = _diag()
        d.pop("severity")
        # Same key as severity=1.
        assert _diagnostic_key(d) == _diagnostic_key(_diag(severity=1))

    def test_null_separator_used(self):
        k = _diagnostic_key(_diag())
        assert "\x00" in k


class TestDedupe:
    def test_empty(self):
        assert _dedupe([]) == []

    def test_single_list_no_dupes(self):
        a = _diag()
        b = _diag(message="other")
        out = _dedupe([a, b])
        assert len(out) == 2

    def test_dedup_within_list(self):
        a = _diag()
        a2 = _diag()  # identical content
        out = _dedupe([a, a2])
        assert len(out) == 1

    def test_dedup_across_lists(self):
        a = _diag()
        # Same content but different dict instance
        b = _diag()
        out = _dedupe([a], [b])
        assert len(out) == 1

    def test_non_dict_entries_skipped(self):
        out = _dedupe([_diag(), "not a dict", 42])
        # Only the real diag survives.
        assert len(out) == 1

    def test_order_preserved(self):
        a = _diag(message="A")
        b = _diag(message="B")
        c = _diag(message="C")
        out = _dedupe([a, b, c])
        assert [x["message"] for x in out] == ["A", "B", "C"]
