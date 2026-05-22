"""Tests for zero-token/claude_code_proxy.py.

Covers every code path: pure helpers, session-UUID rotation, argv
construction, subprocess timeout handling, OpenAI-compat HTTP surface,
and the SIGHUP defence-in-depth.  Each test runs against a fresh import
of the proxy with an isolated HOME (see conftest.proxy fixture).

The real ``claude`` binary is never invoked; subprocess interactions are
mocked at the asyncio.create_subprocess_exec level.
"""
from __future__ import annotations

import asyncio
import json
import os
import signal
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer


# ---------------------------------------------------------------------------
# Module-import side effects
# ---------------------------------------------------------------------------


class TestModuleSideEffects:
    def test_session_dir_created_on_import(self, proxy):
        assert proxy.SESSION_DIR.exists() and proxy.SESSION_DIR.is_dir()

    def test_empty_mcp_config_created_on_import(self, proxy):
        assert proxy.EMPTY_MCP_CONFIG.exists()
        content = json.loads(proxy.EMPTY_MCP_CONFIG.read_text())
        assert content == {"mcpServers": {}}

    def test_empty_mcp_config_not_overwritten_if_exists(self, tmp_path, monkeypatch):
        # Pre-populate with custom content; the fresh import must leave it alone.
        monkeypatch.setenv("HOME", str(tmp_path))
        custom_dir = tmp_path / ".hermes" / "zero-token"
        custom_dir.mkdir(parents=True)
        custom_cfg = custom_dir / "empty-mcp.json"
        custom_cfg.write_text('{"mcpServers": {"foo": {"url": "x"}}}')

        from tests.zero_token.conftest import _load_proxy

        mod = _load_proxy(tmp_path)
        assert json.loads(mod.EMPTY_MCP_CONFIG.read_text())["mcpServers"] == {
            "foo": {"url": "x"}
        }

    def test_workspace_default_is_home(self, proxy):
        assert proxy.WORKSPACE == Path(os.environ["HOME"])

    def test_sighup_handler_is_ignored(self, proxy):
        # Defence-in-depth: proxy must IGN SIGHUP at import.
        current = signal.getsignal(signal.SIGHUP)
        assert current == signal.SIG_IGN

    def test_request_timeout_default(self, proxy):
        assert proxy.REQUEST_TIMEOUT_S == 180

    def test_request_timeout_env_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("CLAUDE_PROXY_TIMEOUT", "42")
        from tests.zero_token.conftest import _load_proxy

        mod = _load_proxy(tmp_path)
        assert mod.REQUEST_TIMEOUT_S == 42

    def test_session_max_age_default(self, proxy):
        assert proxy.SESSION_MAX_AGE_S == 14400

    def test_session_max_age_env_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("CLAUDE_PROXY_SESSION_MAX_AGE", "60")
        from tests.zero_token.conftest import _load_proxy

        mod = _load_proxy(tmp_path)
        assert mod.SESSION_MAX_AGE_S == 60


# ---------------------------------------------------------------------------
# _current_session_uuid + _rotate_session
# ---------------------------------------------------------------------------


class TestSessionUUID:
    def test_generates_new_uuid_when_file_missing(self, proxy):
        assert not proxy.SESSION_FILE.exists()
        uid = proxy._current_session_uuid()
        assert len(uid) == 36  # canonical UUID string
        assert proxy.SESSION_FILE.read_text().strip() == uid

    def test_returns_persisted_uuid(self, proxy):
        proxy.SESSION_FILE.write_text("11111111-2222-3333-4444-555555555555")
        assert (
            proxy._current_session_uuid()
            == "11111111-2222-3333-4444-555555555555"
        )

    def test_env_override_wins(self, proxy, monkeypatch):
        monkeypatch.setenv(
            "CLAUDE_PROXY_SESSION_UUID", "deadbeef-dead-beef-dead-beefdeadbeef"
        )
        proxy.SESSION_FILE.write_text("ignored")
        assert (
            proxy._current_session_uuid()
            == "deadbeef-dead-beef-dead-beefdeadbeef"
        )

    def test_empty_file_regenerates(self, proxy):
        proxy.SESSION_FILE.write_text("   \n")
        uid = proxy._current_session_uuid()
        assert uid.strip()
        assert len(uid) == 36

    def test_uuid_persists_across_calls(self, proxy):
        first = proxy._current_session_uuid()
        second = proxy._current_session_uuid()
        assert first == second

    def test_rotate_removes_session_file(self, proxy):
        proxy._current_session_uuid()
        assert proxy.SESSION_FILE.exists()
        proxy._rotate_session()
        assert not proxy.SESSION_FILE.exists()

    def test_rotate_removes_session_flag(self, proxy):
        proxy.SESSION_FLAG.touch()
        proxy._rotate_session()
        assert not proxy.SESSION_FLAG.exists()

    def test_rotate_is_idempotent(self, proxy):
        # Should not raise when files are already missing.
        proxy._rotate_session()
        proxy._rotate_session()
        assert not proxy.SESSION_FILE.exists()

    def test_rotate_then_uuid_yields_new(self, proxy):
        first = proxy._current_session_uuid()
        proxy._rotate_session()
        second = proxy._current_session_uuid()
        assert first != second


