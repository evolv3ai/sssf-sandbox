---
name: sssf-sandbox
description: Install and operate the SSSF factory in isolated exe.dev VMs. Use for `/sssf-sandbox install`, preflight checks, sandbox mount/run/observe/harvest/teardown, or best-of-N isolated SSSF runs.
argument-hint: "[install|doctor|mount|execute|observe|harvest|teardown]"
---

# SSSF Sandbox

This skill adds an optional **out-of-sandbox** execution layer to Super Simple Software Factory (SSSF). The factory itself runs inside a disposable exe.dev VM; the host owns VM lifecycle and the OpenRouter provisioning credential.

## Install into a target repository

From the target repository root, with this skill present:

```bash
uv run .claude/skills/sssf-sandbox/scripts/install.py
```

The installer first stamps upstream SSSF, then stamps the sandbox module, guest provisioner, and host lifecycle runner. It is idempotent: existing files are skipped unless `--force` is supplied.

## Required host configuration

```bash
cp .env.sample .env
# Set OPENROUTER_PROVISIONING_KEY in .env. Never commit or print it.
just sbx doctor
```

`doctor` is local-only and non-billable. It validates file layout, required commands, source-repository resolution, and the guest model template. Use `just sbx doctor --remote` only when you intentionally want a read-only SSH connectivity check to exe.dev.

## Operation

```bash
just sbx mount my-task                 # billable: VM + capped runtime key; stops at observe
just sbx execute <run-id> "task"       # starts SSSF SDLC in that VM
just sbx observe <run-id>               # prints status and URLs
just sbx harvest <run-id>               # imports VM commits to refs/sandbox/<run-id>
just sbx teardown <run-id>              # destructive/billable cleanup; explicit human decision only
```

## Safety rules

1. `install` and `doctor` never create a VM, mint a runtime key, or call model APIs.
2. `mount` never tears down; it stops after the sandbox is ready.
3. Never run an SSSF write workflow on the host through this skill. Use `just sbx execute`.
4. Runtime keys are capped, written only to `.sandbox/runs/<id>.key` with mode 0600, and never printed.
5. Sandboxes have no Git credential. `harvest` transfers only the run branch via a git bundle into `refs/sandbox/<id>`.
6. `teardown` is always explicit. Harvest first, inspect the ref, then decide whether to keep or destroy the VM.

## Configuration

- `SBX_SOURCE_REPO`: HTTPS Git URL cloned inside each VM. Default: current `origin`, converted from GitHub SSH form when possible. It must be reachable unauthenticated by the VM.
- `SBX_LIMIT`: max USD for the temporary OpenRouter runtime key (default `50`).
- `SBX_TAG`: exe.dev tag used for the VM (default `sssf-sandbox`).

The default SSSF roster uses multiple providers. For the simplest sandbox setup, change the stamped roster to one OpenRouter-backed provider before mounting.

## Attribution

The sandbox architecture is adapted from `disler/inkwell-agent-sandboxes-and-software-factory` (MIT), but deliberately excludes the Inkwell application and its product-specific assets.
