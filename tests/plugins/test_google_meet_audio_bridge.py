"""Coverage for ``plugins.google_meet.audio_bridge.chrome_fake_audio_flags``."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from plugins.google_meet.audio_bridge import chrome_fake_audio_flags


class TestChromeFakeAudioFlags:
    def test_linux_returns_fake_ui_flag(self):
        with patch(
            "plugins.google_meet.audio_bridge.platform.system",
            return_value="Linux",
        ):
            flags = chrome_fake_audio_flags({"device_name": "fake-source"})
        assert "--use-fake-ui-for-media-stream" in flags

    def test_macos_returns_fake_ui_flag(self):
        with patch(
            "plugins.google_meet.audio_bridge.platform.system",
            return_value="Darwin",
        ):
            flags = chrome_fake_audio_flags({"device_name": "BlackHole 2ch"})
        assert "--use-fake-ui-for-media-stream" in flags

    def test_windows_raises(self):
        with patch(
            "plugins.google_meet.audio_bridge.platform.system",
            return_value="Windows",
        ):
            with pytest.raises(RuntimeError, match="windows"):
                chrome_fake_audio_flags({})

    def test_returns_list_of_strings(self):
        with patch(
            "plugins.google_meet.audio_bridge.platform.system",
            return_value="Linux",
        ):
            flags = chrome_fake_audio_flags({})
        assert isinstance(flags, list)
        for flag in flags:
            assert isinstance(flag, str)
            assert flag.startswith("--")
