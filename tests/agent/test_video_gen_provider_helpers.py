"""Coverage for the pure response builders in ``agent.video_gen_provider``."""
from __future__ import annotations

from agent.video_gen_provider import error_response, success_response


class TestSuccessResponse:
    def test_default_modality_and_aspect_ratio(self):
        resp = success_response(
            video="https://x/v.mp4",
            model="veo-3",
            prompt="surf",
            provider="google",
        )
        assert resp["success"] is True
        assert resp["video"] == "https://x/v.mp4"
        assert resp["modality"] == "text"  # default
        assert resp["aspect_ratio"] == ""
        assert resp["duration"] == 0

    def test_extra_kwargs_merged(self):
        resp = success_response(
            video="x",
            model="m",
            prompt="p",
            provider="prov",
            extra={"watermark": False, "fps": 24},
        )
        assert resp["watermark"] is False
        assert resp["fps"] == 24

    def test_explicit_modality_aspect_duration(self):
        resp = success_response(
            video="x",
            model="m",
            prompt="p",
            modality="image",
            aspect_ratio="9:16",
            duration=10,
            provider="prov",
        )
        assert resp["modality"] == "image"
        assert resp["aspect_ratio"] == "9:16"
        assert resp["duration"] == 10


class TestErrorResponse:
    def test_default_shape(self):
        resp = error_response(error="boom")
        assert resp == {
            "success": False,
            "video": None,
            "error": "boom",
            "error_type": "provider_error",
            "model": "",
            "prompt": "",
            "aspect_ratio": "",
            "provider": "",
        }

    def test_caller_overrides_every_field(self):
        resp = error_response(
            error="quota",
            error_type="rate_limit",
            provider="google",
            model="veo-3",
            prompt="surfing dog",
            aspect_ratio="9:16",
        )
        assert resp["error"] == "quota"
        assert resp["error_type"] == "rate_limit"
        assert resp["provider"] == "google"
        assert resp["model"] == "veo-3"
        assert resp["prompt"] == "surfing dog"
        assert resp["aspect_ratio"] == "9:16"
        assert resp["success"] is False
        assert resp["video"] is None
