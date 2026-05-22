"""Coverage for ``plugins.example-dashboard.dashboard.plugin_api``.

Hyphenated package — load via importlib.util."""
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path


_PLUGIN_PATH = (
    Path(__file__).resolve().parents[2]
    / "plugins"
    / "example-dashboard"
    / "dashboard"
    / "plugin_api.py"
)


def _load():
    spec = importlib.util.spec_from_file_location(
        "example_dashboard_plugin", str(_PLUGIN_PATH)
    )
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


class TestExampleDashboardPlugin:
    def test_module_exports_a_fastapi_router(self):
        mod = _load()
        assert hasattr(mod, "router")
        assert mod.router.__class__.__name__ == "APIRouter"

    def test_hello_endpoint_returns_expected_payload(self):
        mod = _load()
        out = asyncio.run(mod.hello())
        assert out == {
            "message": "Hello from the example plugin!",
            "plugin": "example",
            "version": "1.0.0",
        }

    def test_route_is_registered_on_router(self):
        mod = _load()
        paths = {r.path for r in mod.router.routes}
        assert "/hello" in paths
