"""Coverage for ``gateway.whatsapp_identity``.

The two helpers (``normalize_whatsapp_identifier`` +
``canonical_whatsapp_identifier``) gate WhatsApp authorisation and
session-key derivation.  A bug here means the same human is treated as
two different senders — which would break per-user allowlists and
allow phone/LID variants to dodge a block.  No existing direct tests.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from gateway.whatsapp_identity import (
    canonical_whatsapp_identifier,
    expand_whatsapp_aliases,
    normalize_whatsapp_identifier,
)


class TestNormalizeWhatsappIdentifier:
    def test_empty_input_returns_empty_string(self):
        assert normalize_whatsapp_identifier("") == ""
        assert normalize_whatsapp_identifier(None) == ""  # type: ignore[arg-type]

    def test_strips_leading_plus_only_once(self):
        assert normalize_whatsapp_identifier("+60123456789") == "60123456789"

    def test_strips_phone_jid_suffix(self):
        assert (
            normalize_whatsapp_identifier("60123456789@s.whatsapp.net")
            == "60123456789"
        )

    def test_strips_lid_suffix(self):
        assert normalize_whatsapp_identifier("999999999999999@lid") == (
            "999999999999999"
        )

    def test_strips_device_suffix_before_at(self):
        # 60123456789:47@s.whatsapp.net → 60123456789
        assert (
            normalize_whatsapp_identifier("60123456789:47@s.whatsapp.net")
            == "60123456789"
        )

    def test_bare_numeric_passthrough(self):
        assert normalize_whatsapp_identifier("60123456789") == "60123456789"

    def test_strips_surrounding_whitespace(self):
        assert (
            normalize_whatsapp_identifier("  60123456789@lid  ")
            == "60123456789"
        )


class TestExpandWhatsappAliases:
    def test_empty_input_returns_empty_set(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        assert expand_whatsapp_aliases("") == set()

    def test_no_mapping_files_returns_just_self(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        assert expand_whatsapp_aliases("60123456789") == {"60123456789"}

    def test_resolves_through_mapping_file(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        sess = tmp_path / "whatsapp" / "session"
        sess.mkdir(parents=True)
        # Phone → LID via lid-mapping-<phone>.json
        (sess / "lid-mapping-60123456789.json").write_text(
            json.dumps("999999999999999@lid"),
            encoding="utf-8",
        )
        aliases = expand_whatsapp_aliases("60123456789")
        assert "60123456789" in aliases
        assert "999999999999999" in aliases

    def test_resolves_transitively(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        sess = tmp_path / "whatsapp" / "session"
        sess.mkdir(parents=True)
        (sess / "lid-mapping-A.json").write_text(json.dumps("B"))
        (sess / "lid-mapping-B.json").write_text(json.dumps("C"))
        aliases = expand_whatsapp_aliases("A")
        assert aliases == {"A", "B", "C"}

    def test_rejects_traversal_in_identifier(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        sess = tmp_path / "whatsapp" / "session"
        sess.mkdir(parents=True)
        (sess / "lid-mapping-..-secret.json").write_text(json.dumps("X"))
        # Identifier with traversal characters skipped by the safe-regex.
        aliases = expand_whatsapp_aliases("../secret")
        # Normalisation leaves "../secret" mostly intact, then the regex
        # rejects it.  Either way, the returned set is empty or contains
        # only the normalized self — but no expanded "X".
        assert "X" not in aliases

    def test_malformed_json_is_swallowed(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        sess = tmp_path / "whatsapp" / "session"
        sess.mkdir(parents=True)
        (sess / "lid-mapping-A.json").write_text("not json{")
        # Helper logs + skips bad files; the unaliased self still comes back.
        aliases = expand_whatsapp_aliases("A")
        assert aliases == {"A"}


class TestCanonicalWhatsappIdentifier:
    def test_empty_input_returns_empty_string(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        assert canonical_whatsapp_identifier("") == ""

    def test_no_mapping_returns_normalized_input(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        assert (
            canonical_whatsapp_identifier("+60123456789@s.whatsapp.net")
            == "60123456789"
        )

    def test_picks_shortest_alias_when_multiple_exist(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        sess = tmp_path / "whatsapp" / "session"
        sess.mkdir(parents=True)
        # Phone (shorter) ←→ LID (longer)
        (sess / "lid-mapping-999999999999999.json").write_text(
            json.dumps("60123456789")
        )
        (sess / "lid-mapping-60123456789.json").write_text(
            json.dumps("999999999999999")
        )
        # Either entry point picks the same shortest canonical.
        assert canonical_whatsapp_identifier("999999999999999") == (
            "60123456789"
        )
        assert canonical_whatsapp_identifier("60123456789") == (
            "60123456789"
        )

    def test_tie_break_lexicographic(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        sess = tmp_path / "whatsapp" / "session"
        sess.mkdir(parents=True)
        # Two same-length aliases — min() falls back to string order.
        (sess / "lid-mapping-A1.json").write_text(json.dumps("B2"))
        (sess / "lid-mapping-B2.json").write_text(json.dumps("A1"))
        assert canonical_whatsapp_identifier("A1") == "A1"