# ---------------------------------------------------------------------------
# _build_claude_args
# ---------------------------------------------------------------------------


class TestBuildClaudeArgs:
    def test_includes_dangerously_skip_permissions(self, proxy):
        args = proxy._build_claude_args("hi", resume=False)
        assert "--dangerously-skip-permissions" in args

    def test_includes_strict_mcp_config(self, proxy):
        args = proxy._build_claude_args("hi", resume=False)
        assert "--strict-mcp-config" in args

    def test_mcp_config_points_at_empty_file(self, proxy):
        args = proxy._build_claude_args("hi", resume=False)
        i = args.index("--mcp-config")
        assert Path(args[i + 1]) == proxy.EMPTY_MCP_CONFIG

    def test_append_system_prompt_present(self, proxy):
        args = proxy._build_claude_args("hi", resume=False)
        i = args.index("--append-system-prompt")
        assert "Telegram" in args[i + 1] and "8HD-7" in args[i + 1]

    def test_output_format_json(self, proxy):
        args = proxy._build_claude_args("hi", resume=False)
        i = args.index("--output-format")
        assert args[i + 1] == "json"

    def test_session_id_when_not_resuming(self, proxy):
        args = proxy._build_claude_args("hi", resume=False)
        assert "--session-id" in args
        assert "--resume" not in args

    def test_resume_when_resuming(self, proxy):
        args = proxy._build_claude_args("hi", resume=True)
        assert "--resume" in args
        assert "--session-id" not in args

    def test_uuid_in_args_matches_current_uuid(self, proxy):
        uid = proxy._current_session_uuid()
        args = proxy._build_claude_args("hi", resume=False)
        assert uid in args

    def test_prompt_after_double_dash_separator(self, proxy):
        """A prompt starting with '-' would be misread without the separator."""
        args = proxy._build_claude_args("- bullet item", resume=False)
        sep = args.index("--")
        # Everything after -- is the prompt
        assert args[sep + 1] == "- bullet item"

    def test_unicode_prompt_round_trips(self, proxy):
        args = proxy._build_claude_args("你好，世界 🌏", resume=False)
        assert "你好，世界 🌏" in args


# ---------------------------------------------------------------------------
# extract_latest_user
# ---------------------------------------------------------------------------


