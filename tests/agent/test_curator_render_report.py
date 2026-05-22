"""Coverage for agent.curator._render_report_markdown."""
from __future__ import annotations

import pytest

from agent.curator import _render_report_markdown


def _make_report(**overrides):
    base = {
        "started_at": "2026-05-22T12:00:00",
        "duration_seconds": 95,
        "model": "claude-sonnet-4.6",
        "provider": "anthropic",
        "counts": {
            "before": 10, "after": 12, "delta": 2,
            "tool_calls_total": 5,
            "consolidated_this_run": 1,
            "pruned_this_run": 0,
            "added_this_run": 2,
            "state_transitions": 3,
        },
        "auto_transitions": {
            "checked": 100,
            "marked_stale": 5,
            "archived": 1,
            "reactivated": 0,
        },
        "tool_call_counts": {"consolidate": 2, "delete": 1},
        "consolidated": [],
    }
    base.update(overrides)
    return base


class TestRenderReportMarkdown:
    def test_basic_render(self):
        md = _render_report_markdown(_make_report())
        assert md.startswith("# Curator run — 2026-05-22T12:00:00")
        assert "anthropic" in md
        assert "claude-sonnet-4.6" in md
        assert "1m 35s" in md  # 95 seconds → "1m 35s"

    def test_duration_under_a_minute(self):
        md = _render_report_markdown(_make_report(duration_seconds=42))
        assert "42s" in md
        assert "0m 42s" not in md

    def test_delta_signed(self):
        # +/- prefix for delta
        report = _make_report(counts={
            "before": 10, "after": 12, "delta": 2,
            "tool_calls_total": 0, "consolidated_this_run": 0,
            "pruned_this_run": 0, "added_this_run": 0, "state_transitions": 0,
        })
        md = _render_report_markdown(report)
        assert "(+2)" in md

    def test_negative_delta(self):
        report = _make_report(counts={
            "before": 10, "after": 7, "delta": -3,
            "tool_calls_total": 0, "consolidated_this_run": 0,
            "pruned_this_run": 0, "added_this_run": 0, "state_transitions": 0,
        })
        md = _render_report_markdown(report)
        assert "(-3)" in md

    def test_llm_error_surfaced(self):
        md = _render_report_markdown(_make_report(llm_error="rate limit"))
        assert "LLM pass error" in md
        assert "rate limit" in md

    def test_no_model_provider_placeholders(self):
        md = _render_report_markdown(_make_report(model=None, provider=None))
        assert "(not resolved)" in md

    def test_auto_transitions_section(self):
        md = _render_report_markdown(_make_report())
        assert "## Auto-transitions" in md
        assert "checked: 100" in md
        assert "marked stale: 5" in md

    def test_tool_call_counts_listed(self):
        md = _render_report_markdown(_make_report())
        assert "consolidate=2" in md
        assert "delete=1" in md

    def test_no_tool_calls_says_none(self):
        md = _render_report_markdown(_make_report(tool_call_counts={}))
        assert "by name: none" in md

    def test_consolidated_section_present_when_non_empty(self):
        report = _make_report(consolidated=[
            {"name": "old-one", "destination": "umbrella"},
        ])
        md = _render_report_markdown(report)
        assert "Consolidated into umbrella skills" in md
