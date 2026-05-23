# zero-token — Claude Code subprocess proxy for Hermes Agent

A small OpenAI-compatible HTTP proxy that routes [`hermes-agent`](../README.md)'s LLM calls through your local **Claude Code** CLI (`claude -p`), backed by your Anthropic subscription (Pro / Max / Max-20x) — **no API tokens, no claude.ai-web sandbox restrictions**.

```
Telegram / Discord / CLI / WhatsApp
        │
        ▼  (hermes platform gateway)
┌────────────────────────────────┐
│   hermes-gateway.service       │
│   (NousResearch hermes-agent)  │
└────────────────┬───────────────┘
                 │  HTTP /v1/chat/completions
                 ▼  (provider=custom, base_url=http://127.0.0.1:3031/v1)
┌────────────────────────────────┐
│   claude-web-proxy.service     │  ← this folder
│   claude_code_proxy.py         │
└────────────────┬───────────────┘
                 │  subprocess
                 ▼
       claude -p --session-id <UUID>
              --dangerously-skip-permissions
              --append-system-prompt "<override>"
                 │  OAuth (~/.claude/.credentials.json)
                 ▼
            api.anthropic.com
```

## Why this exists

`hermes-agent` is great, but the default options for an Anthropic backend are:
- pay per-token via `ANTHROPIC_API_KEY` (defeats the point of a Claude subscription), or
- drive `claude.ai` web inside a headless browser (works but the web Claude frames itself as a sandboxed chatbot and refuses local-filesystem requests — "I can't access your machine").

This proxy gives a third option: spawn the local `claude` CLI per request. **Claude Code is "Claude running on your machine"** — it has Bash / Read / Write / Edit / Glob built in, knows it has filesystem access, and authenticates via the OAuth credentials Anthropic explicitly allows for that tool.

## What's in here

| File | Purpose |
| --- | --- |
| `claude_code_proxy.py` | The Python proxy (aiohttp). Spawns `claude -p` per request, manages a rolling session UUID, exposes `/v1/chat/completions`. **Current backend.** |
| `claude_web_proxy.py` | Earlier Playwright-based proxy that drove claude.ai web via Chrome CDP. **Superseded** by `claude_code_proxy.py` because of the sandbox-framing problem. Kept as a fallback reference. |
| `systemd/claude-web-proxy.service` | Template systemd user unit. Copy to `~/.config/systemd/user/` and adjust paths if your install differs. |
| `.env_local.example` | Template for hermes `.env` secrets (Telegram bot token, allowed users, etc.). Copy to `.env_local`, fill in real values, never commit. |

## Quick start

Prerequisites:
- `hermes-agent` installed (`curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash`)
- `claude` CLI installed and logged in (`claude` interactively at least once so `~/.claude/.credentials.json` is populated)
- Python 3.11+ available

### 1. Install the proxy

```bash
# venv (kept separate from hermes-agent venv to allow independent updates)
cd ~/.hermes/zero-token-runtime || mkdir -p ~/.hermes/zero-token-runtime && cd ~/.hermes/zero-token-runtime
python3.11 -m venv venv
./venv/bin/pip install aiohttp playwright
```

(The Playwright dep is only needed if you also want to keep `claude_web_proxy.py` as a fallback.  `claude_code_proxy.py` alone needs only `aiohttp`.)

### 2. Install the systemd user service

Copy `systemd/claude-web-proxy.service` to `~/.config/systemd/user/`, then edit `ExecStart` so it points to **your** venv python and **your** checkout of this file:

```ini
ExecStart=/home/<you>/.hermes/zero-token-runtime/venv/bin/python /home/<you>/.hermes/hermes-agent/zero-token/claude_code_proxy.py
```

Then:

```bash
systemctl --user daemon-reload
systemctl --user enable --now claude-web-proxy.service
curl -s http://127.0.0.1:3031/health
```

### 3. Point hermes-agent at the proxy

```bash
hermes config set model.provider custom
hermes config set model.base_url http://127.0.0.1:3031/v1
hermes config set model.default claude-sonnet-4-6
hermes config set model.api_key dummy   # proxy doesn't check it
systemctl --user restart hermes-gateway.service
```

### 4. Add a systemd drop-in so hermes waits for the proxy

```bash
mkdir -p ~/.config/systemd/user/hermes-gateway.service.d
cat > ~/.config/systemd/user/hermes-gateway.service.d/zero-token.conf <<'EOF'
[Unit]
Requires=claude-web-proxy.service
After=claude-web-proxy.service
EOF
systemctl --user daemon-reload
```

### 5. Test

```bash
hermes -z "what is the hostname of this machine?" --yolo
# expected: actual hostname, not "I'm in a sandbox"
```

## Endpoints

- `POST /v1/chat/completions` — OpenAI-compatible; passes the latest user message to `claude -p`. Supports `stream: true` (emits one synthetic delta chunk after the full response).
- `GET /v1/models` — lists model aliases this proxy reports.
- `GET /health` — `{"ok": true, "session_uuid": "...", "session_initialised": true|false}`
- `POST /reset` — drop the rolling session so the next request starts a fresh Claude Code conversation.

## Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `CLAUDE_PROXY_HOST` | `127.0.0.1` | bind address |
| `CLAUDE_PROXY_PORT` | `3031` | bind port |
| `CLAUDE_PROXY_MODEL` | `claude-sonnet-4-6` | model name reported back to OpenAI clients |
| `CLAUDE_BIN` | `/home/<you>/.local/bin/claude` | path to the `claude` binary |
| `CLAUDE_PROXY_WORKSPACE` | `$HOME` | cwd passed to `claude -p` |
| `CLAUDE_PROXY_SESSION_UUID` | `22222222-…-666666666666` | stable session UUID so calls continue one conversation |
| `CLAUDE_PROXY_TIMEOUT` | `600` (seconds) | hard per-request deadline. Long-running tool loops (PPT editing, repo searches, multi-step debugging) routinely exceed 180 s; the proxy emits SSE keepalive comments every 15 s so the client connection survives the full window. |

## Security notes

- The proxy spawns `claude --dangerously-skip-permissions`. **Anyone who can reach `:3031` (or your hermes gateway above it) can make Claude run arbitrary commands on this machine.** Bind to loopback (default), and lock down the upstream hermes channels:
  - Telegram: `TELEGRAM_ALLOWED_USERS=<your user id>` in `~/.hermes/.env`. **Do not** use `*`.
  - Other channels: see `hermes` docs for per-platform allowlists.
- `~/.claude/.credentials.json` is the OAuth token store — protect it like a password manager.
- All requests share one rolling Claude Code session. For multi-tenant or sensitive contexts, call `POST /reset` between users.

## Known limitations

- All inbound chats share one Claude Code conversation history. Multi-user / multi-topic isolation isn't implemented — `POST /reset` is your manual escape.
- Latency is ~10–30 s per turn (Claude Code may chain several tool calls before returning). Trade-off for correctness and real filesystem access.
- Hermes-side tool definitions in the OpenAI request are **ignored**; the proxy forwards only the latest user message. Claude Code uses its own toolbox.
- Streaming is faked — proxy waits for the full Claude Code result then emits one delta chunk. Real token streaming would need `claude --output-format stream-json` integration.

## Syncing with upstream hermes-agent

This repo is a fork of [`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent). To pull upstream changes later:

```bash
git fetch upstream
git merge upstream/main          # or rebase
# resolve conflicts (usually only in README.md if upstream re-edits it)
git push
```

All zero-token code lives in `zero-token/` and shouldn't touch upstream files, so merges should be conflict-free.
