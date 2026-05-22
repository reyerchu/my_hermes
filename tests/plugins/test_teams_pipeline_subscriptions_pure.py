"""Coverage for the pure helpers in
``plugins.teams_pipeline.subscriptions`` — _parse_bool and _parse_int."""
from __future__ import annotations

import pytest

from plugins.teams_pipeline.subscriptions import _parse_bool, _parse_int


class TestParseBool:
    @pytest.mark.parametrize("value", [True, False])
    def test_native_bool_passes_through(self, value):
        assert _parse_bool(value) is value

    @pytest.mark.parametrize("value", ["1", "true", "yes", "on", "TRUE", " On "])
    def test_truthy_strings(self, value):
        assert _parse_bool(value) is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", "FALSE", " Off "])
    def test_falsy_strings(self, value):
        assert _parse_bool(value) is False

    def test_unknown_string_uses_default(self):
        assert _parse_bool("maybe") is False
        assert _parse_bool("maybe", default=True) is True

    def test_none_uses_default(self):
        assert _parse_bool(None) is False
        assert _parse_bool(None, default=True) is True

    def test_integer_input_uses_default(self):
        # Implementation only accepts bool / str; other types pass to default.
        assert _parse_bool(1) is False
        assert _parse_bool(0, default=True) is True


class TestParseInt:
    def test_valid_integer_string(self):
        assert _parse_int("42", default=0) == 42
        assert _parse_int("-3", default=0) == -3

    def test_native_int_passes_through(self):
        assert _parse_int(7, default=0) == 7

    def test_invalid_returns_default(self):
        assert _parse_int("abc", default=99) == 99
        assert _parse_int(None, default=5) == 5

    def test_float_truncates(self):
        # int(3.7) == 3
        assert _parse_int(3.7, default=0) == 3
