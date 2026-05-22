"""Coverage for get_pool_strategy in agent.credential_pool."""
from __future__ import annotations

import sys
import types

import pytest

from agent.credential_pool import (
    get_pool_strategy,
    STRATEGY_FILL_FIRST,
    STRATEGY_ROUND_ROBIN,
    STRATEGY_RANDOM,
    STRATEGY_LEAST_USED,
    SUPPORTED_POOL_STRATEGIES,
)


def _stub_config(monkeypatch, cfg):
    fake = types.ModuleType("hermes_cli.config")
    fake.load_config = lambda: cfg
    monkeypatch.setitem(sys.modules, "hermes_cli.config", fake)


class TestGetPoolStrategy:
    def test_default_when_config_unavailable(self, monkeypatch):
        # Force _load_config_safe to return None.
        from agent import credential_pool
        monkeypatch.setattr(credential_pool, "_load_config_safe", lambda: None)
        assert get_pool_strategy("openai") == STRATEGY_FILL_FIRST

    def test_default_when_strategies_missing(self, monkeypatch):
        from agent import credential_pool
        monkeypatch.setattr(credential_pool, "_load_config_safe", lambda: {})
        assert get_pool_strategy("openai") == STRATEGY_FILL_FIRST

    def test_default_when_strategies_not_dict(self, monkeypatch):
        from agent import credential_pool
        monkeypatch.setattr(
            credential_pool, "_load_config_safe",
            lambda: {"credential_pool_strategies": "not a dict"},
        )
        assert get_pool_strategy("openai") == STRATEGY_FILL_FIRST

    def test_unknown_provider_returns_default(self, monkeypatch):
        from agent import credential_pool
        monkeypatch.setattr(
            credential_pool, "_load_config_safe",
            lambda: {"credential_pool_strategies": {"other": STRATEGY_ROUND_ROBIN}},
        )
        assert get_pool_strategy("openai") == STRATEGY_FILL_FIRST

    @pytest.mark.parametrize("strategy", [
        STRATEGY_FILL_FIRST,
        STRATEGY_ROUND_ROBIN,
        STRATEGY_RANDOM,
        STRATEGY_LEAST_USED,
    ])
    def test_all_supported_strategies(self, monkeypatch, strategy):
        from agent import credential_pool
        monkeypatch.setattr(
            credential_pool, "_load_config_safe",
            lambda: {"credential_pool_strategies": {"openai": strategy}},
        )
        assert get_pool_strategy("openai") == strategy

    def test_case_insensitive_value(self, monkeypatch):
        from agent import credential_pool
        monkeypatch.setattr(
            credential_pool, "_load_config_safe",
            lambda: {"credential_pool_strategies": {"openai": "ROUND_ROBIN"}},
        )
        assert get_pool_strategy("openai") == STRATEGY_ROUND_ROBIN

    def test_whitespace_value_stripped(self, monkeypatch):
        from agent import credential_pool
        monkeypatch.setattr(
            credential_pool, "_load_config_safe",
            lambda: {"credential_pool_strategies": {"openai": "  random  "}},
        )
        assert get_pool_strategy("openai") == STRATEGY_RANDOM

    def test_unrecognised_value_falls_back(self, monkeypatch):
        from agent import credential_pool
        monkeypatch.setattr(
            credential_pool, "_load_config_safe",
            lambda: {"credential_pool_strategies": {"openai": "exotic"}},
        )
        assert get_pool_strategy("openai") == STRATEGY_FILL_FIRST

    def test_supported_strategies_set_complete(self):
        # The module constant should list all four canonical names.
        assert SUPPORTED_POOL_STRATEGIES == {
            STRATEGY_FILL_FIRST,
            STRATEGY_ROUND_ROBIN,
            STRATEGY_RANDOM,
            STRATEGY_LEAST_USED,
        }