class TestExtractLatestUser:
    def test_empty_messages_returns_empty(self, proxy):
        assert proxy.extract_latest_user([]) == ""

    def test_single_user_message(self, proxy):
        out = proxy.extract_latest_user([{"role": "user", "content": "hi"}])
        assert out == "hi"

    def test_walks_back_to_last_user_message(self, proxy):
        msgs = [
            {"role": "user", "content": "first user"},
            {"role": "assistant", "content": "reply"},
            {"role": "user", "content": "second user"},
        ]
        assert proxy.extract_latest_user(msgs) == "second user"

    def test_skips_assistant_turns(self, proxy):
        msgs = [
            {"role": "user", "content": "ask"},
            {"role": "assistant", "content": "answer"},
        ]
        assert proxy.extract_latest_user(msgs) == "ask"

    def test_content_as_list_of_text_blocks(self, proxy):
        msgs = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "hello "},
                    {"type": "text", "text": "world"},
                    {"type": "image_url", "url": "ignored"},
                ],
            }
        ]
        assert proxy.extract_latest_user(msgs) == "hello world"

    def test_tool_message_prefixed(self, proxy):
        msgs = [{"role": "tool", "content": "tool output"}]
        assert proxy.extract_latest_user(msgs) == "Tool result: tool output"

    def test_tool_message_list_content(self, proxy):
        msgs = [
            {
                "role": "tool",
                "content": [{"type": "text", "text": "part1 "}, {"type": "text", "text": "part2"}],
            }
        ]
        assert proxy.extract_latest_user(msgs) == "Tool result: part1 part2"

    def test_fallback_to_stringified_last_message(self, proxy):
        msgs = [{"role": "system", "content": "sys prompt"}]
        # No user or tool: should stringify last message's content
        assert proxy.extract_latest_user(msgs) == "sys prompt"

    def test_user_with_none_content(self, proxy):
        msgs = [{"role": "user", "content": None}]
        assert proxy.extract_latest_user(msgs) == ""


# ---------------------------------------------------------------------------
# _run_claude_once  (subprocess mocked)
# ---------------------------------------------------------------------------


def _fake_proc(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"",
               hang_seconds: float = 0.0):
    """Build a mock asyncio.subprocess.Process compatible with proc.communicate()."""
    mock = MagicMock()
    mock.returncode = returncode
    mock.kill = MagicMock()

    async def _wait():
        return None

    async def _communicate():
        if hang_seconds:
            await asyncio.sleep(hang_seconds)
        return stdout, stderr

    mock.wait = AsyncMock(side_effect=_wait)
    mock.communicate = AsyncMock(side_effect=_communicate)
    return mock


