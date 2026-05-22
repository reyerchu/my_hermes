"""Extended coverage for plugins.google_meet.audio_bridge.AudioBridge
(complements existing test_google_meet_audio_bridge.py which covers
just the chrome_fake_audio_flags helper)."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from plugins.google_meet.audio_bridge import (
    AudioBridge,
    _BLACKHOLE_DEVICE,
)


class TestParseModuleId:
    def test_simple_int(self):
        assert AudioBridge._parse_module_id("42\n") == 42

    def test_token_after_whitespace(self):
        assert AudioBridge._parse_module_id("Module loaded: 17") == 17

    def test_empty_raises(self):
        with pytest.raises(RuntimeError, match="empty stdout"):
            AudioBridge._parse_module_id("")
        with pytest.raises(RuntimeError, match="empty stdout"):
            AudioBridge._parse_module_id("   \n   ")

    def test_non_numeric_raises(self):
        with pytest.raises(RuntimeError, match="could not parse"):
            AudioBridge._parse_module_id("not-a-number")


class TestProperties:
    def test_unset_device_name_raises(self):
        b = AudioBridge()
        with pytest.raises(RuntimeError, match="not set up"):
            _ = b.device_name

    def test_unset_write_target_raises(self):
        b = AudioBridge()
        with pytest.raises(RuntimeError, match="not set up"):
            _ = b.write_target


class TestSetupDispatch:
    def test_windows_raises(self):
        b = AudioBridge()
        with patch("plugins.google_meet.audio_bridge.platform.system", return_value="Windows"):
            with pytest.raises(RuntimeError, match="windows"):
                b.setup()

    def test_unknown_raises(self):
        b = AudioBridge()
        with patch("plugins.google_meet.audio_bridge.platform.system", return_value="BeOS"):
            with pytest.raises(RuntimeError, match="unsupported platform"):
                b.setup()

    def test_linux_dispatch(self):
        b = AudioBridge()
        with patch("plugins.google_meet.audio_bridge.platform.system", return_value="Linux"):
            with patch.object(b, "_setup_linux", return_value={"platform": "linux"}) as l:
                out = b.setup()
        l.assert_called_once()
        assert out["platform"] == "linux"

    def test_darwin_dispatch(self):
        b = AudioBridge()
        with patch("plugins.google_meet.audio_bridge.platform.system", return_value="Darwin"):
            with patch.object(b, "_setup_darwin", return_value={"platform": "darwin"}) as d:
                out = b.setup()
        d.assert_called_once()
        assert out["platform"] == "darwin"


class TestLinuxSetup:
    def test_happy_path(self, monkeypatch):
        results = iter([MagicMock(stdout="100\n"), MagicMock(stdout="101\n")])
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: next(results))
        b = AudioBridge(name_prefix="t")
        info = b._setup_linux()
        assert info["platform"] == "linux"
        assert info["device_name"] == "t_src"
        assert info["write_target"] == "t_sink"
        assert info["module_ids"] == [100, 101]
        assert info["sample_rate"] == 48000
        assert info["channels"] == 2

    def test_missing_pactl(self, monkeypatch):
        def _run(*a, **kw):
            raise FileNotFoundError("pactl")
        monkeypatch.setattr(subprocess, "run", _run)
        b = AudioBridge()
        with pytest.raises(RuntimeError, match="pactl not found"):
            b._setup_linux()

    def test_null_sink_failure(self, monkeypatch):
        exc = subprocess.CalledProcessError(1, "pactl")
        exc.stderr = "denied"
        def _run(*a, **kw):
            raise exc
        monkeypatch.setattr(subprocess, "run", _run)
        b = AudioBridge()
        with pytest.raises(RuntimeError, match="null-sink failed"):
            b._setup_linux()

    def test_virtual_source_failure_rolls_back(self, monkeypatch):
        exc = subprocess.CalledProcessError(1, "pactl")
        exc.stderr = "vsrc broke"
        calls = []
        def _run(argv, *a, **kw):
            calls.append(argv)
            if len(calls) == 1:
                return MagicMock(stdout="100\n")
            if len(calls) == 2:
                raise exc
            return MagicMock(stdout="", returncode=0)
        monkeypatch.setattr(subprocess, "run", _run)
        b = AudioBridge()
        with pytest.raises(RuntimeError, match="virtual-source failed"):
            b._setup_linux()
        # Verify rollback unload was attempted.
        assert any("unload-module" in arg for call in calls for arg in call)


class TestDarwinSetup:
    def test_blackhole_present(self, monkeypatch):
        monkeypatch.setattr(
            subprocess, "check_output",
            lambda *a, **kw: "Devices: BlackHole 2ch, MacBook Pro Microphone",
        )
        b = AudioBridge()
        info = b._setup_darwin()
        assert info["platform"] == "darwin"
        assert info["device_name"] == _BLACKHOLE_DEVICE
        assert info["write_target"] == _BLACKHOLE_DEVICE
        assert info["module_ids"] == []

    def test_missing_system_profiler(self, monkeypatch):
        def _co(*a, **kw):
            raise FileNotFoundError("system_profiler")
        monkeypatch.setattr(subprocess, "check_output", _co)
        b = AudioBridge()
        with pytest.raises(RuntimeError, match="system_profiler not found"):
            b._setup_darwin()

    def test_blackhole_missing(self, monkeypatch):
        monkeypatch.setattr(
            subprocess, "check_output",
            lambda *a, **kw: "Devices: builtin only",
        )
        b = AudioBridge()
        with pytest.raises(RuntimeError, match="BlackHole.*not installed"):
            b._setup_darwin()


class TestTeardown:
    def test_idempotent_before_setup(self):
        b = AudioBridge()
        b.teardown()
        b.teardown()

    def test_linux_unloads_in_reverse_order(self, monkeypatch):
        b = AudioBridge()
        b._platform = "linux"
        b._module_ids = [100, 101]
        calls = []
        monkeypatch.setattr(subprocess, "run", lambda argv, *a, **kw: calls.append(argv) or MagicMock())
        b.teardown()
        assert len(calls) == 2
        # Reverse order: 101 first, then 100.
        assert "101" in calls[0]
        assert "100" in calls[1]
        assert b._torn_down is True
        assert b._module_ids == []

    def test_teardown_swallows_unload_exception(self, monkeypatch):
        b = AudioBridge()
        b._platform = "linux"
        b._module_ids = [100]
        def _run(*a, **kw):
            raise RuntimeError("unload boom")
        monkeypatch.setattr(subprocess, "run", _run)
        # Should not propagate the exception.
        b.teardown()
        assert b._torn_down is True
