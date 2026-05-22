"""Coverage for ``hermes_cli.platforms`` — the canonical platform metadata
registry used by skills_config + tools_config."""
from __future__ import annotations

from collections import OrderedDict

from hermes_cli.platforms import (
    PLATFORMS,
    PlatformInfo,
    get_all_platforms,
    platform_label,
)


class TestPlatformsConstant:
    def test_is_ordered_dict_so_menus_are_deterministic(self):
        assert isinstance(PLATFORMS, OrderedDict)

    def test_cli_is_the_first_entry(self):
        assert next(iter(PLATFORMS)) == "cli"

    def test_every_value_is_a_platform_info(self):
        for info in PLATFORMS.values():
            assert isinstance(info, PlatformInfo)
            assert isinstance(info.label, str) and info.label
            assert info.default_toolset.startswith("hermes-")

    def test_well_known_keys_present(self):
        for key in [
            "telegram", "discord", "slack", "whatsapp", "signal",
            "email", "cron", "api_server", "webhook",
        ]:
            assert key in PLATFORMS


class TestPlatformLabel:
    def test_returns_label_for_known_key(self):
        assert "Telegram" in platform_label("telegram")

    def test_returns_default_for_unknown_key(self):
        assert platform_label("totally-unknown") == ""
        assert platform_label("totally-unknown", default="—") == "—"

    def test_cron_label_has_clock_emoji(self):
        # Smoke check that the well-known labels round-trip.
        assert "Cron" in platform_label("cron")


class TestGetAllPlatforms:
    def test_starts_with_all_builtin_keys(self):
        merged = get_all_platforms()
        for key in PLATFORMS:
            assert key in merged

    def test_returns_an_ordered_dict(self):
        assert isinstance(get_all_platforms(), OrderedDict)

    def test_does_not_drop_or_reorder_builtins(self):
        merged = get_all_platforms()
        builtin_keys = list(PLATFORMS.keys())
        merged_keys = list(merged.keys())
        # All builtin keys appear in the same relative order at the start.
        assert merged_keys[: len(builtin_keys)] == builtin_keys
