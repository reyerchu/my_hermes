"""Coverage for config-readers in tools.image_generation_tool —
_read_configured_image_model, _read_configured_image_provider."""
from __future__ import annotations

import sys
import types

import pytest

from tools.image_generation_tool import (
    _read_configured_image_model,
    _read_configured_image_provider,
)


def _stub_config(monkeypatch, cfg):
    fake = types.ModuleType("hermes_cli.config")
    fake.load_config = lambda: cfg
    monkeypatch.setitem(sys.modules, "hermes_cli.config", fake)


def _missing_config(monkeypatch):
    # Block hermes_cli.config from being importable.
    monkeypatch.setitem(sys.modules, "hermes_cli.config", None)


class TestReadConfiguredImageModel:
    def test_basic(self, monkeypatch):
        _stub_config(monkeypatch, {"image_gen": {"model": "fal-ai/flux"}})
        assert _read_configured_image_model() == "fal-ai/flux"

    def test_strips_whitespace(self, monkeypatch):
        _stub_config(monkeypatch, {"image_gen": {"model": "  fal-ai/x  "}})
        assert _read_configured_image_model() == "fal-ai/x"

    def test_blank_returns_none(self, monkeypatch):
        _stub_config(monkeypatch, {"image_gen": {"model": "   "}})
        assert _read_configured_image_model() is None

    def test_non_string_returns_none(self, monkeypatch):
        _stub_config(monkeypatch, {"image_gen": {"model": 42}})
        assert _read_configured_image_model() is None

    def test_no_section(self, monkeypatch):
        _stub_config(monkeypatch, {})
        assert _read_configured_image_model() is None

    def test_non_dict_section(self, monkeypatch):
        _stub_config(monkeypatch, {"image_gen": "not a dict"})
        assert _read_configured_image_model() is None

    def test_config_import_missing(self, monkeypatch):
        _missing_config(monkeypatch)
        assert _read_configured_image_model() is None


class TestReadConfiguredImageProvider:
    def test_basic(self, monkeypatch):
        _stub_config(monkeypatch, {"image_gen": {"provider": "openai"}})
        assert _read_configured_image_provider() == "openai"

    def test_strips_whitespace(self, monkeypatch):
        _stub_config(monkeypatch, {"image_gen": {"provider": "  fal  "}})
        assert _read_configured_image_provider() == "fal"

    def test_blank_returns_none(self, monkeypatch):
        _stub_config(monkeypatch, {"image_gen": {"provider": ""}})
        assert _read_configured_image_provider() is None

    def test_no_provider_returns_none(self, monkeypatch):
        _stub_config(monkeypatch, {"image_gen": {}})
        assert _read_configured_image_provider() is None

    def test_no_section(self, monkeypatch):
        _stub_config(monkeypatch, {})
        assert _read_configured_image_provider() is None

    def test_non_dict_top_level(self, monkeypatch):
        _stub_config(monkeypatch, "not a dict")
        assert _read_configured_image_provider() is None

    def test_config_import_missing(self, monkeypatch):
        _missing_config(monkeypatch)
        assert _read_configured_image_provider() is None
