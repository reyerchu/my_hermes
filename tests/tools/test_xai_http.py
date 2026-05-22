"""Coverage for ``tools.xai_http.hermes_xai_user_agent``."""
from __future__ import annotations

import sys

from tools.xai_http import hermes_xai_user_agent


class TestHermesXaiUserAgent:
    def test_starts_with_hermes_agent_prefix(self):
        ua = hermes_xai_user_agent()
        assert ua.startswith("Hermes-Agent/")

    def test_includes_version_or_unknown_fallback(self):
        ua = hermes_xai_user_agent()
        # Either a real version (digits dot digits ...) or the literal
        # "unknown" sentinel.  Don't pin the exact version.
        version = ua.split("/", 1)[1]
        assert version
        assert version == "unknown" or any(c.isalnum() for c in version)

    def test_falls_back_to_unknown_when_hermes_cli_import_fails(self, monkeypatch):
        # Force the hermes_cli import inside the helper to fail.  Remove
        # the cached module entry and stub the loader.
        monkeypatch.delitem(sys.modules, "hermes_cli", raising=False)
        # Insert a faux meta path entry that raises for hermes_cli.
        class _FailFinder:
            def find_spec(self, fullname, *_a, **_k):
                if fullname == "hermes_cli":
                    raise ImportError("simulated")
                return None
        monkeypatch.setattr(sys, "meta_path", [_FailFinder(), *sys.meta_path])
        ua = hermes_xai_user_agent()
        assert ua == "Hermes-Agent/unknown"
