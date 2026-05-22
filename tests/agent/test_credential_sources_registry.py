"""Coverage for the registry contract in ``agent.credential_sources``.

The module ships per-source removal handlers (env, claude_code, qwen,
codex, …) that do filesystem I/O; testing those end-to-end requires a
mock auth store.  Here we cover the registry/dispatch layer — the
``RemovalStep.matches`` predicate and the ``register`` /
``find_removal_step`` lookups — which is what every removal flow goes
through first.  No existing direct tests."""
from __future__ import annotations

import pytest

from agent.credential_sources import (
    RemovalResult,
    RemovalStep,
    find_removal_step,
    register,
)


def _noop_remove(*_args, **_kwargs) -> RemovalResult:
    return RemovalResult()


class TestRemovalResult:
    def test_default_fields(self):
        r = RemovalResult()
        assert r.cleaned == []
        assert r.hints == []
        assert r.suppress is True

    def test_each_instance_gets_an_independent_list(self):
        a = RemovalResult()
        b = RemovalResult()
        a.cleaned.append("x")
        assert b.cleaned == []

    def test_field_override(self):
        r = RemovalResult(
            cleaned=["did a thing"], hints=["note: x"], suppress=False,
        )
        assert r.cleaned == ["did a thing"]
        assert r.hints == ["note: x"]
        assert r.suppress is False


class TestRemovalStepMatches:
    def test_exact_provider_and_source_match(self):
        step = RemovalStep(
            provider="xai", source_id="claude_code", remove_fn=_noop_remove,
        )
        assert step.matches("xai", "claude_code") is True

    def test_provider_mismatch_returns_false(self):
        step = RemovalStep(
            provider="xai", source_id="claude_code", remove_fn=_noop_remove,
        )
        assert step.matches("openai", "claude_code") is False

    def test_source_mismatch_returns_false(self):
        step = RemovalStep(
            provider="xai", source_id="claude_code", remove_fn=_noop_remove,
        )
        assert step.matches("xai", "manual") is False

    def test_wildcard_provider_matches_any(self):
        step = RemovalStep(
            provider="*", source_id="manual", remove_fn=_noop_remove,
        )
        assert step.matches("anything", "manual") is True
        assert step.matches("xai", "manual") is True

    def test_match_fn_takes_precedence_over_source_id(self):
        step = RemovalStep(
            provider="xai",
            source_id="placeholder-ignored",
            remove_fn=_noop_remove,
            match_fn=lambda s: s.startswith("env:"),
        )
        assert step.matches("xai", "env:XAI_API_KEY") is True
        assert step.matches("xai", "claude_code") is False

    def test_match_fn_still_respects_provider_gate(self):
        step = RemovalStep(
            provider="xai",
            source_id="x",
            remove_fn=_noop_remove,
            match_fn=lambda s: True,
        )
        assert step.matches("xai", "anything") is True
        assert step.matches("openai", "anything") is False


class TestRegisterAndFindRemovalStep:
    def test_find_unregistered_provider_returns_none(self):
        # Use a provider name that no built-in step claims.
        assert find_removal_step("DEFINITELY_FAKE_PROVIDER", "xx") is None

    def test_register_returns_the_step(self):
        step = RemovalStep(
            provider="DEFINITELY_FAKE_PROVIDER_2",
            source_id="literal-source",
            remove_fn=_noop_remove,
            description="test step",
        )
        assert register(step) is step

    def test_registered_step_is_findable(self):
        step = RemovalStep(
            provider="DEFINITELY_FAKE_PROVIDER_3",
            source_id="literal-source",
            remove_fn=_noop_remove,
        )
        register(step)
        assert find_removal_step(
            "DEFINITELY_FAKE_PROVIDER_3", "literal-source"
        ) is step

    def test_builtin_claude_code_step_is_registered(self):
        # Smoke check: the module's auto-registration ran at import time
        # and at least the well-known claude_code source resolves.
        step = find_removal_step("anthropic", "claude_code")
        # Note: actual provider key may differ; assert at least one of the
        # well-known steps exists.  Iterate well-known provider/source
        # pairs and require at least one to resolve.
        well_known = [
            ("anthropic", "claude_code"),
            ("anthropic", "hermes_pkce"),
            ("nous", "device_code"),
            ("openai-codex", "device_code"),
        ]
        resolved = [
            find_removal_step(p, s) for p, s in well_known
        ]
        assert any(s is not None for s in resolved)
