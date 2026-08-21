#!/usr/bin/env -S uv run
# /// script
# dependencies = []
# ///
"""Stamp SSSF plus its optional exe.dev sandbox layer into the current repo.

Run: uv run .claude/skills/sssf-sandbox/scripts/install.py [--force]
No VM, key, or model API call is made by this installer.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL / "templates"
IGNORE = [".sandbox/", "sandbox/run.log", ".env"]
MODULE_LINE = 'mod sbx "sandbox/just/mod.just"'


def stamp(src: Path, dest: Path, force: bool, stamped: list[str], skipped: list[str]) -> None:
    # A cloned distribution can be installed into its own root. Avoid trying to
    # copy a skill/template file onto itself in that supported bootstrap flow.
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
    shutil.copy2(src, dest)
    stamped.append(str(dest))


def append_once(path: Path, line: str) -> bool:
    existing = path.read_text() if path.exists() else ""
    if line in existing:
        return False
    with path.open("a") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        handle.write(f"\n# Isolated SSSF VM lifecycle (stamped by sssf-sandbox)\n{line}\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite existing stamped sandbox files")
    args = parser.parse_args()
    root = Path.cwd().resolve()

    sssf_install = SKILL.parent / "sssf" / "scripts" / "install.py"
    if not sssf_install.is_file():
        print("Missing sibling .claude/skills/sssf; clone sssf-sandbox or copy both skills.", file=sys.stderr)
        return 2
    subprocess.run(["uv", "run", str(sssf_install)], cwd=root, check=True)

    stamped: list[str] = []
    skipped: list[str] = []
    # Keep both operating skills in the target after installation.
    stamp(SKILL.parent / "sssf", root / ".claude" / "skills" / "sssf", args.force, stamped, skipped)
    stamp(SKILL, root / ".claude" / "skills" / "sssf-sandbox", args.force, stamped, skipped)
    stamp(TEMPLATES / "sandbox", root / "sandbox", args.force, stamped, skipped)
    stamp(TEMPLATES / "sandbox" / "sssf.sandbox.config.yaml", root / "adws" / "adw_sssf_config" / "sssf.sandbox.config.yaml", args.force, stamped, skipped)
    if append_once(root / "justfile", MODULE_LINE):
        stamped.append(f"{root / 'justfile'} (+ sbx module)")
    for entry in IGNORE:
        if append_once(root / ".gitignore", entry):
            stamped.append(f"{root / '.gitignore'} (+ {entry})")
    for line in ("# Host-only: mints/revokes capped sandbox runtime keys", "OPENROUTER_PROVISIONING_KEY=", "# Optional HTTPS URL cloned into each sandbox; defaults to origin", "SBX_SOURCE_REPO="):
        if append_once(root / ".env.sample", line):
            stamped.append(f"{root / '.env.sample'} (+ sandbox setting)")

    print(f"sssf-sandbox installed into {root}")
    print(f"  stamped: {len(stamped)} file(s); skipped: {len(skipped)}")
    print("\nnext steps:")
    print("  1. cp .env.sample .env   # set OPENROUTER_PROVISIONING_KEY")
    print("  2. just sbx doctor       # local, non-billable preflight")
    print("  3. git init && git add -A && git commit -m 'Initialize SSSF sandbox'")
    print("  4. just sbx mount my-task   # explicit billable action")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
