"""Claude.ai web-session proxy — Python port of openclaw-zero-token's claude-web provider.

Exposes an OpenAI-compatible /v1/chat/completions endpoint that drives claude.ai
inside an attached Chrome (CDP debug) session, using a stored sessionKey+cookies
captured from a logged-in browser. No Anthropic API token required.

Phase 2 capabilities:
  - Tool calling translation (OpenAI tools <-> openclaw <tool_call> XML)
  - Streaming (SSE response is buffered for tool-call extraction, then emitted as
    OpenAI chat.completion.chunk events)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any

from aiohttp import web
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright

LOG = logging.getLogger("claude-web-proxy")
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

CDP_URL = os.environ.get("CLAUDE_WEB_CDP_URL", "http://127.0.0.1:9222")
AUTH_FILE = Path(
    os.environ.get(
        "CLAUDE_WEB_AUTH_FILE",
        str(Path.home() / "openclaw-zero-token/.openclaw-upstream-state/agents/main/agent/auth-profiles.json"),
    )
)
LISTEN_HOST = os.environ.get("CLAUDE_WEB_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("CLAUDE_WEB_PORT", "3031"))
DEFAULT_MODEL = os.environ.get("CLAUDE_WEB_DEFAULT_MODEL", "claude-sonnet-4-6")

# Map common OpenAI/upstream model aliases to claude.ai web ids.
MODEL_ALIASES = {
    "claude-3-5-sonnet": "claude-sonnet-4-6",
    "claude-3-opus": "claude-opus-4-6",
    "claude-3-haiku": "claude-haiku-4-6",
    "claude-sonnet-4-6": "claude-sonnet-4-6",
    "claude-opus-4-6": "claude-opus-4-6",
    "claude-haiku-4-6": "claude-haiku-4-6",
}

TOOL_FORMAT_HINT = (
    'To use a tool, output EXACTLY this XML: '
    '<tool_call id="unique_id" name="tool_name">{"arg":"value"}</tool_call>. '
    "Plain-text descriptions of tool actions WILL NOT execute the tool — emit the XML "
    "verbatim. Emit one <tool_call> per intended call. Use plain text only when no tool is needed."
)

# ───────────────────────── Auth profile ─────────────────────────

def load_auth() -> dict[str, Any]:
    raw = json.loads(AUTH_FILE.read_text())
    profile = raw["profiles"]["claude-web:default"]
    inner = json.loads(profile["token"])
    inner.setdefault("userAgent", "Mozilla/5.0")
    if not inner.get("cookie"):
        inner["cookie"] = f"sessionKey={inner['sessionKey']}"
    m = re.search(r"anthropic-device-id=([^;]+)", inner["cookie"])
    inner["deviceId"] = m.group(1) if m else str(uuid.uuid4())
    return inner


# ───────────────────────── Browser state ─────────────────────────

class BrowserSession:
    def __init__(self) -> None:
        self._pw: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._org_id: str | None = None
        self._auth: dict[str, Any] | None = None
        self._lock = asyncio.Lock()

    async def ensure(self) -> tuple[BrowserContext, Page, dict[str, Any]]:
        async with self._lock:
            if self._context and self._page and self._auth:
                return self._context, self._page, self._auth

            self._auth = load_auth()
            self._pw = await async_playwright().start()
            LOG.info("Connecting to Chrome CDP at %s", CDP_URL)
            browser = await self._pw.chromium.connect_over_cdp(CDP_URL)
            if not browser.contexts:
                raise RuntimeError("No CDP browser contexts available")
            self._context = browser.contexts[0]
            claude_page = next(
                (p for p in self._context.pages if "claude.ai" in p.url), None,
            )
            if claude_page is None:
                claude_page = await self._context.new_page()
                await claude_page.goto("https://claude.ai/new", wait_until="domcontentloaded")
            self._page = claude_page

            cookies = []
            for chunk in self._auth["cookie"].split(";"):
                if "=" not in chunk:
                    continue
                name, _, value = chunk.strip().partition("=")
                cookies.append({"name": name.strip(), "value": value.strip(), "domain": ".claude.ai", "path": "/"})
            if cookies:
                await self._context.add_cookies(cookies)

            await self._discover_org()
            LOG.info("Browser session ready; org=%s", self._org_id)
            return self._context, self._page, self._auth

    async def _discover_org(self) -> None:
        assert self._page and self._auth
        js = """async ({ deviceId }) => {
            const res = await fetch('https://claude.ai/api/organizations', {
                headers: {
                    Accept: 'application/json',
                    'anthropic-client-platform': 'web_claude_ai',
                    'anthropic-device-id': deviceId,
                },
                credentials: 'include',
            });
            return { status: res.status, body: res.ok ? await res.json() : await res.text() };
        }"""
        result = await self._page.evaluate(js, {"deviceId": self._auth["deviceId"]})
        if result["status"] == 200 and isinstance(result["body"], list) and result["body"]:
            self._org_id = result["body"][0]["uuid"]
        else:
            raise RuntimeError(f"Failed to discover organization: {result}")

    @property
    def org_id(self) -> str:
        if not self._org_id:
            raise RuntimeError("Browser session not initialized")
        return self._org_id


SESSION = BrowserSession()


# ───────────────────────── Tool prompt + history rendering ─────────────────────────

def render_tool_block(tools: list[dict[str, Any]]) -> str:
    """Render OpenAI tool definitions into a Claude-readable instruction block."""
    if not tools:
        return ""
    lines = ["", "## Available Tools"]
    for t in tools:
        fn = t.get("function") if isinstance(t, dict) else None
        if not fn:
            continue
        name = fn.get("name", "")
        desc = (fn.get("description") or "").strip()
        params = fn.get("parameters") or {}
        lines.append(f"- **{name}**: {desc}")
        if params:
            lines.append(f"  Parameters schema: {json.dumps(params, ensure_ascii=False)}")
    lines.append("")
    lines.append(TOOL_FORMAT_HINT)
    return "\n".join(lines)


def render_messages(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> str:
    """Flatten OpenAI message[] + tool definitions into a single textual prompt."""
    tools = tools or []
    tool_prompt = render_tool_block(tools)

    parts: list[str] = []
    has_system = any(m.get("role") == "system" for m in messages)

    # Standalone system block when caller didn't supply one but tools require it.
    if tool_prompt and not has_system:
        parts.append(f"System: {tool_prompt.lstrip()}")

    for m in messages:
        role = m.get("role", "user")
        content = m.get("content")
        if isinstance(content, list):
            content = "".join(
                c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
            )

        # Assistant turn with tool_calls — render as openclaw XML so context is preserved.
        if role == "assistant" and m.get("tool_calls"):
            buf = content or ""
            for tc in m["tool_calls"]:
                fn = tc.get("function") or {}
                tc_id = tc.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                args = fn.get("arguments")
                if isinstance(args, str):
                    args_str = args
                else:
                    args_str = json.dumps(args or {}, ensure_ascii=False)
                buf += f'\n<tool_call id="{tc_id}" name="{fn.get("name","")}">{args_str}</tool_call>'
            parts.append(f"Assistant: {buf}")
            continue

        # Tool result message (OpenAI: role="tool", with tool_call_id)
        if role == "tool":
            tc_id = m.get("tool_call_id", "")
            name = m.get("name", "")
            body = content if isinstance(content, str) else json.dumps(content or "", ensure_ascii=False)
            parts.append(
                f'User: <tool_response id="{tc_id}" name="{name}">\n{body}\n</tool_response>'
            )
            continue

        if not content:
            continue
        label = {
            "system": "System",
            "user": "User",
            "assistant": "Assistant",
        }.get(role, role.capitalize())

        # Append tool prompt onto the (first) system message.
        if role == "system" and tool_prompt:
            content = f"{content}\n{tool_prompt}"
            tool_prompt = ""  # only inject once

        parts.append(f"{label}: {content}")

    return "\n\n".join(parts)


# ───────────────────────── Response parsing ─────────────────────────

# Tolerant match: id="x" and name="y" can appear in either order or with single quotes.
TOOL_CALL_RE = re.compile(
    r"<tool_call\s+(?P<attrs>[^>]*?)>\s*(?P<body>.*?)\s*</tool_call>",
    re.DOTALL | re.IGNORECASE,
)
ATTR_RE = re.compile(r"""(\w+)\s*=\s*['"]([^'"]*)['"]""")


def extract_text_and_tool_calls(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Strip <tool_call> blocks out of ``text`` and return them as OpenAI tool_calls."""
    tool_calls: list[dict[str, Any]] = []

    def _sub(match: re.Match) -> str:
        attrs = dict(ATTR_RE.findall(match.group("attrs") or ""))
        body = match.group("body").strip()
        tc_id = attrs.get("id") or f"call_{uuid.uuid4().hex[:10]}"
        name = attrs.get("name") or ""
        # arguments must be a JSON-encoded string per OpenAI spec
        try:
            json.loads(body)
            args_str = body
        except json.JSONDecodeError:
            args_str = json.dumps({"_raw": body})
        tool_calls.append({
            "id": tc_id,
            "type": "function",
            "function": {"name": name, "arguments": args_str},
        })
        return ""

    cleaned = TOOL_CALL_RE.sub(_sub, text).strip()
    return cleaned, tool_calls


