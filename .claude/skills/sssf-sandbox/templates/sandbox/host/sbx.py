#!/usr/bin/env python3
"""Host-only lifecycle for an isolated SSSF sandbox.

This program never runs automatically; invoke it through `just sbx ...`.
Records and temporary runtime keys live under .sandbox/runs/ and are gitignored.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / ".sandbox" / "runs"
TAG = os.getenv("SBX_TAG", "sssf-sandbox")
LIMIT = float(os.getenv("SBX_LIMIT", "50"))


def die(message: str) -> None:
    raise SystemExit(f"sbx: {message}")


def run(*args: str, input: str | None = None, capture: bool = False) -> str:
    result = subprocess.run(args, cwd=ROOT, input=input, text=True, capture_output=capture)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        die(f"command failed ({' '.join(args)}): {detail}")
    return result.stdout.strip() if capture else ""


def record_path(run_id: str) -> Path:
    return RUNS / f"{run_id}.json"


def load(run_id: str) -> dict:
    path = record_path(run_id)
    if not path.is_file():
        die(f"no record for {run_id}")
    return json.loads(path.read_text())


def save(data: dict) -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    record_path(data["run_id"]).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def source_repo() -> str:
    configured = os.getenv("SBX_SOURCE_REPO")
    if configured:
        return configured
    origin = run("git", "remote", "get-url", "origin", capture=True)
    match = re.fullmatch(r"git@github\.com:([^/]+/[^/]+?)(?:\.git)?", origin)
    return f"https://github.com/{match.group(1)}.git" if match else origin


def new_id(value: str) -> str:
    if re.fullmatch(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?-[0-9a-f]{6}", value):
        return value
    safe = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    if not safe:
        die("run id must contain letters or numbers")
    return f"{safe[:50]}-{secrets.token_hex(3)}"


def ssh_vm(vm: str, script: str) -> str:
    return run("ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", f"{vm}.exe.xyz", "bash", "-s", input=script, capture=True)


def mint_key(run_id: str, limit: float) -> tuple[str, str]:
    provisioning = os.getenv("OPENROUTER_PROVISIONING_KEY")
    if not provisioning:
        die("OPENROUTER_PROVISIONING_KEY is required for create; add it to .env")
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/keys",
        data=json.dumps({"name": f"sbx-{run_id}", "limit": limit}).encode(),
        headers={"Authorization": f"Bearer {provisioning}", "Content-Type": "application/json"},
        method="POST",
    )
    payload: dict = {}
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            parsed = json.load(response)
            if not isinstance(parsed, dict):
                die("OpenRouter key mint response was not a JSON object")
            payload = parsed
    except urllib.error.URLError as exc:
        die(f"OpenRouter key mint failed: {exc}")
    data = payload.get("data", payload)
    key, key_hash = data.get("key"), data.get("hash")
    if not key or not key_hash:
        die("OpenRouter key mint response did not include key and hash")
    return key, key_hash


def revoke_key(key_hash: str) -> None:
    provisioning = os.getenv("OPENROUTER_PROVISIONING_KEY")
    if not provisioning:
        die("OPENROUTER_PROVISIONING_KEY is required to revoke the live runtime key")
    request = urllib.request.Request(
        f"https://openrouter.ai/api/v1/keys/{key_hash}",
        headers={"Authorization": f"Bearer {provisioning}"},
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status // 100 != 2:
                die(f"OpenRouter key revocation returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            die(f"OpenRouter key revocation returned HTTP {exc.code}")
    except urllib.error.URLError as exc:
        die(f"OpenRouter key revocation failed: {exc}")


def command_doctor(args: argparse.Namespace) -> None:
    missing = [name for name in ("git", "python3", "ssh", "scp", "curl", "uv", "just") if not shutil_which(name)]
    if missing:
        die("missing commands: " + ", ".join(missing))
    for path in (ROOT / "sandbox" / "guest" / "provision.sh", ROOT / "sandbox" / "guest" / "models.json.tmpl", ROOT / "adws"):
        if not path.exists():
            die(f"required path missing: {path.relative_to(ROOT)}")
    try:
        json.loads((ROOT / "sandbox" / "guest" / "models.json.tmpl").read_text())
    except ValueError as exc:
        die(f"invalid guest model template: {exc}")
    print(f"source repo: {source_repo()}")
    if args.remote:
        run("ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "exe.dev", "true")
        print("exe.dev SSH: reachable")
    print("sbx doctor: OK (no VM or key created)")


def command_create(args: argparse.Namespace) -> str:
    run_id = new_id(args.run_id)
    if record_path(run_id).exists():
        die(f"record already exists: {run_id}")
    RUNS.mkdir(parents=True, exist_ok=True)
    record = {"run_id": run_id, "state": "creating", "created_at": datetime.now(UTC).isoformat(), "source_repo": source_repo(), "limit": args.limit, "tag": TAG}
    save(record)
    # VM first means a failed key mint leaves a visible resource and a usable record.
    out = run("ssh", "exe.dev", "new", "--name", run_id, "--tag", TAG, "--json", capture=True)
    try:
        payload = json.loads(out)
    except ValueError:
        payload = {}
    vm = payload.get("vm_name") or payload.get("name") or run_id
    key, key_hash = mint_key(run_id, args.limit)
    key_path = RUNS / f"{run_id}.key"
    key_path.write_text(key + "\n")
    key_path.chmod(0o600)
    record.update({"state": "created", "vm_name": vm, "https_url": f"https://{vm}.exe.xyz", "key_hash": key_hash})
    save(record)
    print(f"created: {run_id} ({vm}) — runtime key capped at ${args.limit:g}")
    return run_id


def command_fill(args: argparse.Namespace) -> None:
    data = load(args.run_id)
    key_path = RUNS / f"{args.run_id}.key"
    if not key_path.is_file():
        die("runtime key file missing; run create first")
    vm, repo = data["vm_name"], data["source_repo"]
    script = f'''set -euo pipefail
rm -rf app
git clone --quiet {shlex.quote(repo)} app
cd app
git switch -c {shlex.quote('sbx/' + args.run_id)}
umask 077
cat > .env <<'EOF'
OPENROUTER_API_KEY={key_path.read_text().strip()}
EOF
chmod 600 .env
git rev-parse HEAD
'''
    head = ssh_vm(vm, script).splitlines()[-1]
    data.update({"state": "filled", "commit_sha": head, "branch": f"sbx/{args.run_id}"})
    save(data)
    print(f"filled: {args.run_id} at {head}")


def command_setup(args: argparse.Namespace) -> None:
    data = load(args.run_id)
    output = ssh_vm(data["vm_name"], "bash app/sandbox/guest/provision.sh")
    if "PROVISION_READY" not in output:
        die("guest provisioner did not report readiness; VM left running for inspection")
    data["state"] = "ready"
    save(data)
    print(f"ready: {args.run_id}")


def command_mount(args: argparse.Namespace) -> None:
    run_id = command_create(args)
    command_fill(argparse.Namespace(run_id=run_id))
    command_setup(argparse.Namespace(run_id=run_id))
    command_observe(argparse.Namespace(run_id=run_id))


def command_execute(args: argparse.Namespace) -> None:
    data = load(args.run_id)
    if data.get("state") not in {"ready", "running"}:
        die("sandbox is not ready; run mount or setup first")
    command = f"cd app && nohup just sdlc {shlex.quote(args.prompt)} --config adws/adw_sssf_config/sssf.sandbox.config.yaml > sandbox/run.log 2>&1 < /dev/null & echo $!"
    pid = run("ssh", f"{data['vm_name']}.exe.xyz", command, capture=True).splitlines()[-1]
    if not pid.isdigit():
        die(f"expected detached pid, got {pid!r}")
    data.update({"state": "running", "pid": int(pid), "prompt": args.prompt})
    save(data)
    print(f"running: {args.run_id} pid={pid}; inspect with: just sbx logs {args.run_id}")


def command_observe(args: argparse.Namespace) -> None:
    data = load(args.run_id)
    status = ssh_vm(data["vm_name"], "cd app && git status --short && (test -f sandbox/run.log && tail -n 20 sandbox/run.log || true)")
    print(json.dumps({"run_id": args.run_id, "state": data.get("state"), "url": data.get("https_url"), "status": status}, indent=2))


def command_logs(args: argparse.Namespace) -> None:
    data = load(args.run_id)
    print(ssh_vm(data["vm_name"], "cd app && tail -n 80 sandbox/run.log"))


def command_harvest(args: argparse.Namespace) -> None:
    data = load(args.run_id)
    base = data.get("commit_sha")
    branch = data.get("branch")
    vm = data["vm_name"]
    if not isinstance(base, str) or not isinstance(branch, str):
        die("record has invalid commit/branch values")
    remote = f"cd app && git bundle create /tmp/{args.run_id}.bundle {shlex.quote(base)}..{shlex.quote(branch)}"
    run("ssh", f"{vm}.exe.xyz", remote)
    bundle = RUNS / f"{args.run_id}.bundle"
    run("scp", f"{vm}.exe.xyz:/tmp/{args.run_id}.bundle", str(bundle))
    run("git", "bundle", "verify", str(bundle))
    run("git", "fetch", "--force", str(bundle), f"refs/heads/{branch}:refs/sandbox/{args.run_id}")
    print(f"harvested: refs/sandbox/{args.run_id}")


def command_teardown(args: argparse.Namespace) -> None:
    data = load(args.run_id)
    if not args.no_harvest:
        command_harvest(args)
    if not isinstance(data.get("key_hash"), str):
        die("record lacks a runtime key hash; refusing VM destruction")
    revoke_key(data["key_hash"])
    run("ssh", "exe.dev", "rm", data["vm_name"])
    key_path = RUNS / f"{args.run_id}.key"
    key_path.unlink(missing_ok=True)
    data["state"] = "torn_down"
    save(data)
    print(f"torn down: {args.run_id}; runtime key revoked and local key file removed")


def shutil_which(name: str) -> str | None:
    from shutil import which
    return which(name)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    subs = p.add_subparsers(dest="command", required=True)
    doctor = subs.add_parser("doctor"); doctor.add_argument("--remote", action="store_true"); doctor.set_defaults(fn=command_doctor)
    for name, fn in (("fill", command_fill), ("setup", command_setup), ("observe", command_observe), ("logs", command_logs), ("harvest", command_harvest)):
        q = subs.add_parser(name); q.add_argument("run_id"); q.set_defaults(fn=fn)
    create = subs.add_parser("create"); create.add_argument("run_id"); create.add_argument("--limit", type=float, default=LIMIT); create.set_defaults(fn=command_create)
    mount = subs.add_parser("mount"); mount.add_argument("run_id"); mount.add_argument("--limit", type=float, default=LIMIT); mount.set_defaults(fn=command_mount)
    execute = subs.add_parser("execute"); execute.add_argument("run_id"); execute.add_argument("prompt"); execute.set_defaults(fn=command_execute)
    teardown = subs.add_parser("teardown"); teardown.add_argument("run_id"); teardown.add_argument("--no-harvest", action="store_true"); teardown.set_defaults(fn=command_teardown)
    return p


if __name__ == "__main__":
    ns = parser().parse_args()
    ns.fn(ns)
