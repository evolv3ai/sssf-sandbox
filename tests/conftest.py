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
