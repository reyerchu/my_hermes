"""Coverage for endpoint/model predicate helpers in agent.anthropic_adapter."""
from __future__ import annotations

import pytest

from agent.anthropic_adapter import (
    _normalize_base_url_text,
    _is_third_party_anthropic_endpoint,
    _is_kimi_coding_endpoint,
    _model_name_is_kimi_family,
    _is_kimi_family_endpoint,
    _is_deepseek_anthropic_endpoint,
    _requires_bearer_auth,
    _base_url_needs_context_1m_beta,
)


class TestNormalizeBaseUrlText:
    def test_none(self):
        assert _normalize_base_url_text(None) == ""

    def test_empty(self):
        assert _normalize_base_url_text("") == ""

    def test_strip_whitespace(self):
        assert _normalize_base_url_text("  https://x  ") == "https://x"

    def test_url_object_passes_through_str(self):
        # httpx.URL stringification works through plain str().
        import httpx
        out = _normalize_base_url_text(httpx.URL("https://x.example/"))
        assert "x.example" in out


class TestIsThirdPartyAnthropicEndpoint:
    def test_anthropic_direct(self):
        assert _is_third_party_anthropic_endpoint("https://api.anthropic.com") is False

    def test_anthropic_with_trailing_slash(self):
        assert _is_third_party_anthropic_endpoint("https://api.anthropic.com/") is False

    def test_no_base_url(self):
        assert _is_third_party_anthropic_endpoint(None) is False
        assert _is_third_party_anthropic_endpoint("") is False

    def test_third_party(self):
        assert _is_third_party_anthropic_endpoint("https://api.example/anthropic") is True

    def test_case_insensitive(self):
        assert _is_third_party_anthropic_endpoint("https://API.ANTHROPIC.COM") is False


class TestIsKimiCodingEndpoint:
    def test_matches(self):
        assert _is_kimi_coding_endpoint("https://api.kimi.com/coding") is True
        assert _is_kimi_coding_endpoint("https://api.kimi.com/coding/") is True

    def test_does_not_match(self):
        assert _is_kimi_coding_endpoint("https://api.kimi.com/") is False
        assert _is_kimi_coding_endpoint("https://api.anthropic.com") is False
        assert _is_kimi_coding_endpoint(None) is False


class TestModelNameIsKimiFamily:
    @pytest.mark.parametrize("model", [
        "kimi-k2.5", "kimi_thinking", "moonshot-v1-8k", "moonshot_v1_8k",
        "k1.5", "k1-thinking", "k2-foo", "k2.5", "k25-foo",
        "moonshotai/kimi-k2.5",
    ])
    def test_matches(self, model):
        assert _model_name_is_kimi_family(model) is True

    @pytest.mark.parametrize("model", [
        "claude-sonnet-4.6", "gpt-4o", "deepseek-chat", "llama-3", "",
    ])
    def test_no_match(self, model):
        assert _model_name_is_kimi_family(model) is False

    def test_non_string(self):
        assert _model_name_is_kimi_family(None) is False
        assert _model_name_is_kimi_family(42) is False  # type: ignore[arg-type]


class TestIsKimiFamilyEndpoint:
    def test_coding_path(self):
        assert _is_kimi_family_endpoint("https://api.kimi.com/coding") is True

    def test_kimi_host(self):
        assert _is_kimi_family_endpoint("https://api.kimi.com") is True

    def test_moonshot_host(self):
        assert _is_kimi_family_endpoint("https://api.moonshot.ai") is True
        assert _is_kimi_family_endpoint("https://api.moonshot.cn") is True

    def test_custom_endpoint_with_kimi_model(self):
        assert _is_kimi_family_endpoint(
            "https://my-proxy.example",
            model="kimi-k2.5",
        ) is True

    def test_unrelated_endpoint_no_kimi_model(self):
        assert _is_kimi_family_endpoint(
            "https://api.anthropic.com",
            model="claude-sonnet-4.6",
        ) is False


class TestIsDeepseekAnthropicEndpoint:
    def test_matches(self):
        assert _is_deepseek_anthropic_endpoint("https://api.deepseek.com/anthropic") is True

    def test_openai_compat_not_matched(self):
        # OpenAI-compatible base URL never reaches the anthropic adapter,
        # but the predicate must say False.
        assert _is_deepseek_anthropic_endpoint("https://api.deepseek.com") is False
        assert _is_deepseek_anthropic_endpoint("https://api.deepseek.com/v1") is False

    def test_other_hosts_not_matched(self):
        assert _is_deepseek_anthropic_endpoint("https://api.example.com/anthropic") is False
        assert _is_deepseek_anthropic_endpoint(None) is False


class TestRequiresBearerAuth:
    @pytest.mark.parametrize("url", [
        "https://api.minimax.io/anthropic",
        "https://api.minimax.io/anthropic/",
        "https://api.minimax.io/anthropic/v1",
        "https://api.minimaxi.com/anthropic",
    ])
    def test_minimax_matches(self, url):
        assert _requires_bearer_auth(url) is True

    @pytest.mark.parametrize("url", [
        "https://api.anthropic.com",
        "https://api.minimax.io/",  # no /anthropic
        None,
        "",
    ])
    def test_no_match(self, url):
        assert _requires_bearer_auth(url) is False


class TestBaseUrlNeedsContext1mBeta:
    def test_azure(self):
        assert _base_url_needs_context_1m_beta("https://my-resource.openai.azure.com") is True

    def test_other(self):
        assert _base_url_needs_context_1m_beta("https://api.anthropic.com") is False
        assert _base_url_needs_context_1m_beta(None) is False
        assert _base_url_needs_context_1m_beta("") is False
