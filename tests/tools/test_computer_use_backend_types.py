"""Coverage for the dataclasses in tools.computer_use.backend."""
from __future__ import annotations

import pytest

from tools.computer_use.backend import (
    UIElement,
    CaptureResult,
    ActionResult,
    ComputerUseBackend,
)


class TestUIElement:
    def test_defaults(self):
        e = UIElement(index=1, role="AXButton")
        assert e.label == ""
        assert e.bounds == (0, 0, 0, 0)
        assert e.app == ""
        assert e.pid == 0
        assert e.window_id == 0
        assert e.attributes == {}

    def test_center_basic(self):
        e = UIElement(index=1, role="AXButton", bounds=(10, 20, 100, 50))
        assert e.center() == (10 + 50, 20 + 25)  # (60, 45)

    def test_center_zero_bounds(self):
        e = UIElement(index=1, role="AXButton")
        assert e.center() == (0, 0)


class TestCaptureResult:
    def test_basic_construction(self):
        c = CaptureResult(mode="som", width=1024, height=768)
        assert c.mode == "som"
        assert c.width == 1024
        assert c.height == 768
        assert c.png_b64 is None
        assert c.elements == []

    def test_optional_fields(self):
        e1 = UIElement(index=1, role="AXButton")
        c = CaptureResult(
            mode="ax",
            width=10, height=10,
            elements=[e1],
            app="TestApp",
            window_title="Foo",
        )
        assert c.elements == [e1]
        assert c.app == "TestApp"
        assert c.window_title == "Foo"


class TestActionResult:
    def test_basic(self):
        a = ActionResult(ok=True, action="click")
        assert a.ok is True
        assert a.action == "click"
        assert a.message == ""
        assert a.capture is None
        assert a.meta == {}

    def test_with_capture(self):
        cap = CaptureResult(mode="som", width=10, height=10)
        a = ActionResult(ok=False, action="type", message="x", capture=cap)
        assert a.capture is cap

    def test_meta_dict(self):
        a = ActionResult(ok=True, action="x", meta={"foo": 1})
        assert a.meta == {"foo": 1}


class TestComputerUseBackendABC:
    def test_abstract_methods(self):
        # Cannot instantiate directly.
        with pytest.raises(TypeError):
            ComputerUseBackend()  # type: ignore[abstract]

    def test_required_methods_declared(self):
        for name in ("start", "stop", "is_available", "capture"):
            attr = getattr(ComputerUseBackend, name)
            assert getattr(attr, "__isabstractmethod__", False)
