# sssf-sandbox

> **A portable distribution of the Super Simple Software Factory with throwaway exe.dev sandboxes and a build manager on top.**
> Six Claude Code skills, one installer, stamped into any repo.

> [!IMPORTANT]
> **This is a downstream distribution, not the original project.**
> The factory itself is [Super Simple Software Factory](https://github.com/disler/super-simple-software-factory)
> and the sandbox mount system is [Factory In A Box](https://github.com/disler/inkwell-agent-sandboxes-and-software-factory),
> both by **IndyDevDan ([disler](https://github.com/disler))** and both MIT licensed.
> This repo vendors those at pinned commits (see [`UPSTREAM.md`](UPSTREAM.md)), adds an installer that stamps
> everything together, and adds a build-manager skill. It is maintained by [evolv3ai](https://github.com/evolv3ai)
> and is not affiliated with or endorsed by the upstream author. For the concepts, the video walkthrough, and the
> canonical skill, go to the upstream repos.

---

## What this repo adds

Upstream ships the factory as one skill you stamp into a repo and run on your machine. Factory In A Box adds a
way to run that factory inside a disposable cloud VM instead, but ships it wrapped around a demo app. This
distribution pulls the two apart and packages only the reusable parts:

| Piece | Where it came from | What is different here |
|---|---|---|
| `sssf` skill | upstream SSSF, verbatim | pinned copy |
| `just sbx` lifecycle and manage recipes, `sandbox_mount/` | Factory In A Box, minus the Inkwell app | clone URL resolved from your remote, app knobs moved to `.env`, several lifecycle fixes listed in `UPSTREAM.md` |
| `sssf-sandbox-orchestrator`, `herdr`, `sandbox-exe-dev` skills | Factory In A Box, verbatim | pinned copies |
| `sssf-sandbox` skill and `install.py` | **new** | one idempotent installer stamps all six skills, both `just` modules, the host and guest helpers, `.env.sample`, and `.gitignore` entries |
| `sssf-admin` skill | **new** | a build manager that owns a build end to end: preflight, mount, execute, watch from herdr panes, harvest, spend report |
| `sandbox_mount/host/source_repo.py` | **new** | resolves and probes the anonymous clone URL the VM will use, so the preflight catches a private remote before any money is spent |
| `tests/` | **new** | 42 pytest cases covering the installer, the templates, and the source-repo probe |

## Quick start

Prerequisites on the host: [`uv`](https://docs.astral.sh/uv/), [`just`](https://github.com/casey/just), an
[exe.dev](https://exe.dev) account, an OpenRouter provisioning key, and a **public** GitHub remote. The `sssf-admin`
skill also wants [herdr](https://herdr.dev). Nothing else runs on the host. The factory, `pi`, and the model
calls all happen inside the VM.

```bash
git clone https://github.com/evolv3ai/sssf-sandbox /tmp/sssf-sandbox    # this distribution
cd /path/to/your/repo
cp -r /tmp/sssf-sandbox/.claude .                                       # all six skills
uv run .claude/skills/sssf-sandbox/scripts/install.py                   # stamp; idempotent, --force overwrites
cp .env.sample .env                                                     # set OPENROUTER_PROVISIONING_KEY
git add -A && git commit -m "Install SSSF sandbox" && git push          # the VM clones your public remote
just sbx manage doctor                                                  # preflight, non-billable
```

Green on `doctor` means the recipes are present, the provisioning key is set, and the VM will be able to clone
your repo anonymously. From there, in Claude Code:

```
/sssf-admin build "add a /health endpoint with a test"
```

or drive one sandbox by hand with the orchestrator skill: "mount a sandbox and run the sdlc chain on X".

## Three layers, each its own skill

| Layer | Skill | You say |
|---|---|---|
| the factory inside the VM | `sssf` | `just adw sdlc "…"` (only ever on the VM) |
| one VM's lifecycle: create, fill, setup, observe, execute, harvest, teardown, fan out N | `sssf-sandbox-orchestrator` | "mount a sandbox and run X" |
| a whole build managed for you from herdr panes, with a spend report | `sssf-admin` | "build X and clean up when done" |

`herdr` (the terminal multiplexer the manager drives) and `sandbox-exe-dev` (the exe.dev VM layer) ride along
as supporting skills. `sssf-sandbox` is the installer and preflight only. It never creates a VM, mints a key,
or calls a model.

## How a run works

1. `create` boots a tagged exe.dev VM.
2. `fill` clones your public remote into it.
3. `setup` runs the guest provisioner, mints a capped per-run OpenRouter key, and checks a five-assertion
   gate (git integrity, toolchain, key, factory smoke run, trace db). A failed gate leaves the VM alive for diagnosis.
4. `execute` runs an ADW chain detached inside the VM.
5. `observe` proxies either your app or the read-only trace UI to a public URL.
6. `harvest` pulls the run's commits back as a bundle under `refs/sandbox/<run-id>`.
7. `teardown` revokes the key, ships the trace db and sidecars, and destroys the VM.

Mounting is always explicit and billable: one VM plus one runtime key capped at $50 by default. Teardown is
never chained after mount or execute. Harvest first, look at the ref, then decide.

## `.env` knobs

| Key | Meaning | Default |
|---|---|---|
| `OPENROUTER_PROVISIONING_KEY` | mints and revokes the per-run runtime keys. Host only, never enters a VM | required |
| `SBX_SOURCE_REPO` | public https URL the VM clones | `origin`, with ssh forms rewritten to https |
| `SBX_TAG` | exe.dev tag on every VM this repo creates | `sssf-sandbox` |
| `SBX_APP_DIR` | app under development, relative to the clone root; empty means no app and the trace UI is proxied instead | empty |
| `SBX_APP_CMD` | how `observe` starts the app, run inside `SBX_APP_DIR` | `bun run server.ts` |
| `SBX_APP_PORT` | port the app binds; must bind `0.0.0.0` | `4501` |

## What gets stamped

```
your-repo/
├── .claude/skills/
│   ├── sssf/                       # the factory (upstream, verbatim)
│   ├── sssf-sandbox/               # this installer and its templates
│   ├── sssf-sandbox-orchestrator/  # one VM's six phases
│   ├── sssf-admin/                 # the build manager
│   ├── herdr/                      # pane multiplexer the manager drives
│   └── sandbox-exe-dev/            # exe.dev VM layer
├── just/
│   ├── adws.just                   # `just adw …`, one recipe per ADW, runs on the VM
│   └── sandbox/                    # `just sbx …`: lifecycle/, manage/, orch/, run/
├── sandbox_mount/
│   ├── host/                       # run records, runs table, source_repo.py
│   └── guest/                      # provision.sh and the pi model registry the VM uses
├── justfile                        # gains `mod adw` and `mod sbx`
├── .env.sample                     # gains the host-only sandbox block
└── .gitignore                      # gains .sandbox/, the visualizer build, run.log
```

The `sssf` installer inside the VM then stamps `adws/`, `sssf.config.yaml`, and the prompts the same way it
would on a laptop. The roster template shipped here routes every model through OpenRouter, because the VM
only ever holds one OpenRouter key.

## Tests

```bash
uv run --with pytest pytest
```

## Limitations

- **The remote must be public.** The VM clones over anonymous https. There is no credential forwarding by design, and `doctor` fails early if the probe cannot clone.
- **exe.dev only.** The VM layer is the `sandbox-exe-dev` skill. Nothing here targets another provider.
- **OpenRouter only inside the VM.** The per-run key is an OpenRouter key, so the roster must route through OpenRouter.
- **Sandboxes cost money.** Every mount creates a VM and a capped key. Nothing in `install` or `doctor` spends anything, and everything past that does.
- **Vendored, not tracked.** The upstream trees are copied at pinned commits. Pulling in a newer upstream is a manual re-copy plus re-applying the edits listed in `UPSTREAM.md`.

## Relationship to upstream

The upstream projects are the place to learn what a software factory is and why code, not the agent, should
own sequencing, retries, and acceptance. The [SSSF README](https://github.com/disler/super-simple-software-factory#readme)
covers the roster, phases, envelopes, gates, the trace, and the twelve starter workflows, and its `example`
branch holds a repo with real traces. There is a full [video breakdown](https://youtu.be/haUfb1ievTE) as well.
None of that is restated here.

This repo is not a GitHub fork. It began as a copy of the SSSF skill-only branch, had the Factory In A Box
sandbox surface copied in, and has diverged since. Every vendored tree, its source commit, and every local
edit is listed in [`UPSTREAM.md`](UPSTREAM.md).

## Credits

- **IndyDevDan ([disler](https://github.com/disler))** wrote the Super Simple Software Factory, the Factory In A Box sandbox system, and the `sssf`, `sssf-sandbox-orchestrator`, `herdr`, and `sandbox-exe-dev` skills. The diagrams in `images/` are his. His [YouTube channel](https://www.youtube.com/@indydevdan) and [Tactical Agentic Coding](https://agenticengineer.com/tactical-agentic-coding) course are where the ideas come from.
- **[herdr](https://herdr.dev)** and **[exe.dev](https://exe.dev)** are the tools the sandbox layer runs on.

## License

MIT. The upstream code is copyright IndyDevDan. The additions in this distribution are copyright evolv3ai.
Both are under the same MIT terms, see [`LICENSE`](LICENSE).
