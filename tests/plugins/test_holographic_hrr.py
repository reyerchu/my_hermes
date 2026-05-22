"""Coverage for plugins.memory.holographic.holographic — HRR phase
algebra primitives."""
from __future__ import annotations

import math

import pytest

np = pytest.importorskip("numpy")

from plugins.memory.holographic.holographic import (
    encode_atom,
    bind,
    unbind,
    bundle,
    similarity,
    encode_text,
    encode_fact,
    phases_to_bytes,
    bytes_to_phases,
    snr_estimate,
    _TWO_PI,
)


class TestEncodeAtom:
    def test_shape_default_dim(self):
        v = encode_atom("hello")
        assert v.shape == (1024,)
        assert v.dtype == np.float64

    def test_custom_dim(self):
        v = encode_atom("hello", dim=128)
        assert v.shape == (128,)

    def test_deterministic_across_calls(self):
        a = encode_atom("hello")
        b = encode_atom("hello")
        assert np.array_equal(a, b)

    def test_different_words_different_vectors(self):
        a = encode_atom("alpha")
        b = encode_atom("beta")
        assert not np.array_equal(a, b)

    def test_phases_in_two_pi_range(self):
        v = encode_atom("hi", dim=512)
        assert (v >= 0).all() and (v < _TWO_PI).all()


class TestBindUnbind:
    def test_bind_adds_phases_mod_two_pi(self):
        a = np.array([0.0, 1.0])
        b = np.array([0.5, 6.0])
        out = bind(a, b)
        expected = np.array([0.5, (1.0 + 6.0) % _TWO_PI])
        assert np.allclose(out, expected)

    def test_unbind_is_inverse_of_bind(self):
        a = encode_atom("subject")
        b = encode_atom("verb")
        bound = bind(a, b)
        recovered = unbind(bound, b)
        # Recovered should be exactly a (within float roundoff).
        # Compare via phase-cosine similarity.
        assert similarity(recovered, a) > 0.99

    def test_unbind_with_wrong_key_low_similarity(self):
        a = encode_atom("x")
        b = encode_atom("y")
        wrong = encode_atom("z")
        bound = bind(a, b)
        rec = unbind(bound, wrong)
        # Should be near-orthogonal (near 0 similarity).
        assert abs(similarity(rec, a)) < 0.2


class TestBundle:
    def test_bundle_phases_in_range(self):
        a = encode_atom("a", dim=64)
        b = encode_atom("b", dim=64)
        out = bundle(a, b)
        assert (out >= 0).all() and (out < _TWO_PI).all()

    def test_bundle_is_similar_to_inputs(self):
        a = encode_atom("a", dim=512)
        b = encode_atom("b", dim=512)
        c = encode_atom("c", dim=512)
        merged = bundle(a, b, c)
        # Merged should be similar to all three (positive similarity > unrelated).
        assert similarity(merged, a) > 0.3
        assert similarity(merged, b) > 0.3
        assert similarity(merged, c) > 0.3

    def test_bundle_single_returns_same_vector(self):
        a = encode_atom("only", dim=32)
        merged = bundle(a)
        # Single-input bundle should be (approximately) identical.
        assert similarity(merged, a) > 0.999


class TestSimilarity:
    def test_identical_vectors(self):
        a = encode_atom("x")
        assert similarity(a, a) == pytest.approx(1.0, abs=1e-10)

    def test_anti_phase_minus_one(self):
        a = np.zeros(32)
        b = np.full(32, math.pi)  # 180° offset
        assert similarity(a, b) == pytest.approx(-1.0, abs=1e-10)

    def test_quasi_orthogonal_words(self):
        a = encode_atom("apple")
        b = encode_atom("zebra")
        # Random pair should have small similarity.
        assert abs(similarity(a, b)) < 0.2


class TestEncodeText:
    def test_empty_returns_sentinel(self):
        v = encode_text("")
        # Should match the canonical empty atom.
        sentinel = encode_atom("__hrr_empty__")
        assert similarity(v, sentinel) > 0.999

    def test_only_punctuation_returns_sentinel(self):
        v = encode_text("?!,.")
        sentinel = encode_atom("__hrr_empty__")
        assert similarity(v, sentinel) > 0.999

    def test_lowercase_tokenization(self):
        a = encode_text("Hello World")
        b = encode_text("hello world")
        assert similarity(a, b) > 0.999

    def test_punctuation_stripped(self):
        a = encode_text("hello, world!")
        b = encode_text("hello world")
        assert similarity(a, b) > 0.999

    def test_token_order_independent(self):
        # Bundle is commutative.
        a = encode_text("one two three")
        b = encode_text("three two one")
        assert similarity(a, b) > 0.999


class TestEncodeFact:
    def test_round_trip_via_unbind(self):
        # Fact: content="paris is sunny", entity="paris"
        content = "paris is sunny"
        fact = encode_fact(content, ["paris"], dim=512)
        role_content = encode_atom("__hrr_role_content__", dim=512)
        rec = unbind(fact, role_content)
        # Recovered should resemble the bundle of content tokens.
        text_v = encode_text(content, dim=512)
        # Imperfect recovery is expected (bundle noise) — require a small
        # positive similarity rather than 1.0.
        assert similarity(rec, text_v) > 0.05


class TestSerialization:
    def test_round_trip(self):
        v = encode_atom("hi", dim=64)
        ser = phases_to_bytes(v)
        out = bytes_to_phases(ser)
        assert np.array_equal(v, out)

    def test_size_dim_times_8(self):
        # float64 = 8 bytes
        v = encode_atom("x", dim=128)
        assert len(phases_to_bytes(v)) == 128 * 8

    def test_result_is_writable(self):
        v = encode_atom("x", dim=64)
        out = bytes_to_phases(phases_to_bytes(v))
        # Must be a copy (writable), not a frombuffer read-only view.
        out[0] = 0.0


class TestSnrEstimate:
    def test_zero_items_is_inf(self):
        assert snr_estimate(1024, 0) == float("inf")

    def test_negative_items_is_inf(self):
        # Per code: <= 0 returns inf.
        assert snr_estimate(1024, -1) == float("inf")

    def test_dim_over_items_sqrt(self):
        # SNR = sqrt(dim / n_items)
        assert snr_estimate(1024, 16) == pytest.approx(math.sqrt(64), rel=1e-6)

    def test_low_snr_triggers_warning(self, caplog):
        # SNR < 2.0 when n_items > dim/4 → emits a warning log.
        with caplog.at_level("WARNING"):
            snr_estimate(16, 100)
        assert any("near capacity" in r.message for r in caplog.records)
