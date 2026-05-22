"""Coverage for Nous helpers in agent.auxiliary_client:
_nous_extra_body, _nous_api_key, _nous_base_url, NOUS_EXTRA_BODY."""
from __future__ import annotations

import pytest

from agent.auxiliary_client import (
    _nous_extra_body,
    _nous_api_key,
    _nous_base_url,
    NOUS_EXTRA_BODY,
    _NOUS_DEFAULT_BASE_URL,
)


class TestNousExtraBody:
    def test_returns_dict_with_tags(self):
        out = _nous_extra_body()
        assert "tags" in out
        assert isinstance(out["tags"], list)

    def test_fresh_each_call(self):
        a = _nous_extra_body()
        b = _nous_extra_body()
        # Distinct dicts so mutation doesn't bleed across callers.
        assert a is not b

    def test_module_constant_present(self):
        # NOUS_EXTRA_BODY is the module-level snapshot.
        assert "tags" in NOUS_EXTRA_BODY


class TestNousApiKey:
    def test_agent_key_wins(self):
        out = _nous_api_key({"agent_key": "ak-123", "access_token": "at-x"})
        assert out == "ak-123"

    def test_falls_back_to_access_token(self):
        out = _nous_api_key({"access_token": "at-456"})
        assert out == "at-456"

    def test_empty_dict_returns_empty(self):
        assert _nous_api_key({}) == ""

    def test_empty_agent_key_falls_back(self):
        out = _nous_api_key({"agent_key": "", "access_token": "at"})
        # Empty string is falsy → uses access_token.
        assert out == "at"


class TestNousBaseUrl:
    def test_default(self, monkeypatch):
        monkeypatch.delenv("NOUS_INFERENCE_BASE_URL", raising=False)
        assert _nous_base_url() == _NOUS_DEFAULT_BASE_URL

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("NOUS_INFERENCE_BASE_URL", "https://custom.example/v1")
        assert _nous_base_url() == "https://custom.example/v1"
