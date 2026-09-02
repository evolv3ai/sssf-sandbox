# Portable SSSF Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `evolv3ai/sssf-sandbox` stamp the complete factory-with-sandboxes into any repo: upstream SSSF, the Inkwell `just sbx` + `just adw` surface, and the `herdr`, `sssf-sandbox-orchestrator`, `sandbox-exe-dev` and `sssf-admin` skills.

**Architecture:** The `sssf-sandbox` skill is an installer. Its `templates/` hold verbatim copies of the Inkwell fork's `just/adws.just`, `just/sandbox/**` and `sandbox_mount/**`, with four Inkwell-specific spots turned into `.env` knobs (`SBX_SOURCE_REPO`, `SBX_TAG`, `SBX_APP_DIR`/`SBX_APP_CMD`/`SBX_APP_PORT`, and a glob in the provisioner). The three disler skills and `sssf-admin` are vendored as sibling skill directories and copied by the installer. `UPSTREAM.md` records where every vendored tree came from.

**Tech Stack:** Python 3.12 stdlib (installer, host helpers, tests via `uv run --with pytest`), `just` 1.46 modules, bash recipes, `uv` 0.11.

**Spec:** `docs/superpowers/specs/2026-09-01-portable-distribution-design.md`

## Global Constraints

- Work on branch `portable-distribution` in `/home/wsladmin/dev/sssf-sandbox`. The agent never pushes; the user pushes and merges.
- Source of vendored files: `/home/wsladmin/dev/inkwell-factory` at commit `57b0f10` (disler upstream `92f1701` plus three evolv3ai fixes).
- Vendored files are byte-identical to the source unless a task below names the edit.
- The provisioning key never leaves the host. Never print, copy, or ssh keys. Never run `just adw` on the host. Never create a VM, mint a key, or tear down without the user's word. Task 10 is the only billable task and is user-gated at every step.
- Tests run with `uv run --with pytest python -m pytest tests -q` from the repo root. `just` and `uv` are on PATH.
- Commit after every task with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01QuQzAJ5MmwHMsdW2pSpXHJ` as the last two lines of the message.

---

## File structure

```
.claude/skills/sssf-sandbox/
  SKILL.md                                  rewritten (Task 8)
  scripts/install.py                        rewritten (Task 2)
  templates/
    just/adws.just                          verbatim (Task 1)
    just/sandbox/mod.just, mount.just       verbatim (Task 1)
    just/sandbox/lifecycle/*.just           verbatim except fill (Task 4), observe (Task 5), create (Task 6)
    just/sandbox/manage/*.just              verbatim except doctor in mod.just (Task 4)
    just/sandbox/run/mod.just, orch/mod.just verbatim
    sandbox_mount/host/run_record.py        verbatim
    sandbox_mount/host/runs_table.py        verbatim
    sandbox_mount/host/source_repo.py       new (Task 3)
    sandbox_mount/guest/provision.sh        one loop edited (Task 7)
    sandbox_mount/guest/models.json.tmpl    verbatim
    env.sample.fragment                     new (Task 2)
.claude/skills/sssf-sandbox-orchestrator/   verbatim (Task 1)
.claude/skills/herdr/                       verbatim (Task 1)
.claude/skills/sandbox-exe-dev/             verbatim (Task 1)
.claude/skills/sssf-admin/                  from ~/dev/sssf-admin, description edited (Task 1)
UPSTREAM.md                                 new (Task 1)
README.md                                   sandbox section rewritten (Task 9)
tests/conftest.py                           new (Task 2)
tests/test_install.py                       new (Task 2)
tests/test_source_repo.py                   new (Task 3)
tests/test_templates.py                     new (Tasks 4-7)
```

Removed in Task 1: `.claude/skills/sssf-sandbox/templates/sandbox/` (five files of the slim rewrite).

---

### Task 1: Vendor the upstream surface verbatim

**Files:**
- Create: `.claude/skills/sssf-sandbox/templates/just/**`, `.claude/skills/sssf-sandbox/templates/sandbox_mount/**`
- Create: `.claude/skills/sssf-sandbox-orchestrator/**`, `.claude/skills/herdr/**`, `.claude/skills/sandbox-exe-dev/**`
- Create: `.claude/skills/sssf-admin/**` (from `/home/wsladmin/dev/sssf-admin/.claude/skills/sssf-admin`, 4 files; line 3 edited)
- Create: `UPSTREAM.md`
- Delete: `.claude/skills/sssf-sandbox/templates/sandbox/**`

**Interfaces:**
- Produces: template tree paths used by every later task, exactly as listed in File structure.

- [ ] **Step 1: Create the branch**

```bash
git switch -c portable-distribution
```

- [ ] **Step 2: Copy the trees**

```bash
cd /home/wsladmin/dev/sssf-sandbox
L=/home/wsladmin/dev/inkwell-factory
T=.claude/skills/sssf-sandbox/templates
git rm -rq $T/sandbox
mkdir -p $T/just $T/sandbox_mount
cp $L/just/adws.just $T/just/adws.just
cp -r $L/just/sandbox $T/just/sandbox
cp -r $L/sandbox_mount/host $L/sandbox_mount/guest $T/sandbox_mount/
for s in sssf-sandbox-orchestrator herdr sandbox-exe-dev; do cp -r $L/.claude/skills/$s .claude/skills/$s; done
cp -r /home/wsladmin/dev/sssf-admin/.claude/skills/sssf-admin .claude/skills/sssf-admin
find $T .claude/skills/herdr .claude/skills/sandbox-exe-dev .claude/skills/sssf-sandbox-orchestrator -name __pycache__ -prune -exec rm -rf {} +
```

- [ ] **Step 3: Verify byte-identical and exec bits preserved**

```bash
cd /home/wsladmin/dev/sssf-sandbox
L=/home/wsladmin/dev/inkwell-factory; T=.claude/skills/sssf-sandbox/templates
diff -r $L/just/sandbox $T/just/sandbox && diff $L/just/adws.just $T/just/adws.just && diff -r $L/sandbox_mount $T/sandbox_mount && echo TEMPLATES IDENTICAL
for s in sssf-sandbox-orchestrator herdr sandbox-exe-dev; do diff -r $L/.claude/skills/$s .claude/skills/$s && echo "$s IDENTICAL"; done
diff -r /home/wsladmin/dev/sssf-admin/.claude/skills/sssf-admin .claude/skills/sssf-admin && echo "sssf-admin IDENTICAL"
ls -l $T/sandbox_mount/host/run_record.py $T/sandbox_mount/host/runs_table.py $T/sandbox_mount/guest/provision.sh | awk '{print $1, $NF}'
```
Expected: three IDENTICAL lines for templates and one per skill (four skills); the three helpers show `-rwxr-xr-x`.

- [ ] **Step 3b: Generalize the sssf-admin description**

In `.claude/skills/sssf-admin/SKILL.md` line 3, replace
`Full-service build manager for the Factory-In-A-Box (sssf-sandbox) repo.`
with
`Full-service build manager for any repo where the sssf-sandbox distribution is installed (just sbx recipes, herdr, sssf-sandbox-orchestrator).`

Leave every other line alone: the `just sbx lifecycle/manage/run` calls, `herdr` usage and `run_record.py` paths are exactly what the installer stamps. Verify: `grep -c 'Factory-In-A-Box' .claude/skills/sssf-admin/SKILL.md` prints `0`.

- [ ] **Step 4: Write UPSTREAM.md**

```markdown
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
```

- [ ] **Step 5: Commit**

```bash
cd /home/wsladmin/dev/sssf-sandbox && git add -A && git commit -q -m "feat(sssf-sandbox): vendor the inkwell sbx/adw surface and disler skills verbatim

Replaces the slim sbx.py rewrite with the upstream just/sandbox recipes,
sandbox_mount helpers, and the herdr / orchestrator / sandbox-exe-dev skills.
Imports sssf-admin from evolv3ai/sssf-admin@8193762 with its description
generalized. UPSTREAM.md pins every source commit.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QuQzAJ5MmwHMsdW2pSpXHJ" && git log --oneline -1
```

---

### Task 2: Installer stamps the full surface

**Files:**
- Create: `tests/conftest.py`, `tests/test_install.py`
- Create: `.claude/skills/sssf-sandbox/templates/env.sample.fragment`
- Modify: `.claude/skills/sssf-sandbox/scripts/install.py` (full rewrite)

**Interfaces:**
- Consumes: template tree from Task 1.
- Produces: `install.py` with `SKILLS`, `MODULE_LINES`, `ENV_MARKER` constants; `tests/conftest.py` fixture `stamped_repo` (a `Path` to a git-initialised temp dir with the installer already run) that Tasks 3 to 7 reuse.

- [ ] **Step 1: Write the fixture and failing tests**

`tests/conftest.py`:
```python
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
INSTALL = REPO / ".claude" / "skills" / "sssf-sandbox" / "scripts" / "install.py"


def run_install(target: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["uv", "run", str(INSTALL), *args],
        cwd=target, capture_output=True, text=True, check=False,
    )


@pytest.fixture
def stamped_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "remote", "add", "origin", "git@github.com:acme/widgets.git"], cwd=tmp_path, check=True)
    result = run_install(tmp_path)
    assert result.returncode == 0, result.stderr
    return tmp_path
```

`tests/test_install.py`:
```python
import subprocess
from pathlib import Path

from conftest import run_install

SKILLS = ["sssf", "sssf-sandbox", "sssf-sandbox-orchestrator", "herdr", "sandbox-exe-dev", "sssf-admin"]


def test_stamps_every_skill(stamped_repo: Path):
    for skill in SKILLS:
        assert (stamped_repo / ".claude" / "skills" / skill / "SKILL.md").is_file(), skill


def test_stamps_just_modules_and_host_helpers(stamped_repo: Path):
    for rel in [
        "just/adws.just", "just/sandbox/mod.just", "just/sandbox/mount.just",
        "just/sandbox/lifecycle/fill.just", "just/sandbox/manage/mod.just",
        "just/sandbox/run/mod.just", "just/sandbox/orch/mod.just",
        "sandbox_mount/host/run_record.py", "sandbox_mount/host/runs_table.py",
        "sandbox_mount/guest/provision.sh", "sandbox_mount/guest/models.json.tmpl",
    ]:
        assert (stamped_repo / rel).is_file(), rel
    for rel in ["sandbox_mount/host/run_record.py", "sandbox_mount/guest/provision.sh"]:
        assert (stamped_repo / rel).stat().st_mode & 0o111, f"{rel} not executable"


def test_does_not_stamp_the_old_slim_runner(stamped_repo: Path):
    assert not (stamped_repo / "sandbox").exists()


def test_justfile_gets_both_modules_once(stamped_repo: Path):
    text = (stamped_repo / "justfile").read_text()
    assert text.count("mod adw 'just/adws.just'") == 1
    assert text.count("mod sbx 'just/sandbox/mod.just'") == 1


def test_env_sample_and_gitignore(stamped_repo: Path):
    env = (stamped_repo / ".env.sample").read_text()
    for key in ["OPENROUTER_PROVISIONING_KEY=", "SBX_SOURCE_REPO=", "SBX_TAG=", "SBX_APP_DIR=", "SBX_APP_CMD=", "SBX_APP_PORT="]:
        assert key in env, key
    assert ".sandbox/" in (stamped_repo / ".gitignore").read_text().splitlines()


def test_second_run_is_a_no_op(stamped_repo: Path):
    before = sorted(p.relative_to(stamped_repo) for p in stamped_repo.rglob("*") if ".git" not in p.parts)
    result = run_install(stamped_repo)
    assert result.returncode == 0, result.stderr
    assert "stamped: 0 file(s)" in result.stdout
    after = sorted(p.relative_to(stamped_repo) for p in stamped_repo.rglob("*") if ".git" not in p.parts)
    assert before == after
    assert (stamped_repo / "justfile").read_text().count("mod sbx") == 1


def test_just_lists_sbx_and_adw(stamped_repo: Path):
    sbx = subprocess.run(["just", "--list", "sbx"], cwd=stamped_repo, capture_output=True, text=True)
    assert sbx.returncode == 0, sbx.stderr
    for name in ["mount", "lifecycle", "manage", "run", "orch"]:
        assert name in sbx.stdout, name
    adw = subprocess.run(["just", "--list", "adw"], cwd=stamped_repo, capture_output=True, text=True)
    assert adw.returncode == 0, adw.stderr
    assert "sdlc" in adw.stdout


def test_refuses_when_a_sibling_skill_is_missing(tmp_path: Path):
    # Copy the distribution's skills minus herdr, run its installer from there.
    import shutil
    src = Path(__file__).resolve().parent.parent / ".claude" / "skills"
    dist = tmp_path / "dist"
    shutil.copytree(src, dist / ".claude" / "skills", ignore=shutil.ignore_patterns("herdr"))
    target = tmp_path / "target"
    target.mkdir()
    result = subprocess.run(
        ["uv", "run", str(dist / ".claude" / "skills" / "sssf-sandbox" / "scripts" / "install.py")],
        cwd=target, capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "herdr" in result.stderr
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/wsladmin/dev/sssf-sandbox && uv run --with pytest python -m pytest tests/test_install.py -q`
Expected: failures (the current installer stamps `sandbox/`, not `just/`; no `sssf-admin` skill yet). `test_refuses_when_a_sibling_skill_is_missing` fails because the old installer only checks for `sssf`.

- [ ] **Step 3: Write the env fragment**

`.claude/skills/sssf-sandbox/templates/env.sample.fragment`:
```
# ── sssf-sandbox (host only) ─────────────────────────────────────────────────
# Mints and revokes the capped per-run runtime keys. The only long-lived secret;
# it never enters a VM. openrouter.ai -> Keys -> Provisioning API Keys.
OPENROUTER_PROVISIONING_KEY=

# Public HTTPS URL the VM clones anonymously. Default: origin, with the
# git@github.com: and ssh://git@github.com/ forms rewritten to https.
SBX_SOURCE_REPO=

# exe.dev tag stamped on every VM this repo creates. Default: sssf-sandbox
SBX_TAG=

# The app under development, if any. observe starts it on the VM and proxies it
# publicly. Leave SBX_APP_DIR empty for "no app": the trace UI (4600) is proxied
# instead, auth-gated. Paths are relative to the clone root.
SBX_APP_DIR=
SBX_APP_CMD=bun run server.ts
SBX_APP_PORT=4501
```

- [ ] **Step 4: Rewrite install.py**

```python
#!/usr/bin/env -S uv run
# /// script
# dependencies = []
# ///
"""Stamp the SSSF factory plus its exe.dev sandbox surface into the current repo.

Run from the target repo root:
    uv run .claude/skills/sssf-sandbox/scripts/install.py [--force]

Stamps: the six operating skills, just/adws.just + just/sandbox/ (the `adw` and
`sbx` modules), sandbox_mount/ (host helpers + guest provisioner), two `mod`
lines in the justfile, .env.sample and .gitignore entries.
No VM, key, or model API call is made by this installer.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SKILLS_DIR = SKILL.parent
TEMPLATES = SKILL / "templates"

# Every skill the stamped repo needs. sssf-admin composes the orchestrator and
# herdr; the orchestrator drives the sbx recipes; sandbox-exe-dev is the VM layer.
SKILLS = ["sssf", "sssf-sandbox", "sssf-sandbox-orchestrator", "herdr", "sandbox-exe-dev", "sssf-admin"]
MODULE_LINES = ["mod adw 'just/adws.just'", "mod sbx 'just/sandbox/mod.just'"]
GITIGNORE = [".sandbox/"]
ENV_MARKER = "# ── sssf-sandbox (host only)"


def stamp(src: Path, dest: Path, force: bool, stamped: list[str], skipped: list[str]) -> None:
    # A cloned distribution can be installed into its own root; never copy a
    # file onto itself.
    if src.resolve() == dest.resolve():
        skipped.append(str(dest))
        return
    if src.is_dir():
        for child in sorted(src.iterdir()):
            if child.name in {"__pycache__", ".DS_Store"}:
                continue
            stamp(child, dest / child.name, force, stamped, skipped)
        return
    if dest.exists() and not force:
        skipped.append(str(dest))
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)  # copy2 keeps the exec bit on provision.sh and the host helpers
    stamped.append(str(dest))


def append_once(path: Path, marker: str, block: str) -> bool:
    existing = path.read_text() if path.exists() else ""
    if marker in existing:
        return False
    with path.open("a") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        handle.write(block)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite existing stamped files")
    args = parser.parse_args()
    root = Path.cwd().resolve()

    missing = [s for s in SKILLS if not (SKILLS_DIR / s / "SKILL.md").is_file()]
    if missing:
        print(f"Missing sibling skill(s) {', '.join(missing)} under {SKILLS_DIR}; "
              "clone the full sssf-sandbox distribution.", file=sys.stderr)
        return 2

    subprocess.run(["uv", "run", str(SKILLS_DIR / "sssf" / "scripts" / "install.py")], cwd=root, check=True)

    stamped: list[str] = []
    skipped: list[str] = []
    for skill in SKILLS:
        stamp(SKILLS_DIR / skill, root / ".claude" / "skills" / skill, args.force, stamped, skipped)
    stamp(TEMPLATES / "just", root / "just", args.force, stamped, skipped)
    stamp(TEMPLATES / "sandbox_mount", root / "sandbox_mount", args.force, stamped, skipped)

    if append_once(root / "justfile", MODULE_LINES[0],
                   "\n# in-sandbox ADWs and out-of-sandbox VM lifecycle (stamped by sssf-sandbox)\n"
                   + "\n".join(MODULE_LINES) + "\n"):
        stamped.append(f"{root / 'justfile'} (+ adw, sbx modules)")
    for entry in GITIGNORE:
        if append_once(root / ".gitignore", entry, f"\n# sssf-sandbox: run records, runtime keys, harvested bundles\n{entry}\n"):
            stamped.append(f"{root / '.gitignore'} (+ {entry})")
    if append_once(root / ".env.sample", ENV_MARKER, "\n" + (TEMPLATES / "env.sample.fragment").read_text()):
        stamped.append(f"{root / '.env.sample'} (+ sandbox settings)")

    print(f"sssf-sandbox installed into {root}")
    print(f"  stamped: {len(stamped)} file(s); skipped: {len(skipped)}")
    print("\nnext steps:")
    print("  1. cp .env.sample .env       # set OPENROUTER_PROVISIONING_KEY; SBX_* as needed")
    print("  2. just sbx manage doctor    # preflight: ssh, key, source repo, adw layer")
    print("  3. git add -A && git commit -m 'Install SSSF sandbox'   # the VM clones what is pushed")
    print("  4. just sbx mount <run-id>   # explicit, billable")
    print("  or hand the whole build to the manager: /sssf-admin build \"<what to build>\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/wsladmin/dev/sssf-sandbox && uv run --with pytest python -m pytest tests/test_install.py -q`
Expected: 8 passed.

Note on `test_just_lists_sbx_and_adw`: the `sssf` starter justfile has `set dotenv-load`; the two modules set their own. If `just --list sbx` errors with "duplicate setting", the module line was appended inside the sssf justfile scope incorrectly; check the justfile tail.

- [ ] **Step 6: Commit**

```bash
cd /home/wsladmin/dev/sssf-sandbox && git add -A && git commit -q -m "feat(sssf-sandbox): installer stamps the full sbx/adw surface and all six skills

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QuQzAJ5MmwHMsdW2pSpXHJ"
```

---

### Task 3: `source_repo.py` resolves the public clone URL

**Files:**
- Create: `.claude/skills/sssf-sandbox/templates/sandbox_mount/host/source_repo.py` (mode 755)
- Create: `tests/test_source_repo.py`

**Interfaces:**
- Produces: CLI `sandbox_mount/host/source_repo.py` printing the HTTPS URL on stdout, exit 0; exit 1 with a message on stderr when unresolvable or not `https://`. `--probe` additionally runs an anonymous `git ls-remote --heads` and exits 1 if it fails. Env `SBX_SOURCE_REPO` overrides origin. Used by Task 4.

- [ ] **Step 1: Write the failing tests**

`tests/test_source_repo.py`:
```python
import os
import subprocess
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parent.parent / ".claude/skills/sssf-sandbox/templates/sandbox_mount/host/source_repo.py")


def git_repo(tmp_path: Path, origin: str | None) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    if origin:
        subprocess.run(["git", "remote", "add", "origin", origin], cwd=tmp_path, check=True)
    return tmp_path


def resolve(cwd: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    full_env = {k: v for k, v in os.environ.items() if k != "SBX_SOURCE_REPO"}
    full_env.update(env or {})
    return subprocess.run([str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True, env=full_env)


def test_env_override_wins(tmp_path):
    repo = git_repo(tmp_path, "git@github.com:acme/widgets.git")
    r = resolve(repo, env={"SBX_SOURCE_REPO": "https://example.com/x/y.git"})
    assert r.returncode == 0 and r.stdout.strip() == "https://example.com/x/y.git"


def test_scp_style_github_origin_becomes_https(tmp_path):
    repo = git_repo(tmp_path, "git@github.com:acme/widgets.git")
    r = resolve(repo)
    assert r.returncode == 0 and r.stdout.strip() == "https://github.com/acme/widgets.git"


def test_ssh_url_github_origin_becomes_https(tmp_path):
    repo = git_repo(tmp_path, "ssh://git@github.com/acme/widgets.git")
    r = resolve(repo)
    assert r.returncode == 0 and r.stdout.strip() == "https://github.com/acme/widgets.git"


def test_https_origin_passes_through(tmp_path):
    repo = git_repo(tmp_path, "https://github.com/acme/widgets")
    r = resolve(repo)
    assert r.returncode == 0 and r.stdout.strip() == "https://github.com/acme/widgets"


def test_non_https_is_rejected(tmp_path):
    repo = git_repo(tmp_path, "git@gitlab.example.com:acme/widgets.git")
    r = resolve(repo)
    assert r.returncode == 1 and "https://" in r.stderr and "SBX_SOURCE_REPO" in r.stderr


def test_no_origin_is_rejected(tmp_path):
    repo = git_repo(tmp_path, None)
    r = resolve(repo)
    assert r.returncode == 1 and "origin" in r.stderr


def test_probe_fails_on_unreachable_remote(tmp_path):
    repo = git_repo(tmp_path, "https://127.0.0.1:9/acme/widgets.git")
    r = resolve(repo, "--probe")
    assert r.returncode == 1 and "anonymous" in r.stderr
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/wsladmin/dev/sssf-sandbox && uv run --with pytest python -m pytest tests/test_source_repo.py -q`
Expected: every test errors with "No such file or directory" for the script.

- [ ] **Step 3: Write source_repo.py**

```python
#!/usr/bin/env python3
"""Resolve the public HTTPS URL a sandbox VM clones.

    sandbox_mount/host/source_repo.py            -> prints the URL, exit 0
    sandbox_mount/host/source_repo.py --probe    -> also proves it clones anonymously

SBX_SOURCE_REPO (from .env, loaded by the just module) wins. Otherwise `origin`,
with GitHub's git@ and ssh:// forms rewritten to https. Anything that is not
https:// is refused: the VM has no credential, so only an anonymous clone can work.
"""
from __future__ import annotations

import os
import subprocess
import sys

SCP_PREFIX = "git@github.com:"
SSH_PREFIX = "ssh://git@github.com/"


def resolve() -> str:
    url = os.environ.get("SBX_SOURCE_REPO", "").strip()
    if not url:
        proc = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
        if proc.returncode != 0:
            raise SystemExit("source_repo: no SBX_SOURCE_REPO and no git remote 'origin' — set SBX_SOURCE_REPO in .env")
        url = proc.stdout.strip()
    if url.startswith(SCP_PREFIX):
        url = "https://github.com/" + url[len(SCP_PREFIX):]
    elif url.startswith(SSH_PREFIX):
        url = "https://github.com/" + url[len(SSH_PREFIX):]
    if not url.startswith("https://"):
        raise SystemExit(f"source_repo: '{url}' is not an https:// URL the VM can clone anonymously — set SBX_SOURCE_REPO in .env")
    return url


def probe(url: str) -> None:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="/bin/false")
    proc = subprocess.run(["git", "ls-remote", "--heads", url], capture_output=True, text=True, env=env, timeout=60)
    if proc.returncode != 0:
        raise SystemExit(f"source_repo: anonymous clone of {url} would fail (is the repo public?):\n{proc.stderr.strip()}")


def main(argv: list[str]) -> int:
    url = resolve()
    if "--probe" in argv:
        probe(url)
    print(url)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit as exc:
        if isinstance(exc.code, str):
            print(exc.code, file=sys.stderr)
            sys.exit(1)
        raise
```

Then: `chmod 755 .claude/skills/sssf-sandbox/templates/sandbox_mount/host/source_repo.py`

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/wsladmin/dev/sssf-sandbox && uv run --with pytest python -m pytest tests/test_source_repo.py -q`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
cd /home/wsladmin/dev/sssf-sandbox && git add -A && git commit -q -m "feat(sssf-sandbox): source_repo.py resolves and probes the anonymous clone URL

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QuQzAJ5MmwHMsdW2pSpXHJ"
```

---

### Task 4: `fill.just` and `doctor` use `source_repo.py`

**Files:**
- Modify: `.claude/skills/sssf-sandbox/templates/just/sandbox/lifecycle/fill.just:19-22`
- Modify: `.claude/skills/sssf-sandbox/templates/just/sandbox/manage/mod.just:29-34`
- Create: `tests/test_templates.py`

**Interfaces:**
- Consumes: `sandbox_mount/host/source_repo.py` from Task 3.

- [ ] **Step 1: Write the failing tests**

`tests/test_templates.py`:
```python
import re
import subprocess
from pathlib import Path

T = Path(__file__).resolve().parent.parent / ".claude/skills/sssf-sandbox/templates"


def non_comment_lines(path: Path) -> list[str]:
    return [l for l in path.read_text().splitlines() if not l.strip().startswith("#")]


def test_no_inkwell_reference_outside_comments():
    hits = []
    for path in list((T / "just").rglob("*.just")) + list((T / "sandbox_mount").rglob("*")):
        if path.is_file():
            hits += [f"{path.name}: {l}" for l in non_comment_lines(path) if "inkwell" in l.lower()]
    assert hits == [], hits


def test_fill_resolves_repo_through_source_repo():
    body = "\n".join(non_comment_lines(T / "just/sandbox/lifecycle/fill.just"))
    assert 'REPO=$(sandbox_mount/host/source_repo.py)' in body
    assert "https://github.com/evolv3ai" not in body


def test_doctor_probes_the_source_repo():
    body = (T / "just/sandbox/manage/mod.just").read_text()
    assert "source_repo.py --probe" in body


def test_recipes_parse(stamped_repo: Path):
    for mod in ["sbx", "sbx::lifecycle", "sbx::manage", "sbx::run", "sbx::orch", "adw"]:
        r = subprocess.run(["just", "--list", mod], cwd=stamped_repo, capture_output=True, text=True)
        assert r.returncode == 0, f"{mod}: {r.stderr}"


def test_fill_dry_run_shows_source_repo_call(stamped_repo: Path):
    r = subprocess.run(["just", "--dry-run", "sbx", "lifecycle", "fill", "run-x"], cwd=stamped_repo, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "source_repo.py" in r.stderr + r.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/wsladmin/dev/sssf-sandbox && uv run --with pytest python -m pytest tests/test_templates.py -q`
Expected: `test_no_inkwell_reference_outside_comments`, `test_fill_resolves_repo_through_source_repo`, `test_doctor_probes_the_source_repo`, `test_fill_dry_run_shows_source_repo_call` fail; `test_recipes_parse` passes.

- [ ] **Step 3: Edit fill.just**

Replace lines 19 to 22 (the comment block and `REPO=...`) with:
```bash
    # The VM clones anonymously: no auth, no GitHub integration, no exe.dev git
    # integration cross the wire. source_repo.py returns SBX_SOURCE_REPO from .env
    # if set, else origin rewritten to https, and refuses anything that is not
    # https:// — a private or ssh-only remote fails here, on the host, with a
    # message, instead of inside the VM with a credential prompt nobody can answer.
    REPO=$(sandbox_mount/host/source_repo.py)
```

- [ ] **Step 4: Edit doctor in manage/mod.just**

After the line `chk "provisioner present" ...` add:
```bash
    chk "source repo resolves + clones anonymously" 'sandbox_mount/host/source_repo.py --probe'
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/wsladmin/dev/sssf-sandbox && uv run --with pytest python -m pytest tests/test_templates.py -q`
Expected: `test_no_inkwell_reference_outside_comments` still fails (observe, create, provision are Tasks 5 to 7); the other four pass.

- [ ] **Step 6: Commit**

```bash
cd /home/wsladmin/dev/sssf-sandbox && git add -A && git commit -q -m "feat(sssf-sandbox): fill clones SBX_SOURCE_REPO or origin-as-https; doctor probes it

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QuQzAJ5MmwHMsdW2pSpXHJ"
```

---

### Task 5: `observe.just` takes the app from `.env`

**Files:**
- Modify: `.claude/skills/sssf-sandbox/templates/just/sandbox/lifecycle/observe.just`
- Modify: `tests/test_templates.py` (append)

- [ ] **Step 1: Add the failing tests**

Append to `tests/test_templates.py`:
```python
def test_observe_reads_app_knobs_from_env():
    body = "\n".join(non_comment_lines(T / "just/sandbox/lifecycle/observe.just"))
    for knob in ["SBX_APP_DIR", "SBX_APP_CMD", "SBX_APP_PORT"]:
        assert knob in body, knob
    assert "apps/inkwell" not in body
    assert "server.ts" in body  # default command is still bun run server.ts


def test_observe_dry_run_parses(stamped_repo: Path):
    r = subprocess.run(["just", "--dry-run", "sbx", "lifecycle", "observe", "run-x"], cwd=stamped_repo, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    script = r.stderr + r.stdout
    assert "SBX_APP_DIR" in script
    chk = subprocess.run(["bash", "-n"], input=script, capture_output=True, text=True)
    assert chk.returncode == 0, chk.stderr
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/wsladmin/dev/sssf-sandbox && uv run --with pytest python -m pytest tests/test_templates.py -q -k observe`
Expected: both fail (`SBX_APP_DIR` absent).

- [ ] **Step 3: Rewrite the app-specific parts of observe.just**

Replace lines 33 to 39 with:
```bash
    # The app under development, from .env (dotenv-load on the lifecycle module).
    # Empty SBX_APP_DIR means "no app": the trace UI becomes the proxied port and
    # stays auth-gated. Paths are relative to the clone root on the VM, which is
    # `app` under the exedev user's home; expanded on the VM, not here.
    APP_REL="${SBX_APP_DIR:-}"
    APP_CMD="${SBX_APP_CMD:-bun run server.ts}"
    APP_PORT="${SBX_APP_PORT:-4501}"
    OBS_PORT=4600
    APP_DIR="\$HOME/app/${APP_REL}"
    OBS_DIR='$HOME/app/.claude/skills/sssf/apps/visualizer'
    OBS_DB='$HOME/app/adws/adw_data/sssf.db'
```

Replace the step-1 block (lines 73 to 91, `# ── 1. inkwell app on 4501` through its closing `fi`) with:
```bash
    # ── 1. the app, if configured ─────────────────────────────────────────────
    # Idempotent: observe is safe to re-run, and `just sbx mount` ends here, so a
    # second call must not stack a second server on the same port.
    if [ -z "$APP_REL" ]; then
        echo "[2/6] app  none (SBX_APP_DIR unset) — the trace UI will be the proxied port"
    else
        echo "[2/6] app  :$APP_PORT  ($APP_REL: $APP_CMD)"
        if listening "$APP_PORT"; then
            echo "       already listening — leaving it alone"
        else
            # All three detachment pieces are REQUIRED or ssh never returns: nohup
            # (survive session end), the redirect (release stdout/stderr), and
            # < /dev/null (release stdin). Dropping any one hangs this recipe.
            ssh "$HOST" "cd $APP_DIR && ( nohup $APP_CMD > \$HOME/app-server.log 2>&1 < /dev/null & echo \$! )" \
                | sed 's/^/       started pid /'
            if ! wait_listen "$APP_PORT"; then
                echo "observe: app never bound :$APP_PORT — tail of ~/app-server.log:" >&2
                ssh "$HOST" 'tail -n 40 $HOME/app-server.log' >&2 || true
                exit 1
            fi
            echo "       up"
        fi
    fi
```

Replace the proxy block (lines 125 to 131) with:
```bash
    # ── 3. proxy ─────────────────────────────────────────────────────────────
    # MANDATORY. A fresh exeuntu VM proxies port 8000 (smallest EXPOSEd port
    # >= 1024); without this retarget https://$HOST/ hits nothing. With an app,
    # it is the primary port and goes public. Without one, the trace UI is the
    # primary port and stays owner-gated: traces are not for anonymous eyes.
    if [ -n "$APP_REL" ]; then
        echo "[4/6] proxy -> :$APP_PORT, public"
        ssh exe.dev share port "$VM" "$APP_PORT"
        ssh exe.dev share set-public "$VM"
    else
        echo "[4/6] proxy -> :$OBS_PORT, owner-gated"
        ssh exe.dev share port "$VM" "$OBS_PORT"
    fi
```

Replace the record line (line 135) with:
```bash
    if [ -n "$APP_REL" ]; then
        "$RR" set {{RUN_ID}} "ports={\"app\":$APP_PORT,\"obs\":$OBS_PORT}"
    else
        "$RR" set {{RUN_ID}} "ports={\"app\":null,\"obs\":$OBS_PORT}"
    fi
```

Replace the verify block from `# The public flag can lag` (line 145) through `echo "       app  200 anonymous"` (line 157) with:
```bash
    if [ -n "$APP_REL" ]; then
        # The public flag can lag the API call by a beat; retry before failing.
        APP_CODE=000
        for _ in 1 2 3 4 5 6; do
            APP_CODE=$(code_of "https://$HOST/")
            [ "$APP_CODE" = "200" ] && break
            sleep 2
        done
        if [ "$APP_CODE" != "200" ]; then
            echo "observe: app returned $APP_CODE anonymously at https://$HOST/ (want 200)" >&2
            echo "         VM left up. Check: ssh exe.dev share show $VM" >&2
            exit 1
        fi
        echo "       app  200 anonymous"
    else
        ROOT_CODE=$(code_of "https://$HOST/")
        if [ "$ROOT_CODE" = "000" ] || [ "$ROOT_CODE" -ge 500 ]; then
            echo "observe: proxied trace UI unreachable at https://$HOST/ (got $ROOT_CODE)" >&2
            exit 1
        fi
        echo "       root $ROOT_CODE anonymous — expected, the trace UI is owner-gated"
    fi
```

Replace the final URL banner (lines 169 to 176) with:
```bash
    echo ""
    echo "════════════════════════════════════════════════════════════"
    if [ -n "$APP_REL" ]; then
        echo "  app  https://$HOST/"
        echo "  obs  https://$HOST:$OBS_PORT/"
    else
        echo "  obs  https://$HOST/   (also https://$HOST:$OBS_PORT/)"
    fi
    echo "════════════════════════════════════════════════════════════"
    echo "  The obs URL opens fine in a browser already signed in to exe.dev."
    echo "  Ports 3000-9999 are auto-forwarded by the proxy but auth-gated;"
    echo "  only ONE port can ever be anonymous, and that is the app port."
```

Also update the recipe's doc comment (line 17) to: `# Phase 5 · start the app (if SBX_APP_DIR) and the trace UI, expose one port, print the URLs`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/wsladmin/dev/sssf-sandbox && uv run --with pytest python -m pytest tests/test_templates.py -q -k observe`
Expected: 2 passed. If `bash -n` reports an error, the dry-run text includes just's `#!/usr/bin/env bash` line and the recipe body; check quoting around `$APP_DIR` (it must expand `\$HOME` on the VM, so the backslash stays).

- [ ] **Step 5: Commit**

```bash
cd /home/wsladmin/dev/sssf-sandbox && git add -A && git commit -q -m "feat(sssf-sandbox): observe starts/proxies the app named by SBX_APP_DIR, or the trace UI

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QuQzAJ5MmwHMsdW2pSpXHJ"
```

---

### Task 6: `create.just` tags VMs with `SBX_TAG`

**Files:**
- Modify: `.claude/skills/sssf-sandbox/templates/just/sandbox/lifecycle/create.just:84-85`
- Modify: `tests/test_templates.py` (append)

- [ ] **Step 1: Add the failing test**

```python
def test_create_uses_sbx_tag():
    body = "\n".join(non_comment_lines(T / "just/sandbox/lifecycle/create.just"))
    assert '--tag "$TAG"' in body
    assert 'TAG="${SBX_TAG:-sssf-sandbox}"' in body
    assert "--tag inkwell" not in body
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /home/wsladmin/dev/sssf-sandbox && uv run --with pytest python -m pytest tests/test_templates.py -q -k create`
Expected: FAIL.

- [ ] **Step 3: Edit create.just**

Replace lines 84 and 85 with:
```bash
    TAG="${SBX_TAG:-sssf-sandbox}"   # exe.dev tag, from .env; lets `ssh exe.dev ls` group this repo's VMs
    echo "vm:      creating $RUN_ID (ssh exe.dev new --tag $TAG) ..."
    VM_JSON="$(ssh exe.dev new --name "$RUN_ID" --tag "$TAG" --json)"
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /home/wsladmin/dev/sssf-sandbox && uv run --with pytest python -m pytest tests/test_templates.py -q -k create`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/wsladmin/dev/sssf-sandbox && git add -A && git commit -q -m "feat(sssf-sandbox): VM tag comes from SBX_TAG, default sssf-sandbox

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QuQzAJ5MmwHMsdW2pSpXHJ"
```

---

### Task 7: `provision.sh` installs every bun app it finds

**Files:**
- Modify: `.claude/skills/sssf-sandbox/templates/sandbox_mount/guest/provision.sh:103-112`
- Modify: `tests/test_templates.py` (append)

- [ ] **Step 1: Add the failing tests**

```python
def test_provision_globs_apps():
    body = "\n".join(non_comment_lines(T / "sandbox_mount/guest/provision.sh"))
    assert "apps/inkwell" not in body
    assert "apps/*/package.json" in body
    chk = subprocess.run(["bash", "-n", str(T / "sandbox_mount/guest/provision.sh")], capture_output=True, text=True)
    assert chk.returncode == 0, chk.stderr


