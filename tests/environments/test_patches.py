"""Coverage for ``environments.patches.apply_patches``.

The module is intentionally a no-op now but still exposed publicly for
backwards compatibility, so the contract worth pinning is: idempotent
and safe to call multiple times in any order."""
from __future__ import annotations

import environments.patches as patches


def test_apply_patches_returns_none_and_is_idempotent():
    # Reset module state for a clean test.
    patches._patches_applied = False
    assert patches.apply_patches() is None
    assert patches._patches_applied is True
    # Second call must be a no-op (doesn't raise, flag stays true).
    assert patches.apply_patches() is None
    assert patches._patches_applied is True


def test_repeated_calls_dont_throw():
    patches._patches_applied = False
    for _ in range(10):
        patches.apply_patches()
    assert patches._patches_applied is True


def test_module_logger_attached_under_environments_namespace():
    # Cheap sanity check that the module hasn't accidentally lost its
    # logger, which the import-time `apply_patches()` call uses.
    assert patches.logger.name == "environments.patches"
