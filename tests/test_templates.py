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
