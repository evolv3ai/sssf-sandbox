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


def test_userinfo_in_url_is_rejected(tmp_path):
    repo = git_repo(tmp_path, None)
    r = resolve(repo, env={"SBX_SOURCE_REPO": "https://user:secret@github.com/acme/widgets.git"})
    assert r.returncode == 1
    assert "credential" in r.stderr
    assert "secret" not in r.stderr


def test_no_origin_is_rejected(tmp_path):
    repo = git_repo(tmp_path, None)
    r = resolve(repo)
    assert r.returncode == 1 and "origin" in r.stderr


def test_probe_fails_on_unreachable_remote(tmp_path):
    repo = git_repo(tmp_path, "https://127.0.0.1:9/acme/widgets.git")
    r = resolve(repo, "--probe")
    assert r.returncode == 1 and "anonymous" in r.stderr


def test_probe_timeout_reports_anonymous_failure(tmp_path):
    # A fake `git` that hangs, first on PATH, plus a 1s timeout: the probe must
    # exit 1 through the normal message path, never a raw traceback.
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    fake_git.write_text("#!/bin/sh\nsleep 5\n")
    fake_git.chmod(0o755)
    r = resolve(
        tmp_path, "--probe",
        env={"SBX_SOURCE_REPO": "https://example.com/x/y.git",
             "SBX_PROBE_TIMEOUT": "1",
             "PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )
    assert r.returncode == 1
    assert "anonymous" in r.stderr and "timed out" in r.stderr
    assert "Traceback" not in r.stderr


def test_probe_disables_credential_helpers(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    argv_log = tmp_path / "argv.txt"
    fake_git = fake_bin / "git"
    fake_git.write_text(
        f"#!/bin/sh\nprintf '%s\\n' \"$@\" > {argv_log}\n"
        f"printf '%s\\n' \"$HOME\" >> {argv_log}\n"
        f"printf '%s\\n' \"$GIT_CONFIG_GLOBAL\" >> {argv_log}\n"
    )
    fake_git.chmod(0o755)
    r = resolve(
        tmp_path, "--probe",
        env={"SBX_SOURCE_REPO": "https://example.com/x/y.git",
             "PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )
    assert r.returncode == 0, r.stderr
    lines = argv_log.read_text().splitlines()
    args = lines[:3]
    probe_home = lines[-2]
    probe_git_config_global = lines[-1]
    assert args == ["-c", "credential.helper=", "ls-remote"]
    assert probe_git_config_global == "/dev/null"
    assert probe_home != os.environ.get("HOME")