def parse_sse(raw: str) -> str:
    out: list[str] = []
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    for line in normalized.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        if obj.get("type") == "content_block_delta":
            delta = obj.get("delta") or {}
            if isinstance(delta, dict) and isinstance(delta.get("text"), str):
                out.append(delta["text"])
            continue
        if isinstance(obj.get("completion"), str):
            out.append(obj["completion"])
    return "".join(out)


# ───────────────────────── claude.ai network ─────────────────────────

CLAUDE_JS = """
async ({ url, body, deviceId }) => {
    const res = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Accept: 'text/event-stream',
            'anthropic-client-platform': 'web_claude_ai',
            'anthropic-device-id': deviceId,
        },
        body: JSON.stringify(body),
        credentials: 'include',
    });
    if (!res.ok) {
        return { ok: false, status: res.status, body: await res.text() };
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let full = '';
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        full += decoder.decode(value, { stream: true });
    }
    return { ok: true, status: 200, body: full };
}
"""

CREATE_CONVERSATION_JS = """
async ({ url, deviceId, convUuid }) => {
    const res = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'anthropic-client-platform': 'web_claude_ai',
            'anthropic-device-id': deviceId,
        },
        body: JSON.stringify({ name: 'hermes-zero-token ' + new Date().toISOString(), uuid: convUuid }),
        credentials: 'include',
    });
    return { ok: res.ok, status: res.status, body: res.ok ? await res.json() : await res.text() };
}
"""


