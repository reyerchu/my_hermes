"""Coverage for pure helpers in gateway.platforms.yuanbao_media."""
from __future__ import annotations

import io
import struct

import pytest

from gateway.platforms.yuanbao_media import (
    guess_mime_type,
    is_image,
    get_image_format,
    md5_hex,
    generate_file_id,
    parse_image_size,
    _basename_from_url,
)


class TestGuessMimeType:
    def test_png(self):
        assert guess_mime_type("foo.png") == "image/png"

    def test_jpg(self):
        assert guess_mime_type("foo.jpg") == "image/jpeg"

    def test_unknown_extension(self):
        assert guess_mime_type("foo.weird") == "application/octet-stream"

    def test_no_extension(self):
        assert guess_mime_type("README") == "application/octet-stream"

    def test_case_insensitive(self):
        # .PNG should resolve same as .png.
        assert guess_mime_type("Photo.PNG") == "image/png"


class TestIsImage:
    def test_mime_image_prefix(self):
        assert is_image("anything", mime_type="image/png") is True

    def test_extension_only(self):
        assert is_image("photo.jpg") is True
        assert is_image("clip.webp") is True

    def test_non_image_extension(self):
        assert is_image("doc.pdf") is False

    def test_no_extension_no_mime(self):
        assert is_image("README") is False


class TestGetImageFormat:
    def test_known_format(self):
        # image/png and image/jpeg should map to non-255 values.
        png = get_image_format("image/png")
        jpeg = get_image_format("image/jpeg")
        assert png != 255
        assert jpeg != 255

    def test_unknown_format_returns_255(self):
        assert get_image_format("application/octet-stream") == 255

    def test_case_insensitive(self):
        a = get_image_format("image/png")
        b = get_image_format("IMAGE/PNG")
        assert a == b


class TestMd5Hex:
    def test_known_value(self):
        # md5("hello") = 5d41402abc4b2a76b9719d911017c592
        assert md5_hex(b"hello") == "5d41402abc4b2a76b9719d911017c592"

    def test_empty(self):
        assert md5_hex(b"") == "d41d8cd98f00b204e9800998ecf8427e"


class TestGenerateFileId:
    def test_length_32(self):
        assert len(generate_file_id()) == 32

    def test_hex_only(self):
        out = generate_file_id()
        int(out, 16)  # must parse as hex

    def test_unique(self):
        ids = {generate_file_id() for _ in range(10)}
        assert len(ids) == 10


class TestParseImageSize:
    def test_png(self):
        # PNG signature + IHDR with width=8, height=16
        png = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", 8, 16) + b"\x00" * 5
        out = parse_image_size(png)
        assert out == {"width": 8, "height": 16}

    def test_jpeg(self):
        # Minimal JPEG: SOI + SOF0 marker with dimensions
        buf = bytearray()
        buf += b"\xFF\xD8"  # SOI
        buf += b"\xFF\xC0"  # SOF0
        buf += struct.pack(">H", 11)  # length (11 bytes including this length field)
        buf += b"\x08"  # precision
        buf += struct.pack(">H", 600)  # height
        buf += struct.pack(">H", 800)  # width
        buf += b"\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01"
        out = parse_image_size(bytes(buf))
        assert out == {"width": 800, "height": 600}

    def test_gif(self):
        gif = b"GIF89a" + struct.pack("<HH", 100, 200) + b"\x00" * 50
        out = parse_image_size(gif)
        assert out == {"width": 100, "height": 200}

    def test_webp_vp8x(self):
        # RIFF...WEBP VP8X header (width and height stored as +1)
        # 24 bytes of preamble + 6 bytes (3 width, 3 height) at offsets 24..29
        buf = bytearray()
        buf += b"RIFF" + b"\x00" * 4 + b"WEBP"  # 12 bytes
        buf += b"VP8X"  # 16 bytes
        # VP8X chunk size + flags + reserved (24 bytes total before W/H)
        buf += b"\x00" * 8
        # width-1, height-1 in 24-bit LE
        buf += struct.pack("<I", 99)[:3]  # width 100
        buf += struct.pack("<I", 199)[:3]  # height 200
        out = parse_image_size(bytes(buf))
        assert out == {"width": 100, "height": 200}

    def test_unknown_format_returns_none(self):
        assert parse_image_size(b"not an image") is None

    def test_empty(self):
        assert parse_image_size(b"") is None

    def test_truncated_png(self):
        # PNG sig but no IHDR data.
        assert parse_image_size(b"\x89PNG") is None


class TestBasenameFromUrl:
    def test_basic(self):
        assert _basename_from_url("https://example.com/path/foo.png") == "foo.png"

    def test_query_params_dropped(self):
        out = _basename_from_url("https://x/y/foo.jpg?a=1&b=2")
        assert out == "foo.jpg"

    def test_no_path(self):
        assert _basename_from_url("https://example.com") == ""

    def test_invalid_url(self):
        # Should not raise — returns "" via except branch.
        out = _basename_from_url("not a url")
        assert isinstance(out, str)