class TestRunClaudeOnce:
    @pytest.mark.asyncio
    async def test_returns_rc_stdout_stderr(self, proxy):
        fake = _fake_proc(0, b'{"result":"ok"}', b"")
        with patch(
            "asyncio.create_subprocess_exec", AsyncMock(return_value=fake)
        ):
            rc, out, err = await proxy._run_claude_once("hi", resume=False)
        assert rc == 0 and out == b'{"result":"ok"}' and err == b""

    @pytest.mark.asyncio
    async def test_timeout_kills_process(self, proxy, monkeypatch):
        monkeypatch.setattr(proxy, "REQUEST_TIMEOUT_S", 0.05)
        fake = _fake_proc(hang_seconds=1.0)
        with patch(
            "asyncio.create_subprocess_exec", AsyncMock(return_value=fake)
        ):
            with pytest.raises(RuntimeError, match="timed out"):
                await proxy._run_claude_once("hi", resume=False)
        fake.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_timeout_rotates_session(self, proxy, monkeypatch):
        # Pre-create state that rotation should clear.
        proxy.SESSION_FILE.write_text("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        proxy.SESSION_FLAG.touch()
        monkeypatch.setattr(proxy, "REQUEST_TIMEOUT_S", 0.05)
        fake = _fake_proc(hang_seconds=1.0)
        with patch(
            "asyncio.create_subprocess_exec", AsyncMock(return_value=fake)
        ):
            with pytest.raises(RuntimeError):
                await proxy._run_claude_once("hi", resume=True)
        assert not proxy.SESSION_FILE.exists()
        assert not proxy.SESSION_FLAG.exists()

    @pytest.mark.asyncio
    async def test_timeout_error_message_mentions_rotation(
        self, proxy, monkeypatch
    ):
        monkeypatch.setattr(proxy, "REQUEST_TIMEOUT_S", 0.01)
        fake = _fake_proc(hang_seconds=0.5)
        with patch(
            "asyncio.create_subprocess_exec", AsyncMock(return_value=fake)
        ):
            with pytest.raises(RuntimeError, match="session rotated"):
                await proxy._run_claude_once("hi", resume=False)

    @pytest.mark.asyncio
    async def test_spawn_args_use_start_new_session(self, proxy):
        fake = _fake_proc(0, b'{"result":"ok"}', b"")
        spawn = AsyncMock(return_value=fake)
        with patch("asyncio.create_subprocess_exec", spawn):
            await proxy._run_claude_once("hi", resume=False)
        # The kwarg start_new_session=True is mandatory: see comment block in the
        # source about SIGHUP propagation killing the proxy.
        assert spawn.call_args.kwargs["start_new_session"] is True

    @pytest.mark.asyncio
    async def test_spawn_args_cwd_is_workspace(self, proxy):
        fake = _fake_proc(0, b'{"result":"ok"}', b"")
        spawn = AsyncMock(return_value=fake)
        with patch("asyncio.create_subprocess_exec", spawn):
            await proxy._run_claude_once("hi", resume=False)
        assert spawn.call_args.kwargs["cwd"] == str(proxy.WORKSPACE)


# ---------------------------------------------------------------------------
# claude_code_call  (high-level orchestrator)
# ---------------------------------------------------------------------------


class TestClaudeCodeCall:
    @pytest.mark.asyncio
    async def test_first_call_uses_session_id_then_touches_flag(self, proxy):
        captured: list[bool] = []

        async def fake_run(prompt, resume):
            captured.append(resume)
            return 0, b'{"result":"hi","usage":{"input_tokens":1,"output_tokens":1}}', b""

        with patch.object(proxy, "_run_claude_once", side_effect=fake_run):
            data = await proxy.claude_code_call("hello")

        assert captured == [False]  # fresh session — no --resume
        assert proxy.SESSION_FLAG.exists()
        assert data["result"] == "hi"

    @pytest.mark.asyncio
    async def test_subsequent_call_uses_resume(self, proxy):
        proxy.SESSION_FLAG.touch()
        captured: list[bool] = []

        async def fake_run(prompt, resume):
            captured.append(resume)
            return 0, b'{"result":"ok"}', b""

        with patch.object(proxy, "_run_claude_once", side_effect=fake_run):
            await proxy.claude_code_call("hi")
        assert captured == [True]

    @pytest.mark.asyncio
    async def test_age_cap_rotates_session(self, proxy, monkeypatch):
        # Touch flag and backdate it to look ancient.
        proxy.SESSION_FILE.write_text("old-uuid")
        proxy.SESSION_FLAG.touch()
        past = time.time() - (proxy.SESSION_MAX_AGE_S + 10)
        os.utime(proxy.SESSION_FLAG, (past, past))

        captured: list[bool] = []

        async def fake_run(prompt, resume):
            captured.append(resume)
            return 0, b'{"result":"ok"}', b""

        with patch.object(proxy, "_run_claude_once", side_effect=fake_run):
            await proxy.claude_code_call("hi")

        # Aged out, so rotation happened: session file gone before the spawn.
        # The fresh spawn must therefore not pass --resume.
        assert captured == [False]

    @pytest.mark.asyncio
    async def test_recovery_when_session_already_in_use(self, proxy):
        """First call says 'already in use' on session-id; auto-retry with resume."""
        calls: list[bool] = []

        async def fake_run(prompt, resume):
            calls.append(resume)
            if len(calls) == 1:
                return 1, b"", b"error: session already in use"
            return 0, b'{"result":"recovered"}', b""

        with patch.object(proxy, "_run_claude_once", side_effect=fake_run):
            data = await proxy.claude_code_call("hi")
        assert calls == [False, True]
        assert data["result"] == "recovered"
        assert proxy.SESSION_FLAG.exists()

    @pytest.mark.asyncio
    async def test_recovery_when_stored_session_missing(self, proxy):
        """--resume fails with 'not found'; rotate and retry with session-id."""
        proxy.SESSION_FILE.write_text("ghost-uuid")
        proxy.SESSION_FLAG.touch()
        calls: list[bool] = []

        async def fake_run(prompt, resume):
            calls.append(resume)
            if len(calls) == 1:
                return 1, b"", b"error: session not found"
            return 0, b'{"result":"new"}', b""

        with patch.object(proxy, "_run_claude_once", side_effect=fake_run):
            data = await proxy.claude_code_call("hi")
        assert calls == [True, False]
        assert data["result"] == "new"
        # Rotation deletes the ghost-uuid file (mocked _run_claude_once never
        # rebuilds args, so no new UUID is generated yet — just deletion).
        assert not proxy.SESSION_FILE.exists() or (
            proxy.SESSION_FILE.read_text().strip() != "ghost-uuid"
        )

    @pytest.mark.asyncio
    async def test_non_zero_exit_raises_runtime_error(self, proxy):
        async def fake_run(prompt, resume):
            return 5, b"", b"some unrecoverable claude failure"

        with patch.object(proxy, "_run_claude_once", side_effect=fake_run):
            with pytest.raises(RuntimeError, match="exited 5"):
                await proxy.claude_code_call("hi")

    @pytest.mark.asyncio
    async def test_non_json_stdout_raises(self, proxy):
        async def fake_run(prompt, resume):
            return 0, b"not json at all", b""

        with patch.object(proxy, "_run_claude_once", side_effect=fake_run):
            with pytest.raises(RuntimeError, match="non-JSON"):
                await proxy.claude_code_call("hi")

    @pytest.mark.asyncio
    async def test_is_error_in_response_raises(self, proxy):
        async def fake_run(prompt, resume):
            return 0, b'{"is_error":true,"result":"model refused"}', b""

        with patch.object(proxy, "_run_claude_once", side_effect=fake_run):
            with pytest.raises(RuntimeError, match="model refused"):
                await proxy.claude_code_call("hi")

    @pytest.mark.asyncio
    async def test_lock_serialises_concurrent_calls(self, proxy):
        """Two simultaneous calls must run sequentially under the proxy lock."""
        order: list[str] = []

        async def fake_run(prompt, resume):
            order.append(f"start:{prompt}")
            await asyncio.sleep(0.05)
            order.append(f"end:{prompt}")
            return 0, b'{"result":"ok"}', b""

        with patch.object(proxy, "_run_claude_once", side_effect=fake_run):
            await asyncio.gather(
                proxy.claude_code_call("a"),
                proxy.claude_code_call("b"),
            )

        # No interleaving: every start must be followed by its own end.
        assert order in (
            ["start:a", "end:a", "start:b", "end:b"],
            ["start:b", "end:b", "start:a", "end:a"],
        )


# ---------------------------------------------------------------------------
# HTTP handlers — use aiohttp TestServer with claude_code_call mocked
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client(proxy):
    """aiohttp TestClient pointed at the proxy's app."""
    app = proxy.build_app()
    async with TestServer(app) as server, TestClient(server) as cli:
        yield cli


def _ok_response(text: str = "pong", cost: float = 0.0) -> dict[str, Any]:
    return {
        "result": text,
        "usage": {"input_tokens": 3, "output_tokens": 1},
        "total_cost_usd": cost,
    }


class TestChatCompletionsEndpoint:
    @pytest.mark.asyncio
    async def test_returns_openai_shape(self, proxy, client):
        with patch.object(
            proxy, "claude_code_call", AsyncMock(return_value=_ok_response("hello"))
        ):
            resp = await client.post(
                "/v1/chat/completions",
                json={
                    "model": "claude-sonnet-4-6",
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
        assert resp.status == 200
        body = await resp.json()
        assert body["object"] == "chat.completion"
        assert body["model"] == "claude-sonnet-4-6"
        assert body["choices"][0]["message"]["content"] == "hello"
        assert body["choices"][0]["finish_reason"] == "stop"

    @pytest.mark.asyncio
    async def test_default_model_when_not_specified(self, proxy, client):
        with patch.object(
            proxy, "claude_code_call", AsyncMock(return_value=_ok_response())
        ):
            resp = await client.post(
                "/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "hi"}]},
            )
        body = await resp.json()
        assert body["model"] == proxy.DEFAULT_MODEL

    @pytest.mark.asyncio
    async def test_invalid_json_returns_400(self, client):
        resp = await client.post(
            "/v1/chat/completions",
            data="not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status == 400
        body = await resp.json()
        assert body["error"]["type"] == "invalid_request_error"

    @pytest.mark.asyncio
    async def test_missing_messages_returns_400(self, client):
        resp = await client.post("/v1/chat/completions", json={})
        assert resp.status == 400
        body = await resp.json()
        assert "messages required" in body["error"]["message"]

    @pytest.mark.asyncio
    async def test_no_user_prompt_returns_400(self, client):
        # extract_latest_user falls back to stringifying the final message's
        # content; an empty content string is what actually triggers the
        # "no user prompt" branch.
        resp = await client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": ""}]},
        )
        assert resp.status == 400
        body = await resp.json()
        assert "no user prompt" in body["error"]["message"]

    @pytest.mark.asyncio
    async def test_claude_failure_returns_500(self, proxy, client):
        with patch.object(
            proxy,
            "claude_code_call",
            AsyncMock(side_effect=RuntimeError("claude blew up")),
        ):
            resp = await client.post(
                "/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "hi"}]},
            )
        assert resp.status == 500
        body = await resp.json()
        assert body["error"]["type"] == "api_error"
        assert "claude blew up" in body["error"]["message"]

    @pytest.mark.asyncio
    async def test_usage_fields_populated(self, proxy, client):
        with patch.object(
            proxy, "claude_code_call", AsyncMock(return_value=_ok_response())
        ):
            resp = await client.post(
                "/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "hi"}]},
            )
        body = await resp.json()
        assert body["usage"]["prompt_tokens"] == 3
        assert body["usage"]["completion_tokens"] == 1
        assert body["usage"]["total_tokens"] == 4

    @pytest.mark.asyncio
    async def test_streaming_response(self, proxy, client):
        with patch.object(
            proxy, "claude_code_call", AsyncMock(return_value=_ok_response("pong"))
        ):
            resp = await client.post(
                "/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": True,
                },
            )
        assert resp.status == 200
        assert resp.headers["Content-Type"].startswith("text/event-stream")
        body = (await resp.read()).decode()
        # The proxy emits two data: blocks then [DONE].
        assert body.count("data: ") >= 2
        assert "[DONE]" in body
        assert "pong" in body


class TestOtherEndpoints:
    @pytest.mark.asyncio
    async def test_models_listing(self, client):
        resp = await client.get("/v1/models")
        assert resp.status == 200
        body = await resp.json()
        assert body["object"] == "list"
        ids = [m["id"] for m in body["data"]]
        assert "claude-sonnet-4-6" in ids
        assert "claude-opus-4-7" in ids
        for m in body["data"]:
            assert m["owned_by"] == "claude-code"

    @pytest.mark.asyncio
    async def test_health_endpoint(self, proxy, client):
        resp = await client.get("/health")
        body = await resp.json()
        assert body["ok"] is True
        assert body["workspace"] == str(proxy.WORKSPACE)
        # session_uuid is generated on demand by the call
        assert len(body["session_uuid"]) == 36

    @pytest.mark.asyncio
    async def test_health_reports_session_initialised_flag(self, proxy, client):
        resp = await client.get("/health")
        assert (await resp.json())["session_initialised"] is False
        proxy.SESSION_FLAG.touch()
        resp = await client.get("/health")
        assert (await resp.json())["session_initialised"] is True

    @pytest.mark.asyncio
    async def test_reset_endpoint_rotates(self, proxy, client):
        proxy.SESSION_FILE.write_text("aaaa-bbbb")
        proxy.SESSION_FLAG.touch()
        resp = await client.post("/reset")
        body = await resp.json()
        assert body == {"ok": True, "reset": True}
        assert not proxy.SESSION_FILE.exists()
        assert not proxy.SESSION_FLAG.exists()

    @pytest.mark.asyncio
    async def test_reset_safe_when_already_clean(self, client):
        # Called twice in a row; second call must still succeed.
        await client.post("/reset")
        resp = await client.post("/reset")
        assert resp.status == 200
        assert (await resp.json())["ok"] is True


# ---------------------------------------------------------------------------
# build_app — routing sanity
# ---------------------------------------------------------------------------


class TestBuildApp:
    def test_app_has_all_expected_routes(self, proxy):
        app = proxy.build_app()
        paths = {(r.method, r.resource.canonical) for r in app.router.routes()}
        assert ("POST", "/v1/chat/completions") in paths
        assert ("GET", "/v1/models") in paths
        assert ("GET", "/health") in paths
        assert ("POST", "/reset") in paths
