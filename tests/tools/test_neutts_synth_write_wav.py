"""Coverage for ``tools.neutts_synth._write_wav`` — the standalone WAV
encoder that ships independent of soundfile."""
from __future__ import annotations

import struct
from pathlib import Path

import pytest


def _import_module():
    # Defer the import so missing numpy on a test runner is a clean skip
    # rather than a collection error.
    pytest.importorskip("numpy")
    import importlib
    return importlib.import_module("tools.neutts_synth")


class TestWriteWav:
    def test_creates_file_at_path(self, tmp_path: Path):
        ns = _import_module()
        out = tmp_path / "a.wav"
        ns._write_wav(str(out), [0.0, 0.5, -0.5, 0.0], sample_rate=8000)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_riff_wave_header_present(self, tmp_path: Path):
        ns = _import_module()
        out = tmp_path / "a.wav"
        ns._write_wav(str(out), [0.0] * 8, sample_rate=16000)
        data = out.read_bytes()
        assert data[:4] == b"RIFF"
        assert data[8:12] == b"WAVE"
        assert data[12:16] == b"fmt "

    def test_sample_rate_embedded_in_header(self, tmp_path: Path):
        ns = _import_module()
        out = tmp_path / "a.wav"
        ns._write_wav(str(out), [0.0] * 4, sample_rate=22050)
        data = out.read_bytes()
        # fmt chunk starts at byte 12; sample rate is little-endian uint32
        # at offset 24.
        rate = struct.unpack("<I", data[24:28])[0]
        assert rate == 22050

    def test_clamps_out_of_range_samples(self, tmp_path: Path):
        ns = _import_module()
        out = tmp_path / "a.wav"
        # Out-of-range values get clamped to ±1.0 then quantised to int16.
        ns._write_wav(str(out), [2.0, -2.0, 0.0], sample_rate=8000)
        data = out.read_bytes()
        # The encoded PCM starts after the 44-byte header.
        pcm = data[44:]
        # First sample is 32767 (+1.0 quantised), second is -32767.
        first = struct.unpack("<h", pcm[0:2])[0]
        second = struct.unpack("<h", pcm[2:4])[0]
        assert first == 32767
        assert second == -32767

    def test_accepts_numpy_array_input(self, tmp_path: Path):
        ns = _import_module()
        import numpy as np
        out = tmp_path / "a.wav"
        ns._write_wav(str(out), np.array([0.0, 0.5], dtype=np.float32), 16000)
        assert out.exists()
