"""Coverage for the pure helpers in ``gateway.platforms.qqbot.onboard``:
BindStatus enum + build_connect_url."""
from __future__ import annotations

from gateway.platforms.qqbot.onboard import BindStatus, build_connect_url


class TestBindStatus:
    def test_enum_values_are_stable(self):
        assert int(BindStatus.NONE) == 0
        assert int(BindStatus.PENDING) == 1
        assert int(BindStatus.COMPLETED) == 2
        assert int(BindStatus.EXPIRED) == 3

    def test_enum_round_trip(self):
        for member in BindStatus:
            assert BindStatus(int(member)) is member


class TestBuildConnectUrl:
    def test_substitutes_task_id(self):
        url = build_connect_url("task-12345")
        assert "task_id=task-12345" in url

    def test_url_quotes_spaces_but_not_slashes_by_default(self):
        # urllib.parse.quote() with default safe="/" leaves slashes alone
        # but percent-encodes other special chars like spaces.
        url = build_connect_url("a/b c")
        assert "%20" in url  # the space
        assert "a/b" in url

    def test_url_carries_hermes_source_marker(self):
        url = build_connect_url("t1")
        assert "source=hermes" in url

    def test_url_starts_with_q_qq_com_host(self):
        url = build_connect_url("t1")
        assert url.startswith("https://q.qq.com/qqbot")

    def test_empty_task_id_still_renders(self):
        url = build_connect_url("")
        # Empty task_id is allowed by the formatter; QR rendering will
        # surface the failure on the next layer.
        assert "task_id=" in url
