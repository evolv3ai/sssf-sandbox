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
    ignored = (stamped_repo / ".gitignore").read_text().splitlines()
    for entry in [".sandbox/", ".claude/skills/sssf/apps/visualizer/node_modules/", ".claude/skills/sssf/apps/visualizer/dist/", "/run.log"]:
        assert entry in ignored, entry


def test_provisioner_build_outputs_are_ignored(stamped_repo: Path):
    # setup's gate A fails on any untracked path; the provisioner creates the first two, execute the third.
    for rel in [".claude/skills/sssf/apps/visualizer/node_modules/vite/index.js", ".claude/skills/sssf/apps/visualizer/dist/index.html", "run.log"]:
        f = stamped_repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x")
        r = subprocess.run(["git", "check-ignore", "-q", str(f)], cwd=stamped_repo)
        assert r.returncode == 0, f"{rel} is not ignored"


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


def test_next_steps_mention_push(stamped_repo: Path):
    result = run_install(stamped_repo)
    assert result.returncode == 0, result.stderr
    assert "git push" in result.stdout


def test_fresh_repo_gets_openrouter_roster(stamped_repo: Path):
    import re

    text = (stamped_repo / "adws/adw_sssf_config/sssf.config.yaml").read_text()
    models = re.findall(r"^\s*model:\s*(\S+)", text, re.MULTILINE)
    assert models, "no model: lines found"
    for m in models:
        assert m.startswith("openrouter/"), m


def test_existing_roster_is_kept(tmp_path: Path):
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "remote", "add", "origin", "git@github.com:acme/widgets.git"], cwd=tmp_path, check=True)
    config = tmp_path / "adws" / "adw_sssf_config" / "sssf.config.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("agents: []\n")

    result = run_install(tmp_path)
    assert result.returncode == 0, result.stderr
    assert config.read_text() == "agents: []\n"

    result = run_install(tmp_path, "--force")
    assert result.returncode == 0, result.stderr
    import re
    models = re.findall(r"^\s*model:\s*(\S+)", config.read_text(), re.MULTILINE)
    assert models
    for m in models:
        assert m.startswith("openrouter/"), m


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
