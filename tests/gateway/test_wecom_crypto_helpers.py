"""Coverage for the pure helpers in ``gateway.platforms.wecom_crypto``.

The full WXBizMsgCrypt class needs a 32-byte EncodingAESKey to test
round-trip; we cover the smaller pure surfaces (PKCS7 encoder/decoder,
SHA1 signature, exception hierarchy) which are the load-bearing units."""
from __future__ import annotations

import hashlib

import pytest

from gateway.platforms.wecom_crypto import (
    DecryptError,
    EncryptError,
    PKCS7Encoder,
    SignatureError,
    WeComCryptoError,
    _sha1_signature,
)


class TestPKCS7Encoder:
    def test_block_size_is_32(self):
        assert PKCS7Encoder.block_size == 32

    def test_encode_pads_to_next_multiple(self):
        text = b"abcdef"  # 6 bytes; pad to 32
        out = PKCS7Encoder.encode(text)
        assert len(out) == 32
        # The pad byte equals the padding length.
        assert out[-1] == 32 - 6
        # Every padding byte is the same.
        assert out[6:] == bytes([26]) * 26

    def test_encode_pads_full_block_when_already_aligned(self):
        text = b"a" * 32
        out = PKCS7Encoder.encode(text)
        # A full block of padding is appended (BizMsgCrypt spec).
        assert len(out) == 64
        assert out[-1] == 32

    def test_decode_strips_pkcs7_padding(self):
        text = b"hello"
        encoded = PKCS7Encoder.encode(text)
        assert PKCS7Encoder.decode(encoded) == text

    def test_decode_round_trip_for_arbitrary_lengths(self):
        for length in (0, 1, 15, 31, 32, 33, 64, 100):
            text = b"x" * length
            assert PKCS7Encoder.decode(PKCS7Encoder.encode(text)) == text

    def test_decode_empty_payload_raises(self):
        with pytest.raises(DecryptError):
            PKCS7Encoder.decode(b"")

    def test_decode_invalid_pad_byte_raises(self):
        # A pad byte of 0 or > block_size is invalid.
        with pytest.raises(DecryptError):
            PKCS7Encoder.decode(b"x" * 31 + bytes([0]))
        with pytest.raises(DecryptError):
            PKCS7Encoder.decode(b"x" * 31 + bytes([33]))

    def test_decode_inconsistent_padding_raises(self):
        # Last byte says "3 bytes of padding" but the 3 trailing bytes
        # aren't all 0x03.
        bad = b"x" * 29 + bytes([1, 2, 3])
        with pytest.raises(DecryptError):
            PKCS7Encoder.decode(bad)


class TestSha1Signature:
    def test_sorted_concat_sha1_matches_manual_computation(self):
        sig = _sha1_signature("tok", "1700000000", "nonce", "encrypted")
        expected = hashlib.sha1(
            "".join(sorted(["tok", "1700000000", "nonce", "encrypted"]))
            .encode("utf-8")
        ).hexdigest()
        assert sig == expected

    def test_order_of_arguments_does_not_matter(self):
        # The implementation sorts inputs before concatenating, so any
        # argument permutation yields the same signature.
        a = _sha1_signature("a", "b", "c", "d")
        b = _sha1_signature("d", "c", "b", "a")
        c = _sha1_signature("c", "a", "d", "b")
        assert a == b == c

    def test_distinct_inputs_produce_distinct_signatures(self):
        sig1 = _sha1_signature("tok", "1", "n", "e1")
        sig2 = _sha1_signature("tok", "1", "n", "e2")
        assert sig1 != sig2


class TestExceptionHierarchy:
    def test_signature_error_inherits_base(self):
        assert issubclass(SignatureError, WeComCryptoError)

    def test_decrypt_error_inherits_base(self):
        assert issubclass(DecryptError, WeComCryptoError)

    def test_encrypt_error_inherits_base(self):
        assert issubclass(EncryptError, WeComCryptoError)

    def test_base_is_a_real_exception(self):
        assert issubclass(WeComCryptoError, Exception)
