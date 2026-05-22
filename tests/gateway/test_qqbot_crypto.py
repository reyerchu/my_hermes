"""Coverage for ``gateway.platforms.qqbot.crypto`` — the AES-256-GCM
key generator + secret decrypter used by QQBot scan-to-configure."""
from __future__ import annotations

import base64
import os

import pytest

from gateway.platforms.qqbot.crypto import decrypt_secret, generate_bind_key


class TestGenerateBindKey:
    def test_returns_base64_string(self):
        k = generate_bind_key()
        assert isinstance(k, str)
        # Decodes back to exactly 32 bytes (256-bit key).
        assert len(base64.b64decode(k)) == 32

    def test_each_call_returns_a_different_key(self):
        a = generate_bind_key()
        b = generate_bind_key()
        assert a != b


class TestDecryptSecret:
    def _encrypt(self, key_b64: str, plaintext: str) -> str:
        # Build a ciphertext matching the layout decrypt_secret expects:
        # IV (12) || ct || tag (16), then base64.
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key = base64.b64decode(key_b64)
        aes = AESGCM(key)
        iv = os.urandom(12)
        ct = aes.encrypt(iv, plaintext.encode("utf-8"), None)
        return base64.b64encode(iv + ct).decode()

    def test_round_trip(self):
        key = generate_bind_key()
        token = self._encrypt(key, "my-client-secret-123")
        assert decrypt_secret(token, key) == "my-client-secret-123"

    def test_unicode_secret_round_trip(self):
        key = generate_bind_key()
        token = self._encrypt(key, "🔐 秘密 شیر")
        assert decrypt_secret(token, key) == "🔐 秘密 شیر"

    def test_wrong_key_raises(self):
        key1 = generate_bind_key()
        key2 = generate_bind_key()
        token = self._encrypt(key1, "secret")
        with pytest.raises(Exception):
            decrypt_secret(token, key2)

    def test_corrupted_ciphertext_raises(self):
        key = generate_bind_key()
        token = self._encrypt(key, "secret")
        # Flip a bit in the middle of the base64 payload.
        raw = bytearray(base64.b64decode(token))
        raw[len(raw) // 2] ^= 0x01
        bad = base64.b64encode(bytes(raw)).decode()
        with pytest.raises(Exception):
            decrypt_secret(bad, key)
