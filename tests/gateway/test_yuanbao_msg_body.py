"""Coverage for build_image_msg_body and build_file_msg_body
in gateway.platforms.yuanbao_media."""
from __future__ import annotations

import pytest

from gateway.platforms.yuanbao_media import (
    build_image_msg_body,
    build_file_msg_body,
    get_image_format,
)


class TestBuildImageMsgBody:
    def test_basic(self):
        out = build_image_msg_body(
            url="https://example/x.png",
            uuid="abc123",
            filename="photo.png",
            size=1024,
            width=100,
            height=200,
            mime_type="image/png",
        )
        assert len(out) == 1
        m = out[0]
        assert m["msg_type"] == "TIMImageElem"
        c = m["msg_content"]
        assert c["uuid"] == "abc123"
        assert c["image_format"] == get_image_format("image/png")
        assert len(c["image_info_array"]) == 1
        img = c["image_info_array"][0]
        assert img == {
            "type": 1,
            "size": 1024,
            "width": 100,
            "height": 200,
            "url": "https://example/x.png",
        }

    def test_uuid_falls_back_to_filename(self):
        out = build_image_msg_body(
            url="https://x/y.png",
            uuid=None,
            filename="bar.png",
        )
        assert out[0]["msg_content"]["uuid"] == "bar.png"

    def test_uuid_falls_back_to_basename(self):
        out = build_image_msg_body(
            url="https://x/y/qux.gif",
            uuid=None,
            filename=None,
        )
        # _basename_from_url extracts "qux.gif"
        assert out[0]["msg_content"]["uuid"] == "qux.gif"

    def test_uuid_final_fallback_image(self):
        out = build_image_msg_body(url="not a valid url", uuid=None, filename=None)
        # Final fallback is the literal "image"
        assert out[0]["msg_content"]["uuid"] in {"image", "not a valid url".rsplit("/", 1)[-1]}

    def test_no_mime_uses_255(self):
        out = build_image_msg_body(url="https://x/y.png")
        # image_format defaults to 255 when mime_type is empty.
        assert out[0]["msg_content"]["image_format"] == 255

    def test_defaults_zero_dimensions(self):
        out = build_image_msg_body(url="https://x/y.png")
        img = out[0]["msg_content"]["image_info_array"][0]
        assert img["size"] == 0
        assert img["width"] == 0
        assert img["height"] == 0


class TestBuildFileMsgBody:
    def test_basic(self):
        out = build_file_msg_body(
            url="https://example/x.pdf",
            filename="doc.pdf",
            uuid="abc",
            size=4096,
        )
        assert len(out) == 1
        m = out[0]
        assert m["msg_type"] == "TIMFileElem"
        c = m["msg_content"]
        assert c == {
            "uuid": "abc",
            "file_name": "doc.pdf",
            "file_size": 4096,
            "url": "https://example/x.pdf",
        }

    def test_uuid_falls_back_to_filename(self):
        out = build_file_msg_body(
            url="https://x/y.txt",
            filename="report.txt",
            uuid=None,
        )
        assert out[0]["msg_content"]["uuid"] == "report.txt"

    def test_default_size_zero(self):
        out = build_file_msg_body(
            url="https://x/y.txt",
            filename="a.txt",
        )
        assert out[0]["msg_content"]["file_size"] == 0
