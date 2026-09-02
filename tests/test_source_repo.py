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
