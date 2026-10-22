# Open Duet (Open Dots) on Railway

Deploy the experimental [Open Duet](https://github.com/Anil-matcha/open-duet) personal AI workspace, formerly Open Dots. One owner can manage agents, chat, recurring routines, approvals and optional Telegram integration in a web interface.

## What this template adds

- Generated `APP_PASSWORD`, initialized through the application's own owner authentication before the HTTP server starts.
- A persistent `/data` volume for the SQLite database, attachments, decisions, workspaces and engine sign-ins.
- A generated `ENCRYPTION_SECRET` from which a valid Fernet key is derived. An explicitly supplied `TOKEN_ENCRYPTION_KEYS` takes precedence. Keep the secret stable and back it up separately from the volume.
- Unprivileged runtime after repairing the fresh volume's ownership.
- Claude Code and Codex CLIs installed at build time. Upstream also offers an OpenAI-compatible chat engine configured in **Settings → Engines**; deployment does not require a model key.
- Native `/api/v1/health` readiness check, one replica and graceful shutdown.

## First login and model setup

Open the generated Railway domain and sign in using `APP_PASSWORD` from the service variables. Initial bootstrap only sets a missing owner; restarting does not reset a password changed in the app. Configure an OpenAI-compatible endpoint, model and API key in **Settings → Engines**, or sign in to the installed Claude/Codex CLI on the server. Engine login and model API costs are separate from Railway hosting.

`LOCAL_EXECUTION_ENABLED=true` allows authenticated owner/device sessions to use the installed engines. `LOCAL_TOOLS_ENABLED=true` enables their workspace tools; upstream approvals still apply. Keep approval prompts enabled for tools. This is a single-owner service, not a multi-tenant sandbox.

## Persistence and updates

Use one replica. Keep `/data` attached, `ENCRYPTION_SECRET` unchanged and the generated domain or custom domain reflected in `OPEN_DOTS_PUBLIC_URL`, `FRONTEND_ORIGINS` and `TRUSTED_HOSTS`. The upstream migration command runs before every start. Back up the Railway volume and encryption secret before upgrades.

This build uses upstream commit `65b5f05e95377d247fbfb087dea52cc0bd4dc9bc`, Claude Code `2.1.308` and Codex `0.163.0`. The Dockerfile follows the upstream server image; `entrypoint.py` performs Railway owner bootstrap without modifying application auth or approval policies.

## Limits

Open Duet is experimental. This container has no Docker socket: per-agent Docker computers are unavailable. The OpenAI-compatible engine supports chat, not tool execution. Engine sign-in, Telegram tokens and other integrations must be configured by the owner. A successful health check verifies readiness, not the availability or billing status of an external model provider.

## License

Apache-2.0, following Open Duet. Original application copyright and license remain with its authors. This repository contains the Railway Docker recipe and bootstrap only; upstream source is downloaded from the pinned public commit during the build. No user credentials or private data are included.
