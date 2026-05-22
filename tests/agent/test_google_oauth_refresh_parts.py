"""Coverage for the ``RefreshParts`` packing/parsing in
``agent.google_oauth``."""
from __future__ import annotations

import pytest

from agent.google_oauth import GoogleCredentials, RefreshParts


class TestRefreshPartsParse:
    def test_empty_string_returns_empty_token(self):
        parts = RefreshParts.parse("")
        assert parts.refresh_token == ""
        assert parts.project_id == ""
        assert parts.managed_project_id == ""

    def test_bare_token_no_project_ids(self):
        parts = RefreshParts.parse("rt-abc")
        assert parts.refresh_token == "rt-abc"
        assert parts.project_id == ""

    def test_token_with_project_only(self):
        parts = RefreshParts.parse("rt|proj-id")
        assert parts.refresh_token == "rt"
        assert parts.project_id == "proj-id"
        assert parts.managed_project_id == ""

    def test_token_with_project_and_managed(self):
        parts = RefreshParts.parse("rt|proj|managed-proj")
        assert parts.refresh_token == "rt"
        assert parts.project_id == "proj"
        assert parts.managed_project_id == "managed-proj"

    def test_managed_can_contain_pipes(self):
        # split limit=2 → managed slot absorbs any trailing pipes.
        parts = RefreshParts.parse("rt|proj|with|extra|pipes")
        assert parts.refresh_token == "rt"
        assert parts.project_id == "proj"
        assert parts.managed_project_id == "with|extra|pipes"


class TestRefreshPartsFormat:
    def test_empty_token_formats_to_empty(self):
        parts = RefreshParts(refresh_token="")
        assert parts.format() == ""

    def test_token_only_formats_to_bare_token(self):
        parts = RefreshParts(refresh_token="rt-abc")
        assert parts.format() == "rt-abc"

    def test_token_with_project_uses_pipe_delimiter(self):
        parts = RefreshParts(
            refresh_token="rt", project_id="proj", managed_project_id=""
        )
        assert parts.format() == "rt|proj|"

    def test_token_with_managed_only_still_pipe_delimited(self):
        parts = RefreshParts(
            refresh_token="rt", project_id="", managed_project_id="m"
        )
        assert parts.format() == "rt||m"


class TestRefreshPartsRoundTrip:
    @pytest.mark.parametrize("packed", [
        "rt-abc",
        "rt|proj",
        "rt|proj|managed",
        "rt||managed",
        "rt|with-dash|hyphen-project",
    ])
    def test_parse_then_format_round_trips(self, packed: str):
        parsed = RefreshParts.parse(packed)
        # format() may add/remove a trailing pipe for empty slots, so
        # reparse and compare canonical fields rather than raw strings.
        reparsed = RefreshParts.parse(parsed.format())
        assert reparsed.refresh_token == parsed.refresh_token
        assert reparsed.project_id == parsed.project_id
        assert reparsed.managed_project_id == parsed.managed_project_id


class TestGoogleCredentialsRoundTrip:
    def test_to_dict_and_from_dict_preserve_fields(self):
        creds = GoogleCredentials(
            access_token="at",
            refresh_token="rt",
            expires_ms=1_700_000_000_000,
            email="user@example.com",
            project_id="proj-1",
            managed_project_id="managed-2",
        )
        d = creds.to_dict()
        # Required on-disk keys.
        assert set(d.keys()) == {"refresh", "access", "expires", "email"}
        re = GoogleCredentials.from_dict(d)
        assert re.access_token == creds.access_token
        assert re.refresh_token == creds.refresh_token
        assert re.expires_ms == creds.expires_ms
        assert re.email == creds.email
        assert re.project_id == creds.project_id
        assert re.managed_project_id == creds.managed_project_id

    def test_from_dict_missing_fields_default_to_blank(self):
        creds = GoogleCredentials.from_dict({})
        assert creds.access_token == ""
        assert creds.refresh_token == ""
        assert creds.expires_ms == 0
