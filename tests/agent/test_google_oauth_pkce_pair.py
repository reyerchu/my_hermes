"""Coverage for the pure ``_generate_pkce_pair`` helper in
``agent.google_oauth``.  The function is invoked at the start of every
Gemini OAuth login flow — wrong derivation of the SHA-256 challenge is
indistinguishable from a server-side rejection."""
from __future__ import annotations

import base64
import hashlib

import pytest

from agent.google_oauth import _generate_pkce_pair


class TestGeneratePkcePair:
    def test_returns_tuple_of_two_strings(self):
        verifier, challenge = _generate_pkce_pair()
        assert isinstance(verifier, str) and verifier
        assert isinstance(challenge, str) and challenge

    def test_verifier_is_url_safe(self):
        # token_urlsafe() emits ascii-safe URL-encoded chars.
        verifier, _ = _generate_pkce_pair()
        for ch in verifier:
            assert ch.isalnum() or ch in {"-", "_"}

    def test_challenge_matches_s256_derivation(self):
        verifier, challenge = _generate_pkce_pair()
        # The challenge must be base64url(sha256(verifier)) with no
        # trailing "=" padding — the OAuth S256 spec.
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        assert challenge == expected

    def test_challenge_has_no_padding(self):
        _, challenge = _generate_pkce_pair()
        assert "=" not in challenge

    def test_each_call_returns_a_different_pair(self):
        v1, _ = _generate_pkce_pair()
        v2, _ = _generate_pkce_pair()
        assert v1 != v2

    def test_verifier_length_minimum_43_chars(self):
        # RFC 7636 §4.1: code_verifier must be 43–128 characters of
        # URL-safe characters.  token_urlsafe(64) produces ~86 chars.
        verifier, _ = _generate_pkce_pair()
        assert 43 <= len(verifier) <= 128
