"""Coverage for pure helpers in plugins.hermes-achievements.dashboard.plugin_api.

Loaded via importlib.util because the package name "hermes-achievements"
contains a hyphen."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_MOD_PATH = (
    _REPO_ROOT / "plugins" / "hermes-achievements" / "dashboard" / "plugin_api.py"
)


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "hermes_achievements_api", _MOD_PATH
    )
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
    except Exception as e:
        pytest.skip(f"could not load module: {e}")
    return m


class TestTierAndReq:
    def test_tiers_basic(self, mod):
        out = mod.tiers([10, 20, 30, 40, 50])
        # Implementation iterates TIER_NAMES; should yield 5 dicts.
        assert len(out) == 5
        # All have name + threshold.
        for entry in out:
            assert "name" in entry
            assert "threshold" in entry

    def test_tiers_names_match_module_constant(self, mod):
        out = mod.tiers([1, 2, 3, 4, 5])
        assert [t["name"] for t in out] == mod.TIER_NAMES

    def test_tiers_thresholds_preserved(self, mod):
        out = mod.tiers([10, 20, 30, 40, 50])
        assert [t["threshold"] for t in out] == [10, 20, 30, 40, 50]

    def test_tiers_short_values_zip_truncates(self, mod):
        # zip stops at shorter — only as many tiers as values given.
        out = mod.tiers([1, 2])
        assert len(out) == 2

    def test_req(self, mod):
        out = mod.req("metric_x", 5)
        assert out == {"metric": "metric_x", "gte": 5}


class TestJsonSafe:
    def test_dict(self, mod):
        out = mod._json_safe({"a": 1})
        assert out == {"a": 1}

    def test_list_passthrough(self, mod):
        out = mod._json_safe([1, 2, 3])
        assert out == [1, 2, 3]

    def test_tuple_to_list(self, mod):
        out = mod._json_safe((1, 2))
        assert out == [1, 2]

    def test_set_to_sorted_list(self, mod):
        out = mod._json_safe({3, 1, 2})
        assert out == [1, 2, 3]

    def test_nested(self, mod):
        out = mod._json_safe({"a": (1, 2), "b": {4, 5}})
        # Nested tuple becomes list; nested set becomes sorted list.
        assert out["a"] == [1, 2]
        assert out["b"] == [4, 5]

    def test_scalar_passthrough(self, mod):
        assert mod._json_safe(42) == 42
        assert mod._json_safe("hi") == "hi"
        assert mod._json_safe(None) is None
        assert mod._json_safe(True) is True


class TestAchievementsCatalog:
    def test_module_has_achievements(self, mod):
        assert isinstance(mod.ACHIEVEMENTS, list)
        assert len(mod.ACHIEVEMENTS) > 0

    def test_every_entry_has_id_and_tiers_or_requirements(self, mod):
        for entry in mod.ACHIEVEMENTS:
            assert "id" in entry
            # Multi-condition entries have requirements; others have tiers.
            assert "tiers" in entry or "requirements" in entry

    def test_ids_are_unique(self, mod):
        ids = [e["id"] for e in mod.ACHIEVEMENTS]
        assert len(set(ids)) == len(ids)


class TestTierNames:
    def test_pinned(self, mod):
        assert mod.TIER_NAMES == ["Copper", "Silver", "Gold", "Diamond", "Olympian"]