def test_provision_step5_runs_with_no_apps(tmp_path: Path):
    # Extract step 5 and run it in a repo with no apps/ and no visualizer: must
    # print two skips and exit 0, and must not leave a literal "apps/*" behind.
    src = (T / "sandbox_mount/guest/provision.sh").read_text()
    start = src.index("# ── 5. bun install")
    end = src.index("# ── 6.")
    snippet = "set -euo pipefail\nstep(){ echo \"-- $1\"; }\nsay(){ echo \"   $*\"; }\n" + src[start:end]
    r = subprocess.run(["bash", "-c", snippet], cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "apps/*" not in r.stdout
    assert "skipped" in r.stdout
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /home/wsladmin/dev/sssf-sandbox && uv run --with pytest python -m pytest tests/test_templates.py -q -k provision`
Expected: both FAIL.

- [ ] **Step 3: Edit step 5 in provision.sh**

Replace lines 103 to 112 with:
```bash
# ── 5. bun install ───────────────────────────────────────────────────────────
# Every bun app the repo carries under apps/, plus the trace UI. A repo with no
# bun apps only installs the visualizer; one with none of either just skips.
step "5/9 bun install"
shopt -s nullglob
app_manifests=(apps/*/package.json)
shopt -u nullglob
if [[ ${#app_manifests[@]} -eq 0 ]]; then
  say "skipped apps/ (no apps/*/package.json)"
fi
for manifest in "${app_manifests[@]}" .claude/skills/sssf/apps/visualizer/package.json; do
  dir="${manifest%/package.json}"
  if [[ -f "$manifest" ]]; then
    ( cd "$dir" && bun install )
    say "installed ${dir}"
  else
    say "skipped ${dir} (no package.json)"
  fi
done
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd /home/wsladmin/dev/sssf-sandbox && uv run --with pytest python -m pytest tests/test_templates.py -q`
Expected: every test in the file passes, including `test_no_inkwell_reference_outside_comments` now that all four spots are parameterized.

- [ ] **Step 5: Commit**

```bash
cd /home/wsladmin/dev/sssf-sandbox && git add -A && git commit -q -m "feat(sssf-sandbox): provisioner installs apps/*/ bun apps instead of apps/inkwell

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QuQzAJ5MmwHMsdW2pSpXHJ"
```

---

### Task 8: Rewrite `sssf-sandbox/SKILL.md` as a thin installer skill

**Files:**
- Modify: `.claude/skills/sssf-sandbox/SKILL.md` (full rewrite)

- [ ] **Step 1: Write the new SKILL.md**

```markdown
---
name: sssf-sandbox
description: Install the Super Simple Software Factory plus its exe.dev sandbox surface into any repo, and run the non-billable preflight. Use for `/sssf-sandbox install`, "stamp the factory into this repo", "add sandboxes to sssf", or `just sbx manage doctor`. Operation (mount, execute, observe, harvest, teardown) belongs to sssf-sandbox-orchestrator; managed builds belong to sssf-admin.
argument-hint: "[install|doctor]"
---

# SSSF Sandbox — the installer

This skill stamps a complete factory-with-sandboxes into the current repo and stops.
It never creates a VM, mints a key, or calls a model.

## What gets stamped

| Into the target | What it is | Who drives it |
|---|---|---|
| `adws/`, `justfile`, `.env.sample` | upstream SSSF: deterministic ADWs, roster config | `sssf` skill |
| `just/adws.just` (`just adw …`) | in-sandbox execution layer, one recipe per ADW | the VM, via `execute` |
| `just/sandbox/` (`just sbx …`) | out-of-sandbox lifecycle: create, fill, setup, observe, execute, teardown; manage: list, harvest, reap, doctor | `sssf-sandbox-orchestrator` |
| `sandbox_mount/host/` | run records, runs table, source-repo resolution | the recipes |
| `sandbox_mount/guest/` | provisioner and pi model registry the VM runs | `setup` |
| `.claude/skills/{sssf, sssf-sandbox, sssf-sandbox-orchestrator, herdr, sandbox-exe-dev, sssf-admin}` | the six operating skills | you, next session |

## Install

From the target repo root, with this distribution's `.claude/skills/` present
(clone `evolv3ai/sssf-sandbox` and copy its `.claude/skills` in, or install into the clone itself):

```bash
uv run .claude/skills/sssf-sandbox/scripts/install.py          # idempotent; --force overwrites
cp .env.sample .env                                             # set OPENROUTER_PROVISIONING_KEY
git add -A && git commit -m "Install SSSF sandbox"              # the VM clones what is pushed
git push                                                        # the remote must be PUBLIC over https
just sbx manage doctor                                          # preflight, non-billable
```

## `.env` knobs the sandbox reads

| Key | Meaning | Default |
|---|---|---|
| `OPENROUTER_PROVISIONING_KEY` | mints/revokes the capped per-run runtime keys. Host only, never enters a VM | required |
| `SBX_SOURCE_REPO` | public https URL the VM clones | `origin`, git@/ssh:// GitHub forms rewritten to https |
| `SBX_TAG` | exe.dev tag on every VM this repo creates | `sssf-sandbox` |
| `SBX_APP_DIR` | app under development, relative to the clone root; empty = no app, the trace UI is proxied instead | empty |
| `SBX_APP_CMD` | how observe starts it, run inside `SBX_APP_DIR` | `bun run server.ts` |
| `SBX_APP_PORT` | port it binds (must bind 0.0.0.0) | `4501` |

## Then

- Operate one sandbox or fan out N: read `.claude/skills/sssf-sandbox-orchestrator/SKILL.md`.
- Hand a whole build over and get a report back: `/sssf-admin build "<what to build>"`.

## Hard rules

1. `install` and `doctor` never create a VM, mint a key, or call a model API.
2. The provisioning key never leaves the host. Never print, copy, or ssh it.
3. Never run an ADW on the host through this skill. Work happens inside a VM.
4. Teardown is a human decision, never chained after mount or execute.
```

- [ ] **Step 2: Verify the frontmatter parses and the skill lists**

Run: `cd /home/wsladmin/dev/sssf-sandbox && head -5 .claude/skills/sssf-sandbox/SKILL.md && python3 -c "import re,sys;t=open('.claude/skills/sssf-sandbox/SKILL.md').read();assert t.startswith('---\nname: sssf-sandbox\n');print('frontmatter ok')"`
Expected: `frontmatter ok`.

- [ ] **Step 2b: Run the full suite**

Run: `uv run --with pytest python -m pytest tests -q`
Expected: every test in `test_install.py`, `test_source_repo.py` and `test_templates.py` passes.

- [ ] **Step 3: Commit**

```bash
cd /home/wsladmin/dev/sssf-sandbox && git add -A && git commit -q -m "docs(sssf-sandbox): thin installer skill; operation lives in the orchestrator and sssf-admin

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QuQzAJ5MmwHMsdW2pSpXHJ"
```

---

### Task 9: README sandbox section

**Files:**
- Modify: `README.md:407-421` (the "SSSF Sandbox extension" section)

- [ ] **Step 1: Replace the section**

Replace everything from `## SSSF Sandbox extension` up to (not including) `## License` with:

```markdown
## Sandboxes, and a manager to run them

This distribution wraps the upstream factory with the sandbox mount system from
[Factory In A Box](https://github.com/disler/inkwell-agent-sandboxes-and-software-factory)
(MIT), minus the Inkwell app. One installer stamps all of it into your repo:

```bash
uv run .claude/skills/sssf-sandbox/scripts/install.py
cp .env.sample .env            # OPENROUTER_PROVISIONING_KEY, host only
git add -A && git commit -m "Install SSSF sandbox" && git push   # the VM clones your PUBLIC remote
just sbx manage doctor         # preflight, non-billable
```

Three layers, each its own skill:

| Layer | Skill | You say |
|---|---|---|
| the factory inside the VM | `sssf` | `just adw sdlc "…"` (never on the host) |
| one VM's lifecycle: mount, execute, observe, harvest, teardown, fan out N | `sssf-sandbox-orchestrator` | "mount a sandbox and run X" |
| a whole build managed for you from herdr panes, with a spend report | `sssf-admin` | "build X and clean up when done" |

`herdr` (the terminal multiplexer the manager drives) and `sandbox-exe-dev` (the exe.dev VM
layer) ride along. Vendored sources and pins are in [`UPSTREAM.md`](UPSTREAM.md).

Mounting is always explicit and billable: a VM plus a runtime key capped at $50 by default.
Teardown is never chained; harvest first, look at `refs/sandbox/<run-id>`, then decide.
`.env` knobs: `SBX_SOURCE_REPO`, `SBX_TAG`, `SBX_APP_DIR` / `SBX_APP_CMD` / `SBX_APP_PORT`
(set the app knobs only if the sandbox should start and expose a server; otherwise the trace UI
is what you get at the VM's URL).

```

- [ ] **Step 2: Check the README still renders as one document**

Run: `cd /home/wsladmin/dev/sssf-sandbox && grep -nE '^## ' README.md | tail -5`
Expected: `Sandboxes, and a manager to run them` appears once, directly before `License`.

- [ ] **Step 3: Commit**

```bash
cd /home/wsladmin/dev/sssf-sandbox && git add -A && git commit -q -m "docs: README describes the stamped sandbox surface and the three skill layers

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QuQzAJ5MmwHMsdW2pSpXHJ"
```

---

### Task 10: Verify against the lab, then one real build (user-gated)

**Files:** none in this repo. Produces evidence only.

- [ ] **Step 1: Force-install into a scratch copy of the Inkwell lab and diff**

The lab already carries the upstream surface, so a force install must change only the parameterized files plus the additions.

```bash
S=/tmp/claude-1002/-home-wsladmin-dev-sssf-sandbox/cd0feac1-d346-4b0c-b203-e0402a9461aa/scratchpad/inkwell-scratch
rm -rf "$S" && git clone -q /home/wsladmin/dev/inkwell-factory "$S"
cd "$S" && cp -r /home/wsladmin/dev/sssf-sandbox/.claude/skills/. .claude/skills/
uv run .claude/skills/sssf-sandbox/scripts/install.py --force
git status --porcelain | sort
```
Expected changed tracked files, and nothing else:
```
 M .env.sample
 M just/sandbox/lifecycle/create.just
 M just/sandbox/lifecycle/fill.just
 M just/sandbox/lifecycle/observe.just
 M just/sandbox/manage/mod.just
 M sandbox_mount/guest/provision.sh
?? .claude/skills/sssf-admin/
?? .claude/skills/sssf-sandbox/
?? sandbox_mount/host/source_repo.py
```
plus `M` lines under `.claude/skills/sssf/` where the two upstream snapshots differ (the lab's `sssf` is disler's Aug 9 copy, this repo's is the Aug 2 copy; `--force` overwrites). `.gitignore` and `justfile` must NOT appear: the lab already has `.sandbox/` and `mod adw 'just/adws.just'`, so both append_once markers match. If either shows as modified, fix the marker in `install.py`, not the lab. `adws/` must not appear either: the `sssf` installer is invoked without `--force`. Run `just sbx manage doctor` here: every check except the ssh and key lines should be `ok`, and `source repo` should be `ok` because the lab's origin is public.

- [ ] **Step 2: Hand the branch to the user**

Report the diff from Step 1 and stop. The user pushes `portable-distribution`, opens and merges the PR, and archives `evolv3ai/sssf-admin`. Nothing below runs until the user says so.

- [ ] **Step 3: Stamped throwaway target (user approves the repo creation)**

```bash
mkdir -p ~/dev/sbx-e2e && cd ~/dev/sbx-e2e && git init -q -b main
cp -r /home/wsladmin/dev/sssf-sandbox/.claude .
uv run .claude/skills/sssf-sandbox/scripts/install.py
cp .env.sample .env      # user fills OPENROUTER_PROVISIONING_KEY; leaves SBX_APP_DIR empty
git add -A && git commit -q -m "Install SSSF sandbox"
gh repo create evolv3ai/sbx-e2e --public --source . --push   # only after the user says yes
just sbx manage doctor
```
Expected: `sbx doctor: OK` including `source repo resolves + clones anonymously`.

- [ ] **Step 4: One managed build, teardown authorized in the request**

In `~/dev/sbx-e2e`, with herdr running, invoke the manager exactly as a user would:

`/sssf-admin build "add a file HELLO.md containing the single line hello, using the build workflow" and tear down when done`

Expected, per `sssf-admin`'s report format: mount succeeded with `[2/6] app  none (SBX_APP_DIR unset)` in the observe output and the VM URL answering owner-gated; execute ran `adw build`; harvest reports 1 commit bundled into `refs/sandbox/<run-id>`; teardown revoked the key; `just sbx manage list` shows the run closed; `ssh exe.dev ls` shows no VM with tag `sssf-sandbox`.

- [ ] **Step 5: Re-run the sssf-admin evals**

Billable: each eval mounts real VMs. Only with the user's go-ahead. Use the `skill-creator:skill-creator` skill's benchmark mode, the same tooling that produced the two earlier iterations:

- skill under test: `/home/wsladmin/dev/sssf-sandbox/.claude/skills/sssf-admin`
- evals: its own `evals.json` (ids 0, 1, 2: full build with authorized teardown, fleet reconciliation, build without teardown), 3 runs each, with and without the skill
- workspace: `/home/wsladmin/dev/inkwell-factory/.claude/skills/sssf-admin-workspace/iteration-3/`, so `benchmark.md` lands beside `iteration-2/benchmark.md`
- working directory for the runs: `~/dev/sbx-e2e` from Step 3 (the eval prompts mention Inkwell features; a build that adds the file the prompt asks for still passes the grader, which checks the runbook, not the app)

Baseline to beat or match, from `iteration-2/benchmark.md`: pass rate 100% with the skill, about 324 s and 80k tokens per run.

- [ ] **Step 6: Clean up the throwaway (user decides)**

`~/dev/sbx-e2e` and `evolv3ai/sbx-e2e` are the user's to delete or keep.
