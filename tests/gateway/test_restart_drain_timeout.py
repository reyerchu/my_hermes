"""Coverage for ``gateway.restart.parse_restart_drain_timeout``.

This helper is consumed by every restart path; a regression turning
restart drain into a no-wait or hang would be ugly to debug from logs."""
from __future__ import annotations

from gateway.restart import (
    DEFAULT_GATEWAY_RESTART_DRAIN_TIMEOUT,
    GATEWAY_SERVICE_RESTART_EXIT_CODE,
    parse_restart_drain_timeout,
)


class TestConstants:
    def test_exit_code_is_sysexits_tempfail(self):
        # EX_TEMPFAIL = 75 per sysexits.h.
        assert GATEWAY_SERVICE_RESTART_EXIT_CODE == 75

    def test_default_drain_timeout_is_positive_float(self):
        assert isinstance(DEFAULT_GATEWAY_RESTART_DRAIN_TIMEOUT, float)
        assert DEFAULT_GATEWAY_RESTART_DRAIN_TIMEOUT > 0


class TestParseRestartDrainTimeout:
    def test_returns_default_for_none(self):
        assert (
            parse_restart_drain_timeout(None)
            == DEFAULT_GATEWAY_RESTART_DRAIN_TIMEOUT
        )

    def test_returns_default_for_empty_string(self):
        assert (
            parse_restart_drain_timeout("")
            == DEFAULT_GATEWAY_RESTART_DRAIN_TIMEOUT
        )

    def test_returns_default_for_whitespace_only(self):
        assert (
            parse_restart_drain_timeout("   ")
            == DEFAULT_GATEWAY_RESTART_DRAIN_TIMEOUT
        )

    def test_parses_a_valid_float(self):
        assert parse_restart_drain_timeout("30") == 30.0
        assert parse_restart_drain_timeout("30.5") == 30.5

    def test_parses_an_integer_value(self):
        assert parse_restart_drain_timeout(15) == 15.0

    def test_falls_back_on_garbage_string(self):
        assert (
            parse_restart_drain_timeout("not-a-number")
            == DEFAULT_GATEWAY_RESTART_DRAIN_TIMEOUT
        )

    def test_negative_value_clamps_to_zero(self):
        assert parse_restart_drain_timeout("-5") == 0.0
        assert parse_restart_drain_timeout(-3.5) == 0.0

    def test_zero_string_is_accepted_as_explicit_zero(self):
        # "0" is non-empty after strip → parsed as 0.0 (not the default).
        assert parse_restart_drain_timeout("0") == 0.0

    def test_zero_int_falls_back_to_default(self):
        # `0 or ""` evaluates to "" so the int 0 path goes through the
        # default-branch.  Documented quirk; pinned here.
        assert (
            parse_restart_drain_timeout(0)
            == DEFAULT_GATEWAY_RESTART_DRAIN_TIMEOUT
        )
