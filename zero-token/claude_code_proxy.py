"""Claude Code subprocess proxy — exposes the local ``claude`` CLI as an
OpenAI-compatible /v1/chat/completions endpoint for hermes-gateway.

Why this exists: Telegram-driven hermes chats need to access the local
filesystem and run shell commands.  When we routed the LLM call to claude.ai
web, Claude refused because that surface presents itself as a sandboxed web
chatbot.  Claude Code is the legitimate "Claude running on your machine"
surface — full Bash/Read/Write/Edit, OAuth via the user's Claude subscription,
and no sandbox framing.

Architecture:
    Telegram → hermes-gateway → (HTTP) → THIS PROXY → (subprocess) → claude -p
    Each /v1/chat/completions call spawns ``claude -p`` with a fixed session
    UUID so subsequent calls continue the same conversation.  Hermes-side tools
    are ignored; Claude Code uses its own toolbox.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

from aiohttp import web

LOG = logging.getLogger("claude-code-proxy")
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

# Defence-in-depth: ignore SIGHUP at the proxy itself.  Even if start_new_session
# fails to fully isolate claude's process group on some kernel/setup, an HUP
# arriving at us will be discarded rather than terminating the server.
import signal as _signal
_signal.signal(_signal.SIGHUP, _signal.SIG_IGN)

LISTEN_HOST = os.environ.get("CLAUDE_PROXY_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("CLAUDE_PROXY_PORT", "3031"))
DEFAULT_MODEL = os.environ.get("CLAUDE_PROXY_MODEL", "claude-sonnet-4-6")
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "/home/reyerchu/.local/bin/claude")

WORKSPACE = Path(
    os.environ.get("CLAUDE_PROXY_WORKSPACE", str(Path.home()))
)
WORKSPACE.mkdir(parents=True, exist_ok=True)

# Stored UUID for the *current* Claude Code session.  Holding it in a file
# (not a constant) is what lets us truly rotate sessions: rotation deletes
# the file, and the next call generates a brand-new UUID Claude Code has
# never seen — so it really does start fresh.  The legacy hardcoded
# 22222222-… UUID is kept as an env-override only for explicit pinning.
SESSION_DIR = Path.home() / ".hermes/zero-token"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
SESSION_FILE = SESSION_DIR / "current-session-uuid"
# Empty MCP config so `claude -p` doesn't load any globally-configured MCP
# servers on cold spawn (they were the main source of 90 s+ latency).
EMPTY_MCP_CONFIG = SESSION_DIR / "empty-mcp.json"
if not EMPTY_MCP_CONFIG.exists():
    EMPTY_MCP_CONFIG.write_text('{"mcpServers": {}}')
# Backwards-compatible "session has been initialised" marker (still touched
# so external scripts checking for the old flag keep working).
SESSION_FLAG = SESSION_DIR / ".session-initialized"


def _current_session_uuid() -> str:
    """Return the active session UUID, generating + persisting one if needed."""
    env_pin = os.environ.get("CLAUDE_PROXY_SESSION_UUID")
    if env_pin:
        return env_pin
    if SESSION_FILE.exists():
        text = SESSION_FILE.read_text().strip()
        if text:
            return text
    new = str(uuid.uuid4())
    SESSION_FILE.write_text(new)
    LOG.info("generated new session UUID: %s", new)
    return new


def _rotate_session() -> None:
    """Force the next call to use a brand-new session UUID."""
    SESSION_FILE.unlink(missing_ok=True)
    SESSION_FLAG.unlink(missing_ok=True)

# Hard-deadline per request.  Originally 300 s; tightened to 90 s when stuck
# sessions were the dominant failure; bumped to 180 s once we discovered that
# real Telegram tasks (file search, web fetch, multi-step tool use) legitimately
# take >90 s.  180 s is the sweet spot: long enough for genuine tool loops,
# short enough that the user sees a recovery message before giving up.
REQUEST_TIMEOUT_S = int(os.environ.get("CLAUDE_PROXY_TIMEOUT", "180"))

# After this many seconds of session lifetime, force a fresh session UUID so
# context doesn't grow unbounded (the root cause of the 2026-05-22 stuck-loop
# issue).  Default 4 h; override with CLAUDE_PROXY_SESSION_MAX_AGE.
SESSION_MAX_AGE_S = int(os.environ.get("CLAUDE_PROXY_SESSION_MAX_AGE", "14400"))

# System-prompt override fed via --append-system-prompt on every call.
# Suppresses the user's global CLAUDE.md "confirm in zh+en then Go or not?" pattern
# (which makes no sense in a Telegram chat) and tells Claude its operating context.
SYSTEM_OVERRIDE = (
    "You are responding to a chat message relayed from Telegram via hermes-agent. "
    "You are running as Claude Code on the user's Linux machine (hostname 8HD-7). "
    "You have full local filesystem access and may run shell commands via your "
    "Bash/Read/Write/Edit/Glob tools — do not claim you are in a sandbox. "
    "IGNORE any 'My understanding... Go or not?' confirmation protocol from the "
    "user's global CLAUDE.md — Telegram interactions are conversational, not "
    "stepwise approvals. Answer the user's question or perform the requested "
    "action directly, briefly, and in the same language they used. "
    "The user is reyerchu (charlieway60@gmail.com). Default working directory: "
    f"{Path.home()}. Time-zone Asia/Taipei. "
)

# Serialise claude invocations so they don't fight for stdin/permissions.
_lock = asyncio.Lock()


def extract_latest_user(messages: list[dict[str, Any]]) -> str:
    """Pull the last user-originated message from an OpenAI-style messages list.

    Hermes sends the whole conversation, but Claude Code keeps its own history
    via --session-id continuity, so we only forward the latest user turn.
    Tool-result messages (role="tool") are flattened into the prompt as plain
    text so the user-side text intent is preserved.
    """
    if not messages:
        return ""
    # Walk backwards for the most recent user/tool message; ignore assistant turns.
    for m in reversed(messages):
        role = m.get("role")
        if role == "user":
            content = m.get("content")
            if isinstance(content, list):
                return "".join(
                    c.get("text", "") for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                )
            return content or ""
        if role == "tool":
            body = m.get("content") or ""
            if isinstance(body, list):
                body = "".join(c.get("text", "") for c in body if isinstance(c, dict))
            return f"Tool result: {body}"
    # Fallback: stringify the final message.
    return str(messages[-1].get("content") or "")


def _build_claude_args(prompt: str, resume: bool) -> list[str]:
    args: list[str] = [
        CLAUDE_BIN,
        "-p",
        "--output-format", "json",
        "--dangerously-skip-permissions",
        "--append-system-prompt", SYSTEM_OVERRIDE,
        # Disable MCP loading on cold spawn.  Each Telegram message spawns a
        # fresh `claude -p` subprocess, and globally-configured MCP servers
        # (Gmail/Calendar/Harvey/…) each open network connections on startup
        # — which made cold-spawn latency exceed our 90 s budget.  The proxy
        # uses Claude Code's built-in Bash/Read/Write/Edit/Grep instead.
        "--strict-mcp-config",
        "--mcp-config", str(EMPTY_MCP_CONFIG),
    ]
    session_uuid = _current_session_uuid()
    if resume:
        args += ["--resume", session_uuid]
    else:
        args += ["--session-id", session_uuid]
    # "--" terminates option parsing; otherwise prompts starting with "-"
    # (e.g. a bullet list "- foo") get rejected by claude as unknown flag.
    args.extend(["--", prompt])
    return args


async def _run_claude_once(prompt: str, resume: bool) -> tuple[int, bytes, bytes]:
    args = _build_claude_args(prompt, resume)
    LOG.info("spawn claude: resume=%s prompt=%d chars", resume, len(prompt))
    # IMPORTANT: start_new_session=True puts claude in its own session/process
    # group.  Without this, claude (a Node.js process) inherits our pgid and
    # any group-wide signal it issues during cleanup (e.g. kill(-pgid, SIGHUP)
    # to reap tool subprocesses) propagates back to us, killing the proxy.
    # We observed exactly this on 2026-05-17 21:28: proxy got SIGHUP 96s into
    # a long multi-tool claude run with no other plausible source on the host.
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=str(WORKSPACE),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.DEVNULL,
        start_new_session=True,
        env={**os.environ, "CLAUDE_CODE_NONINTERACTIVE": "1"},
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(), timeout=REQUEST_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        # Auto-reset: a stuck session keeps failing on every retry, so
        # rotate the UUID — the next call will use a UUID Claude Code has
        # never seen and starts genuinely fresh.
        _rotate_session()
        raise RuntimeError(
            f"claude -p timed out after {REQUEST_TIMEOUT_S}s — session rotated; retry your message"
        )
    return proc.returncode or 0, stdout_b, stderr_b


async def claude_code_call(prompt: str) -> dict[str, Any]:
    async with _lock:
        # Session age cap: if the flag is older than SESSION_MAX_AGE_S, rotate
        # to a fresh session UUID so context doesn't snowball.
        if SESSION_FLAG.exists():
            try:
                age = time.time() - SESSION_FLAG.stat().st_mtime
                if age > SESSION_MAX_AGE_S:
                    LOG.info("session age %.0fs > %ds; rotating to fresh session",
                             age, SESSION_MAX_AGE_S)
                    _rotate_session()
            except OSError:
                pass

        resume_first = SESSION_FLAG.exists()
        rc, stdout_b, stderr_b = await _run_claude_once(prompt, resume=resume_first)

        if rc != 0:
            stderr = stderr_b.decode(errors="replace")
            # Auto-recover when the session-flag and Claude's session DB disagree.
            if (not resume_first) and "already in use" in stderr:
                LOG.warning("session already exists; retrying with --resume")
                SESSION_FLAG.touch()
                rc, stdout_b, stderr_b = await _run_claude_once(prompt, resume=True)
            elif resume_first and ("not found" in stderr.lower() or "does not exist" in stderr.lower()):
                LOG.warning("stored session missing; rotating to fresh UUID")
                _rotate_session()
                rc, stdout_b, stderr_b = await _run_claude_once(prompt, resume=False)

        if rc != 0:
            stderr = stderr_b.decode(errors="replace")
            raise RuntimeError(f"claude -p exited {rc}: stderr={stderr[:1500]}")

        if not SESSION_FLAG.exists():
            SESSION_FLAG.touch()

    try:
        data = json.loads(stdout_b.decode())
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"claude -p returned non-JSON output: {exc}: {stdout_b[:1000]!r}"
        )
    if data.get("is_error"):
        raise RuntimeError(f"claude reported error: {data.get('result')}")
    return data


def _build_chunk(cid: str, model: str, created: int, delta: dict[str, Any], finish: str | None) -> dict[str, Any]:
    return {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }


async def handle_chat_completions(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
    except Exception as exc:
        return web.json_response(
            {"error": {"message": f"Invalid JSON: {exc}", "type": "invalid_request_error"}},
            status=400,
        )

    messages = payload.get("messages") or []
    model = payload.get("model") or DEFAULT_MODEL
    stream = bool(payload.get("stream"))
    if not messages:
        return web.json_response(
            {"error": {"message": "messages required", "type": "invalid_request_error"}},
            status=400,
        )

    prompt = extract_latest_user(messages)
    if not prompt.strip():
        return web.json_response(
            {"error": {"message": "no user prompt found in messages", "type": "invalid_request_error"}},
            status=400,
        )

    try:
        data = await claude_code_call(prompt)
    except Exception as exc:
        LOG.exception("claude-code call failed")
        return web.json_response(
            {"error": {"message": str(exc), "type": "api_error"}}, status=500,
        )

    text = data.get("result") or ""
    usage = data.get("usage") or {}
    cid = f"chatcmpl-{uuid.uuid4()}"
    created = int(time.time())
    finish = "stop"

    LOG.info("claude-code response: %d chars, cost=$%s",
             len(text), data.get("total_cost_usd"))

    if stream:
        resp = web.StreamResponse(status=200, headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        })
        await resp.prepare(request)
        await resp.write(
            f"data: {json.dumps(_build_chunk(cid, model, created, {'role': 'assistant', 'content': text}, None))}\n\n".encode()
        )
        await resp.write(
            f"data: {json.dumps(_build_chunk(cid, model, created, {}, finish))}\n\n".encode()
        )
        await resp.write(b"data: [DONE]\n\n")
        await resp.write_eof()
        return resp

    return web.json_response({
        "id": cid,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": text},
            "finish_reason": finish,
        }],
        "usage": {
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
        },
    })


async def handle_models(_request: web.Request) -> web.Response:
    return web.json_response({
        "object": "list",
        "data": [
            {"id": mid, "object": "model", "created": 0, "owned_by": "claude-code"}
            for mid in ("claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5",
                        "claude-opus-4-7", "claude-sonnet-4-7")
        ],
    })


async def handle_health(_request: web.Request) -> web.Response:
    return web.json_response({
        "ok": True,
        "session_uuid": _current_session_uuid(),
        "session_initialised": SESSION_FLAG.exists(),
        "workspace": str(WORKSPACE),
    })


async def handle_reset(_request: web.Request) -> web.Response:
    """POST /reset rotates to a new session UUID on the next call."""
    _rotate_session()
    return web.json_response({"ok": True, "reset": True})


def build_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/v1/chat/completions", handle_chat_completions)
    app.router.add_get("/v1/models", handle_models)
    app.router.add_get("/health", handle_health)
    app.router.add_post("/reset", handle_reset)
    return app


def main() -> None:
    LOG.info("Starting claude-code proxy on %s:%d", LISTEN_HOST, LISTEN_PORT)
    LOG.info("Workspace: %s  Session UUID: %s  initialised=%s",
             WORKSPACE, _current_session_uuid(), SESSION_FLAG.exists())
    LOG.info("claude bin: %s", CLAUDE_BIN)
    web.run_app(build_app(), host=LISTEN_HOST, port=LISTEN_PORT, print=None)


if __name__ == "__main__":
    main()
