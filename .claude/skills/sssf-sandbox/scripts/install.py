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
