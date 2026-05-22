"""Coverage for ``agent.lmstudio_reasoning.resolve_lmstudio_effort``.

This function gates every LM Studio chat-completions request — a wrong
choice causes the server to 400 on an unsupported effort or silently
substitute one.  No existing direct tests.
"""
from __future__ import annotations

import pytest

from agent.lmstudio_reasoning import resolve_lmstudio_effort


class TestResolveLmstudioEffort:
    def test_default_medium_when_no_reasoning_config(self):
        assert resolve_lmstudio_effort(None, None) == "medium"
        assert resolve_lmstudio_effort({}, None) == "medium"

    def test_disabled_reasoning_returns_none_effort(self):
        assert (
            resolve_lmstudio_effort({"enabled": False}, None) == "none"
        )

    def test_explicit_effort_passes_through(self):
        assert (
            resolve_lmstudio_effort({"effort": "high"}, None) == "high"
        )

    def test_effort_is_case_insensitive_and_stripped(self):
        assert (
            resolve_lmstudio_effort({"effort": "  HIGH  "}, None) == "high"
        )

    def test_off_alias_maps_to_none(self):
        assert resolve_lmstudio_effort({"effort": "off"}, None) == "none"

    def test_on_alias_maps_to_medium(self):
        assert resolve_lmstudio_effort({"effort": "on"}, None) == "medium"

    def test_unknown_effort_falls_back_to_medium(self):
        assert (
            resolve_lmstudio_effort({"effort": "extreme"}, None) == "medium"
        )

    def test_empty_effort_string_falls_back_to_medium(self):
        assert resolve_lmstudio_effort({"effort": ""}, None) == "medium"

    def test_allowed_options_clamps_to_allowed_subset(self):
        # Model only allows the toggle style.
        result = resolve_lmstudio_effort(
            {"effort": "high"}, ["off", "on"]
        )
        # "high" not in {"none","medium"} after alias mapping → returns None.
        assert result is None

    def test_allowed_options_with_native_vocabulary(self):
        result = resolve_lmstudio_effort(
            {"effort": "high"}, ["low", "medium", "high"]
        )
        assert result == "high"

    def test_allowed_options_falsy_skips_clamp(self):
        # Empty list or None means "probe failed" — pass effort through.
        assert (
            resolve_lmstudio_effort({"effort": "xhigh"}, None) == "xhigh"
        )
        assert (
            resolve_lmstudio_effort({"effort": "xhigh"}, []) == "xhigh"
        )

    def test_disabled_overrides_explicit_effort(self):
        # When `enabled` is False the effort key is ignored entirely.
        assert (
            resolve_lmstudio_effort(
                {"enabled": False, "effort": "high"}, ["off", "on", "high"]
            )
            == "none"
        )

    def test_non_dict_reasoning_config_falls_back_to_medium(self):
        assert resolve_lmstudio_effort("nope", None) == "medium"  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "effort", ["none", "minimal", "low", "medium", "high", "xhigh"],
    )
    def test_all_native_efforts_recognised(self, effort):
        assert resolve_lmstudio_effort({"effort": effort}, None) == effort