async def claude_complete(prompt: str, model: str) -> str:
    _, page, auth = await SESSION.ensure()
    org = SESSION.org_id

    conv_uuid = str(uuid.uuid4())
    create_url = f"https://claude.ai/api/organizations/{org}/chat_conversations"
    created = await page.evaluate(
        CREATE_CONVERSATION_JS,
        {"url": create_url, "deviceId": auth["deviceId"], "convUuid": conv_uuid},
    )
    if not created["ok"]:
        raise RuntimeError(f"create_conversation failed: {created['status']}: {created['body']}")
    conv_id = created["body"]["uuid"]

    completion_url = (
        f"https://claude.ai/api/organizations/{org}/chat_conversations/{conv_id}/completion"
    )
    body = {
        "prompt": prompt,
        "parent_message_uuid": "00000000-0000-4000-8000-000000000000",
        "model": MODEL_ALIASES.get(model, model),
        "timezone": "Asia/Taipei",
        "rendering_mode": "messages",
        "attachments": [],
        "files": [],
        "locale": "en-US",
        "personalized_styles": [],
        "sync_sources": [],
        "tools": [],
    }
    LOG.info(
        "claude.ai completion: model=%s conv=%s prompt=%d chars",
        body["model"], conv_id, len(prompt),
    )
    result = await page.evaluate(
        CLAUDE_JS,
        {"url": completion_url, "body": body, "deviceId": auth["deviceId"]},
    )
    if not result["ok"]:
        raise RuntimeError(f"completion failed: {result['status']}: {result['body'][:500]}")
    text = parse_sse(result["body"])
    LOG.info("claude.ai response: %d chars: %r", len(text), text[:200])
    return text


