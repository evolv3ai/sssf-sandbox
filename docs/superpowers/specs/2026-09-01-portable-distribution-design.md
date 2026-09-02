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
        just/sandbox/**          15 files, vendored from inkwell just/sandbox/
        sandbox_mount/
          host/run_record.py
          host/runs_table.py
          guest/provision.sh     parameterized, see below
          guest/models.json.tmpl
        env.sample.fragment      OPENROUTER_PROVISIONING_KEY, SBX_SOURCE_REPO
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
3. Stamp `templates/just/sandbox` to `target/just/sandbox` and `templates/sandbox_mount`
   to `target/sandbox_mount`.
4. Append `mod sbx 'just/sandbox/mod.just'` to `target/justfile` once. The sandbox
   `mod.just` carries its own `set working-directory`, `set dotenv-load` and
   `set positional-arguments`, so the root justfile needs nothing else.
5. Append `.sandbox/` and `.env` to `.gitignore` once, and the env fragment to `.env.sample` once.
6. Idempotent: existing files are skipped unless `--force`. Self-install into this repo's
   own root stays supported (the existing same-path guard).
7. Makes no VM, key, or model call.

## Parameterizing the two Inkwell-coupled spots

Verified by grep: the only app-specific references in the 19 vendored files are these two.

- `just/sandbox/lifecycle/fill.just` hardcodes the clone URL. It becomes
  `${SBX_SOURCE_REPO:-<origin as HTTPS>}`. The URL must stay a public HTTPS remote because
  the VM clones anonymously and no credential crosses. `doctor` fails if the resolved URL is
  not HTTPS or the remote is private.
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
