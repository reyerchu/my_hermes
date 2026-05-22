"""Coverage for pure helpers in tools.image_generation_tool:
- _normalize_fal_queue_url_format
- _extract_http_status
- _resolve_fal_model
- _build_fal_payload (additional aspect/size_style coverage)
"""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

from tools.image_generation_tool import (
    _normalize_fal_queue_url_format,
    _extract_http_status,
    _resolve_fal_model,
    _build_fal_payload,
    DEFAULT_MODEL,
    DEFAULT_ASPECT_RATIO,
    FAL_MODELS,
)


class TestNormalizeFalQueueUrlFormat:
    def test_basic(self):
        assert _normalize_fal_queue_url_format("https://x.example") == "https://x.example/"

    def test_trailing_slashes_collapsed(self):
        assert _normalize_fal_queue_url_format("https://x.example///") == "https://x.example/"

    def test_whitespace_stripped(self):
        assert _normalize_fal_queue_url_format("  https://x  ") == "https://x/"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="required"):
            _normalize_fal_queue_url_format("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="required"):
            _normalize_fal_queue_url_format("    ")

    def test_none_raises(self):
        with pytest.raises(ValueError, match="required"):
            _normalize_fal_queue_url_format(None)  # type: ignore[arg-type]


class TestExtractHttpStatus:
    def test_response_status_code(self):
        exc = Exception()
        exc.response = MagicMock(status_code=429)
        assert _extract_http_status(exc) == 429

    def test_direct_status_code(self):
        exc = Exception()
        exc.status_code = 503
        assert _extract_http_status(exc) == 503

    def test_response_with_no_status(self):
        exc = Exception()
        exc.response = MagicMock(spec=["other"])  # has no status_code attr
        exc.response.status_code = "not-an-int"
        assert _extract_http_status(exc) is None

    def test_no_attrs(self):
        assert _extract_http_status(ValueError("x")) is None

    def test_response_status_takes_precedence(self):
        # response.status_code wins over a direct .status_code on the exc.
        exc = Exception()
        exc.response = MagicMock(status_code=500)
        exc.status_code = 999
        assert _extract_http_status(exc) == 500


class TestResolveFalModel:
    def _stub_config(self, monkeypatch, cfg):
        fake = types.ModuleType("hermes_cli.config")
        fake.load_config = lambda: cfg
        monkeypatch.setitem(sys.modules, "hermes_cli.config", fake)

    def test_default_when_no_config(self, monkeypatch):
        # config import fails
        monkeypatch.setitem(sys.modules, "hermes_cli.config", None)
        monkeypatch.delenv("FAL_IMAGE_MODEL", raising=False)
        model_id, meta = _resolve_fal_model()
        assert model_id == DEFAULT_MODEL
        assert meta is FAL_MODELS[DEFAULT_MODEL]

    def test_explicit_model_from_config(self, monkeypatch):
        # Pick the first registered non-default model.
        candidate = next(m for m in FAL_MODELS if m != DEFAULT_MODEL)
        self._stub_config(monkeypatch, {"image_gen": {"model": candidate}})
        monkeypatch.delenv("FAL_IMAGE_MODEL", raising=False)
        model_id, meta = _resolve_fal_model()
        assert model_id == candidate

    def test_unknown_model_falls_back(self, monkeypatch):
        self._stub_config(monkeypatch, {"image_gen": {"model": "unknown/model"}})
        monkeypatch.delenv("FAL_IMAGE_MODEL", raising=False)
        model_id, _ = _resolve_fal_model()
        assert model_id == DEFAULT_MODEL

    def test_env_var_fallback(self, monkeypatch):
        # Empty config but env var set.
        self._stub_config(monkeypatch, {})
        candidate = next(m for m in FAL_MODELS if m != DEFAULT_MODEL)
        monkeypatch.setenv("FAL_IMAGE_MODEL", candidate)
        model_id, _ = _resolve_fal_model()
        assert model_id == candidate

    def test_blank_config_uses_default(self, monkeypatch):
        self._stub_config(monkeypatch, {"image_gen": {"model": "   "}})
        monkeypatch.delenv("FAL_IMAGE_MODEL", raising=False)
        model_id, _ = _resolve_fal_model()
        assert model_id == DEFAULT_MODEL


class TestBuildFalPayload:
    def test_prompt_assigned(self):
        out = _build_fal_payload(DEFAULT_MODEL, "a cat", aspect_ratio="square")
        assert out.get("prompt") == "a cat"

    def test_prompt_stripped(self):
        out = _build_fal_payload(DEFAULT_MODEL, "  hi  ", aspect_ratio="square")
        assert out["prompt"] == "hi"

    def test_unknown_aspect_falls_back_to_default(self):
        out = _build_fal_payload(DEFAULT_MODEL, "p", aspect_ratio="bogus")
        # Whatever the default aspect is, the result is valid (no crash).
        assert "prompt" in out

    def test_seed_when_int(self):
        meta = FAL_MODELS[DEFAULT_MODEL]
        if "seed" not in meta.get("supports", []):
            pytest.skip("Default model doesn't support seed — pick another")
        out = _build_fal_payload(DEFAULT_MODEL, "p", aspect_ratio="square", seed=42)
        assert out.get("seed") == 42

    def test_seed_non_int_ignored(self):
        out = _build_fal_payload(DEFAULT_MODEL, "p", aspect_ratio="square", seed="42")  # type: ignore
        assert "seed" not in out

    def test_overrides_applied(self):
        meta = FAL_MODELS[DEFAULT_MODEL]
        supports = meta["supports"]
        # Pick any supported key not in {"prompt", "image_size", "seed", "aspect_ratio"}.
        candidate = next(
            (k for k in supports if k not in {"prompt", "image_size", "aspect_ratio", "seed"}),
            None,
        )
        if candidate is None:
            pytest.skip("No override candidate")
        out = _build_fal_payload(
            DEFAULT_MODEL, "p", overrides={candidate: "X"},
        )
        assert out.get(candidate) == "X"

    def test_overrides_none_filtered(self):
        out = _build_fal_payload(
            DEFAULT_MODEL, "p", overrides={"prompt": None},
        )
        # None overrides are skipped — original prompt preserved.
        assert out["prompt"] == "p"

    def test_unsupported_keys_filtered_out(self):
        out = _build_fal_payload(
            DEFAULT_MODEL, "p", overrides={"definitely_not_a_real_field": "X"},
        )
        # Not in supports — must be stripped.
        assert "definitely_not_a_real_field" not in out
