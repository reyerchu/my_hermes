"""Coverage for the default SOUL.md template seeded on first run."""
from __future__ import annotations

from hermes_cli.default_soul import DEFAULT_SOUL_MD


class TestDefaultSoulMd:
    def test_is_a_non_empty_string(self):
        assert isinstance(DEFAULT_SOUL_MD, str)
        assert len(DEFAULT_SOUL_MD.strip()) > 0

    def test_mentions_hermes_agent_identity(self):
        assert "Hermes Agent" in DEFAULT_SOUL_MD

    def test_mentions_nous_research(self):
        assert "Nous Research" in DEFAULT_SOUL_MD

    def test_no_template_placeholders_left_in_text(self):
        # ${...} placeholders should be substituted before seeding.
        assert "${" not in DEFAULT_SOUL_MD

    def test_starts_with_role_statement(self):
        # The first sentence establishes the agent's identity.
        first_sentence = DEFAULT_SOUL_MD.split(".", 1)[0]
        assert "Hermes" in first_sentence