# ───────────────────────── HTTP handlers ─────────────────────────

def _build_openai_chunk(cid: str, model: str, created: int, delta: dict[str, Any], finish: str | None) -> dict[str, Any]:
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
    tools = payload.get("tools") or []
    if not messages:
        return web.json_response(
            {"error": {"message": "messages required", "type": "invalid_request_error"}},
            status=400,
        )

    prompt = render_messages(messages, tools)
    try:
        raw_text = await claude_complete(prompt, model)
    except Exception as exc:
        LOG.exception("completion error")
        return web.json_response(
            {"error": {"message": str(exc), "type": "api_error"}}, status=500,
        )

    text, tool_calls = extract_text_and_tool_calls(raw_text)
    finish_reason = "tool_calls" if tool_calls else "stop"
    cid = f"chatcmpl-{uuid.uuid4()}"
    created = int(time.time())

    if tool_calls:
        LOG.info("emitting %d tool_calls; text_len=%d", len(tool_calls), len(text))

    if stream:
        resp = web.StreamResponse(status=200, headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        })
        await resp.prepare(request)

        # First chunk: role + any leading text content
        first_delta: dict[str, Any] = {"role": "assistant"}
        if text:
            first_delta["content"] = text
        if tool_calls:
            first_delta["tool_calls"] = [
                {
                    "index": i,
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    },
                }
                for i, tc in enumerate(tool_calls)
            ]
        await resp.write(
            f"data: {json.dumps(_build_openai_chunk(cid, model, created, first_delta, None))}\n\n".encode()
        )
        # Final chunk: stop reason
        await resp.write(
            f"data: {json.dumps(_build_openai_chunk(cid, model, created, {}, finish_reason))}\n\n".encode()
        )
        await resp.write(b"data: [DONE]\n\n")
        await resp.write_eof()
        return resp

    # Non-streaming response
    message: dict[str, Any] = {"role": "assistant", "content": text}
    if tool_calls:
        message["tool_calls"] = tool_calls
        if not text:
            message["content"] = None
    return web.json_response({
        "id": cid,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    })


async def handle_models(_request: web.Request) -> web.Response:
    return web.json_response({
        "object": "list",
        "data": [
            {"id": mid, "object": "model", "created": 0, "owned_by": "claude-web"}
            for mid in ("claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-6")
        ],
    })


async def handle_health(_request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "org_id": SESSION._org_id})


def build_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/v1/chat/completions", handle_chat_completions)
    app.router.add_get("/v1/models", handle_models)
    app.router.add_get("/health", handle_health)
    return app


def main() -> None:
    LOG.info("Starting claude-web Python proxy on %s:%d", LISTEN_HOST, LISTEN_PORT)
    LOG.info("Auth file: %s", AUTH_FILE)
    LOG.info("CDP URL: %s", CDP_URL)
    web.run_app(build_app(), host=LISTEN_HOST, port=LISTEN_PORT, print=None)


if __name__ == "__main__":
    main()
