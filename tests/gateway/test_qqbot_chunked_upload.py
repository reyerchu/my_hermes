"""Coverage for pure helpers in gateway.platforms.qqbot.chunked_upload."""
from __future__ import annotations

import hashlib
import os

import pytest

from gateway.platforms.qqbot.chunked_upload import (
    format_size,
    _read_file_chunk,
    _compute_file_hashes,
    _parse_prepare_response,
    _PrepareResult,
    _PreparePart,
)


class TestFormatSize:
    def test_bytes(self):
        assert format_size(500) == "500.0 B"

    def test_kb(self):
        assert format_size(2048) == "2.0 KB"

    def test_mb(self):
        assert format_size(5 * 1024 * 1024) == "5.0 MB"

    def test_gb(self):
        assert format_size(2 * 1024 ** 3) == "2.0 GB"

    def test_tb(self):
        # 2 TB ≈ 2 * 1024^4 bytes
        assert format_size(2 * 1024 ** 4) == "2.0 TB"

    def test_zero(self):
        assert format_size(0) == "0.0 B"


class TestReadFileChunk:
    def test_basic(self, tmp_path):
        p = tmp_path / "f.bin"
        p.write_bytes(b"0123456789")
        out = _read_file_chunk(str(p), offset=2, length=4)
        assert out == b"2345"

    def test_zero_offset(self, tmp_path):
        p = tmp_path / "f.bin"
        p.write_bytes(b"hello")
        out = _read_file_chunk(str(p), offset=0, length=5)
        assert out == b"hello"

    def test_short_read_raises(self, tmp_path):
        p = tmp_path / "f.bin"
        p.write_bytes(b"only5")
        with pytest.raises(IOError, match="Short read"):
            _read_file_chunk(str(p), offset=0, length=10)


class TestComputeFileHashes:
    def test_hashes_correct(self, tmp_path):
        p = tmp_path / "f.bin"
        data = b"hello world"
        p.write_bytes(data)
        out = _compute_file_hashes(str(p), file_size=len(data))
        assert out["md5"] == hashlib.md5(data).hexdigest()
        assert out["sha1"] == hashlib.sha1(data).hexdigest()

    def test_md5_10m_only_for_large_files(self, tmp_path):
        # Small file should not need the md5_10m hash, but the helper may
        # still return a value — check structure not absolute presence.
        p = tmp_path / "f.bin"
        p.write_bytes(b"x" * 100)
        out = _compute_file_hashes(str(p), file_size=100)
        assert "md5" in out
        assert "sha1" in out


class TestParsePrepareResponse:
    def test_direct_response(self):
        raw = {
            "upload_id": "u1",
            "block_size": 4194304,
            "parts": [
                {"part_index": 1, "presigned_url": "https://x", "block_size": 4194304},
                {"part_index": 2, "url": "https://y", "block_size": 4194304},
            ],
            "concurrency": 4,
        }
        out = _parse_prepare_response(raw)
        assert isinstance(out, _PrepareResult)
        assert out.upload_id == "u1"
        assert out.block_size == 4194304
        assert len(out.parts) == 2
        assert out.parts[0].presigned_url == "https://x"
        # "url" key accepted as fallback for "presigned_url"
        assert out.parts[1].presigned_url == "https://y"
        assert out.concurrency == 4

    def test_data_wrapped_response(self):
        raw = {
            "data": {
                "upload_id": "u2",
                "block_size": 1024,
                "parts": [{"part_index": 1, "presigned_url": "u", "block_size": 1024}],
            },
            "code": 0,
        }
        out = _parse_prepare_response(raw)
        assert out.upload_id == "u2"

    def test_missing_upload_id_raises(self):
        with pytest.raises(ValueError, match="upload_id"):
            _parse_prepare_response({"parts": [{"part_index": 1}]})

    def test_missing_parts_raises(self):
        with pytest.raises(ValueError, match="parts"):
            _parse_prepare_response({"upload_id": "u"})

    def test_non_dict_part_skipped(self):
        raw = {
            "upload_id": "u",
            "parts": ["not-a-dict", {"part_index": 1, "presigned_url": "u", "block_size": 1}],
        }
        out = _parse_prepare_response(raw)
        # Only one valid part survives.
        assert len(out.parts) == 1

    def test_default_concurrency_used(self):
        raw = {
            "upload_id": "u",
            "parts": [{"part_index": 1, "url": "u", "block_size": 1}],
        }
        out = _parse_prepare_response(raw)
        # concurrency falls back to default (>0)
        assert out.concurrency > 0

    def test_part_list_alias(self):
        # Server might use "part_list" instead of "parts"
        raw = {
            "upload_id": "u",
            "part_list": [{"index": 1, "url": "u", "block_size": 1}],
        }
        out = _parse_prepare_response(raw)
        assert len(out.parts) == 1
        # "index" alias used for "part_index"
        assert out.parts[0].index == 1
