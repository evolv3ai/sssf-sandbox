# Vendored trees

Every tree below is copied from a pinned commit. Refresh by re-copying from the
source at a newer commit, re-applying the listed local edits, and updating the row.

| Tree in this repo | Source | Commit | Local edits |
|---|---|---|---|
| `.claude/skills/sssf/` | `disler/super-simple-software-factory` | as of 2026-08-02 (`de31374` here) | none |
| `.claude/skills/sssf-sandbox/templates/just/adws.just` | `evolv3ai/inkwell-agent-sandboxes-and-software-factory` `just/adws.just` | `57b0f10` | none |
| `.claude/skills/sssf-sandbox/templates/just/sandbox/` | same repo, `just/sandbox/` | `57b0f10` | `lifecycle/fill.just` clone URL via `source_repo.py`; `lifecycle/observe.just` app knobs `SBX_APP_*`; `lifecycle/create.just` tag via `SBX_TAG`; `manage/mod.just` doctor probes the source repo |
| `.claude/skills/sssf-sandbox/templates/sandbox_mount/` | same repo, `sandbox_mount/` | `57b0f10` | `guest/provision.sh` step 5 globs `apps/*`; `host/source_repo.py` is new |
| `.claude/skills/sssf-sandbox-orchestrator/` | same repo | `57b0f10` (authored upstream by disler at `92f1701`) | none. Its cookbooks show port 4501 and run ids like `inkwell-e2e`; those are the defaults and examples, not requirements |
| `.claude/skills/herdr/` | same repo | `57b0f10` (disler `92f1701`) | none |
| `.claude/skills/sandbox-exe-dev/` | same repo | `57b0f10` (disler `92f1701`) | none |
| `.claude/skills/sssf-admin/` | `evolv3ai/sssf-admin` | `8193762` | `SKILL.md` description generalized away from the Inkwell repo |

The inkwell fork commit `57b0f10` = disler upstream `92f1701` plus `71d0576` (pi apiKey
syntax in `models.json.tmpl`), `96db719` (clone URL, superseded by `source_repo.py`),
`57b0f10` (GNU mktemp templates in `teardown.just` and `reap.just`).
