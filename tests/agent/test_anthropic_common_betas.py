"""Coverage for _common_betas_for_base_url in agent.anthropic_adapter."""
from __future__ import annotations

import pytest

from agent.anthropic_adapter import (
    _common_betas_for_base_url,
    _COMMON_BETAS,
    _CONTEXT_1M_BETA,
    _TOOL_STREAMING_BETA,
)


class TestCommonBetasForBaseUrl:
    def test_default_anthropic_url(self):
        out = _common_betas_for_base_url("https://api.anthropic.com")
        # All defaults present; no 1M context beta.
        for b in _COMMON_BETAS:
            assert b in out
        assert _CONTEXT_1M_BETA not in out

    def test_no_base_url(self):
        out = _common_betas_for_base_url(None)
        assert _CONTEXT_1M_BETA not in out

    def test_azure_endpoint_adds_1m_beta(self):
        out = _common_betas_for_base_url("https://my-resource.openai.azure.com")
        assert _CONTEXT_1M_BETA in out

    def test_drop_context_1m_beta_kills_it(self):
        out = _common_betas_for_base_url(
            "https://my-resource.openai.azure.com",
            drop_context_1m_beta=True,
        )
        assert _CONTEXT_1M_BETA not in out

    def test_minimax_strips_tool_streaming_and_1m(self):
        out = _common_betas_for_base_url("https://api.minimax.io/anthropic")
        assert _TOOL_STREAMING_BETA not in out
        assert _CONTEXT_1M_BETA not in out

    def test_minimax_does_not_add_1m_beta(self):
        # Even if some other path tried to add 1M, MiniMax strips it.
        out = _common_betas_for_base_url("https://api.minimaxi.com/anthropic")
        assert _CONTEXT_1M_BETA not in out

    def test_returns_list(self):
        assert isinstance(_common_betas_for_base_url(None), list)

    def test_does_not_mutate_module_constant(self):
        before = list(_COMMON_BETAS)
        _common_betas_for_base_url("https://my-resource.openai.azure.com")
        assert list(_COMMON_BETAS) == before
