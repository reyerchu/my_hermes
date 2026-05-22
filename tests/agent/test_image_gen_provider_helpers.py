"""Coverage for the pure helpers in ``agent.image_gen_provider`` —
resolve_aspect_ratio + the success_response / error_response builders.
No existing direct tests."""
from __future__ import annotations

import pytest

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    VALID_ASPECT_RATIOS,
    error_response,
    resolve_aspect_ratio,
    success_response,
)


class TestResolveAspectRatio:
    @pytest.mark.parametrize("value", VALID_ASPECT_RATIOS)
    def test_valid_values_pass_through(self, value):
        assert resolve_aspect_ratio(value) == value

    def test_case_insensitive_and_stripped(self):
        assert resolve_aspect_ratio(" LANDSCAPE ") == "landscape"
        assert resolve_aspect_ratio("Portrait") == "portrait"

    def test_unknown_value_falls_back_to_default(self):
        assert resolve_aspect_ratio("16:9") == DEFAULT_ASPECT_RATIO
        assert resolve_aspect_ratio("square2") == DEFAULT_ASPECT_RATIO

    def test_none_falls_back_to_default(self):
        assert resolve_aspect_ratio(None) == DEFAULT_ASPECT_RATIO

    def test_non_string_falls_back_to_default(self):
        assert resolve_aspect_ratio(16) == DEFAULT_ASPECT_RATIO  # type: ignore[arg-type]
        assert resolve_aspect_ratio([]) == DEFAULT_ASPECT_RATIO  # type: ignore[arg-type]


class TestSuccessResponse:
    def test_builds_expected_payload(self):
        resp = success_response(
            image="https://example/img.png",
            model="dall-e-3",
            prompt="a hat",
            aspect_ratio="square",
            provider="openai",
        )
        assert resp["success"] is True
        assert resp["image"] == "https://example/img.png"
        assert resp["model"] == "dall-e-3"
        assert resp["prompt"] == "a hat"
        assert resp["aspect_ratio"] == "square"
        assert resp["provider"] == "openai"

    def test_extra_kwargs_merged_into_payload(self):
        resp = success_response(
            image="x",
            model="m",
            prompt="p",
            aspect_ratio="landscape",
            provider="prov",
            extra={"upscaled": True, "seed": 42},
        )
        assert resp["upscaled"] is True
        assert resp["seed"] == 42


class TestErrorResponse:
    def test_default_shape(self):
        resp = error_response(error="boom")
        assert resp["success"] is False
        assert resp["image"] is None
        assert resp["error"] == "boom"
        # Default fields populated with empty-ish placeholders.
        assert resp["error_type"] == "provider_error"
        assert resp["provider"] == ""
        assert resp["model"] == ""
        assert resp["prompt"] == ""
        assert resp["aspect_ratio"] == DEFAULT_ASPECT_RATIO

    def test_caller_overrides(self):
        resp = error_response(
            error="auth",
            error_type="auth_error",
            provider="openai",
            model="dall-e",
            prompt="cat",
            aspect_ratio="portrait",
        )
        assert resp["error"] == "auth"
        assert resp["error_type"] == "auth_error"
        assert resp["provider"] == "openai"
        assert resp["model"] == "dall-e"
        assert resp["prompt"] == "cat"
        assert resp["aspect_ratio"] == "portrait"
