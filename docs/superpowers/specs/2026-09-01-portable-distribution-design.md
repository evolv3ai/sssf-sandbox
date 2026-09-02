# Design: sssf-sandbox as the single portable SSSF distribution

Date: 2026-09-01. Status: draft for review.

## Goal

One public repo, `evolv3ai/sssf-sandbox`, that stamps a complete software factory with
sandboxes into any repository via skills: the upstream SSSF factory, the exe.dev sandbox
mount system, and the agent-facing skills that drive it, up to and including `sssf-admin`,
which owns a build end to end through herdr.

## Decisions already made (user, 2026-09-01)

| Question | Decision |
|---|---|
| Which sandbox surface do the skills drive | The upstream Inkwell `just sbx` surface (nested `lifecycle` / `manage` / `run` / `orch` modules, `sandbox_mount/`). The slim `sbx.py` rewrite in this repo is retired. |
| What is `evolv3ai/sssf-sandbox` | The portable skill-only distribution. |
| Where does `sssf-admin` live | Here, public. `evolv3ai/sssf-admin` (private) is archived after the merge. |
| Does `sssf-sandbox-orchestrator` replace `sssf-admin` | No. The orchestrator is disler's thin operator over the recipes. `sssf-admin` composes orchestrator + herdr + fleet ops on top. Both ship. |
| Inkwell fork | Stays as the lab and test target. Local dir renamed to `~/dev/inkwell-factory`. |
| Local squash of sssf-admin | Dropped. History kept. |
| `fusion-harness`, `~/dev/Fusion` | Out of scope. |

## Repo layout after this work

```
evolv3ai/sssf-sandbox
  .claude/skills/
    sssf/                        upstream SSSF, unchanged
    sssf-sandbox/                the installer (reworked)
      SKILL.md                   thin: install, doctor, then hand off to the orchestrator
      scripts/install.py
      templates/
        just/adws.just           vendored from inkwell; the VM runs `just adw <recipe>` in the clone
        just/sandbox/**          15 files, vendored from inkwell just/sandbox/; 3 parameterized
        sandbox_mount/
          host/run_record.py
          host/runs_table.py
          host/source_repo.py    new: resolves and validates the public clone URL
          guest/provision.sh     parameterized, see below
          guest/models.json.tmpl
        env.sample.fragment      OPENROUTER_PROVISIONING_KEY, SBX_SOURCE_REPO, SBX_TAG, SBX_APP_*
    sssf-sandbox-orchestrator/   vendored from inkwell (disler, 92f1701)
    herdr/                       vendored from inkwell (disler, 92f1701)
    sandbox-exe-dev/             vendored from inkwell (disler, 92f1701)
    sssf-admin/                  from evolv3ai/sssf-admin@8193762, wording generalized
  UPSTREAM.md                    source repo + commit for every vendored tree
  README.md  LICENSE  images/  docs/superpowers/specs/
```

Removed: `templates/sandbox/host/sbx.py`, `templates/sandbox/just/mod.just`,
`templates/sandbox/sssf.sandbox.config.yaml`. The upstream recipes read
`adws/adw_sssf_config/sssf.config.yaml`, which the `sssf` skill already stamps, so the
separate sandbox config file has no consumer.

## Installer behaviour

`uv run .claude/skills/sssf-sandbox/scripts/install.py [--force]`, run from the target repo root.

1. Run the sibling `sssf/scripts/install.py` (unchanged from today).
2. Stamp every sibling skill into `target/.claude/skills/`: `sssf`, `sssf-sandbox`,
   `sssf-sandbox-orchestrator`, `herdr`, `sandbox-exe-dev`, `sssf-admin`.
3. Stamp `templates/just` to `target/just` (the `adw` module plus `sandbox/`) and
   `templates/sandbox_mount` to `target/sandbox_mount`.
4. Append `mod adw 'just/adws.just'` and `mod sbx 'just/sandbox/mod.just'` to
   `target/justfile` once. Both modules carry their own `set working-directory`,
   `set dotenv-load` and `set positional-arguments`, so the root justfile needs nothing else.
   The `adw` module is required: `execute` runs `just adw <recipe>` inside the VM's clone
   and `doctor` checks `just --list adw` on the host.
