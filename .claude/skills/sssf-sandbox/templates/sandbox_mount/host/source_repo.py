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