5. Append `.sandbox/` and `.env` to `.gitignore` once, and the env fragment to `.env.sample` once.
6. Idempotent: existing files are skipped unless `--force`. Self-install into this repo's
   own root stays supported (the existing same-path guard).
7. Makes no VM, key, or model call.

## Parameterizing the four Inkwell-coupled spots

Verified by grep (`inkwell` outside comments): these are the only app-specific references
in the 20 vendored files. Every knob is read from `.env` via the modules' `dotenv-load`.

- `just/sandbox/lifecycle/fill.just` hardcodes the clone URL. It now calls
  `sandbox_mount/host/source_repo.py`, which returns `SBX_SOURCE_REPO` if set, else `origin`
  with the `git@github.com:` and `ssh://git@github.com/` forms rewritten to HTTPS, and exits
  non-zero for anything that is not `https://`. The VM clones anonymously, so the remote must
  be public. `doctor` runs `source_repo.py --probe`, an anonymous `git ls-remote`, so a
  private remote fails preflight instead of failing inside the VM.
- `just/sandbox/lifecycle/observe.just` starts the Inkwell app from `apps/inkwell` on 4501
  and proxies it publicly. It now reads `SBX_APP_DIR`, `SBX_APP_CMD` (default
  `bun run server.ts`) and `SBX_APP_PORT` (default `4501`). With `SBX_APP_DIR` unset there is
  no app: the trace UI on 4600 becomes the proxied port, it is not set public, and the
  verification accepts any reachable non-5xx answer. The recorded `ports` field then carries
  `"app": null`.
- `just/sandbox/lifecycle/create.just` tags every VM `inkwell`. It now uses
  `SBX_TAG`, default `sssf-sandbox`.
- `sandbox_mount/guest/provision.sh` step 5 loops over a hardcoded `apps/inkwell` plus the
  visualizer. It becomes: every `apps/*/package.json` found, plus the visualizer, keeping
  the existing skip-when-absent behaviour. A repo with no bun apps provisions cleanly.

The three evolv3ai fork fixes in inkwell (`71d0576` pi apiKey syntax, `57b0f10` mktemp
templates) are carried; `96db719` (fork clone URL) is superseded by the parameterization.

## Skill adaptation

- `sssf-sandbox/SKILL.md`: rewritten to cover install and preflight only, then point at
  `sssf-sandbox-orchestrator` for operation. Its flat `mount|execute|observe|...` command
  docs go away because those recipes no longer exist.
- `sssf-admin/SKILL.md`: description says "for the Factory-In-A-Box (sssf-sandbox) repo";
  generalize to "any repo where sssf-sandbox is installed". Its `just sbx ...`, `herdr`,
  `run_record.py` references are already correct for the stamped surface and stay.
- `sssf-sandbox-orchestrator`: vendored verbatim. Its references to `just/sandbox/` and
  the six phases hold because the tree is stamped at the same paths.
- `herdr`, `sandbox-exe-dev`: vendored verbatim.

## Verification

1. Install into a fresh `git init` directory: `just sbx` lists the nested recipes and
   `just sbx manage doctor` passes without a key (local, non-billable).
2. Install into `~/dev/inkwell-factory` itself: idempotent, only the parameterized files differ.
3. One real build on exe.dev through `sssf-admin` against a stamped throwaway repo: mount,
   execute a trivial prompt, harvest, teardown. Billable; teardown authorized by the user.
   This exercises herdr and the orchestrator on the stamped surface.
4. Re-run the `sssf-admin` evals (`evals.json` ships with the skill; the benchmark workspace
   stays in `~/dev/inkwell-factory/.claude/skills/sssf-admin-workspace/`).

## Repo operations and their owners

| Step | Owner |
|---|---|
| Work on branch `portable-distribution` in `~/dev/sssf-sandbox`, PR to `main` | agent |
| Push branch, merge PR | user |
| Archive `evolv3ai/sssf-admin`, delete `~/dev/sssf-admin` | user, after merge |
| Commit the `sssf-admin` skill into `~/dev/inkwell-factory` or leave untracked | user's call; the skill's canonical home is now this repo |

## Standing constraints

Never print, copy, or ssh keys. The provisioning key never leaves the host. Never run
`just adw` on the host. Never destroy VMs, keys, or run records without the user's word.
Force-pushes are run by the user.
