"""Tests for 'python protocol/ra.py digest', run as a subprocess inside a project repo.

The library behind the command is tested in test_digest.py.
"""

import subprocess
import sys
from pathlib import Path

from conftest import _commit_all

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "template" / "protocol" / "ra.py"


def _git(repo: Path, *args: str) -> str:
    """Run git in repo and return its output, read as UTF-8."""
    done = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return done.stdout


def _head(repo: Path) -> str:
    """The sha of HEAD."""
    return _git(repo, "rev-parse", "HEAD").strip()


def _ra(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run 'python <ra.py> <args>' with cwd as the working directory; output is read as UTF-8."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=False,
    )


def _entries(text: str) -> list[str]:
    """The commit lines of a rendered digest."""
    return [line for line in text.splitlines() if line.startswith("- ")]


def test_cli_digest_prints_the_digest_since_the_persons_last_commit(
    repo, git_identity, monkeypatch
):
    monkeypatch.setenv("GIT_AUTHOR_DATE", "2026-10-25T09:00:00+0000")
    _commit_all(repo, "[log] fan's own")
    git_identity(repo, "Lee", "lee@x")
    _commit_all(
        repo, "[question] added A\n\nPerson: Lee\nAgent: claude-code\nLinks: questions/Q-x.md"
    )
    question = _head(repo)
    _commit_all(repo, "fixed typo by hand")
    typo = _head(repo)
    proc = _ra(repo, "digest", "--person", "Fan")
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""
    assert proc.stdout == (
        "## question (1)\n"
        f"- 2026-10-25 {question[:7]} added A — Lee/claude-code\n"
        "\n"
        "## other (1)\n"
        f"- 2026-10-25 {typo[:7]} fixed typo by hand — ?/?\n"
    )


def test_cli_digest_fallback_defaults_to_20_and_can_be_set(repo):
    for i in range(25):
        _commit_all(repo, f"[log] s{i}")
    default = _ra(repo, "digest", "--person", "Nobody")
    assert default.returncode == 0, default.stderr
    assert len(_entries(default.stdout)) == 20
    few = _ra(repo, "digest", "--person", "Nobody", "--fallback", "3")
    assert few.returncode == 0, few.stderr
    assert len(_entries(few.stdout)) == 3


def test_cli_digest_in_a_repository_without_commits(tmp_path):
    unborn = tmp_path / "unborn"  # the repo fixture already has its first commit
    (unborn / "protocol").mkdir(parents=True)
    for name in ("PROJECT.md", "protocol/ra.py"):  # what makes it a project root (Ruling R62)
        (unborn / name).write_text("", encoding="utf-8")
    _git(unborn, "init", "-q", "-b", "main")
    proc = _ra(unborn, "digest", "--person", "Fan")
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "No new commits.\n", "")


def test_cli_digest_rejects_a_blank_person_with_an_error_line(repo):
    _commit_all(repo, "[log] s")
    proc = _ra(repo, "digest", "--person", " ")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr == "error: person must not be empty\n"


def test_cli_digest_reports_a_git_error_as_one_error_line(repo):
    _commit_all(repo, "[log] s")
    proc = _ra(repo, "digest", "--person", "\\(")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("error: git log ")
    assert " --author=\\( -n 1 --format=%H failed: " in proc.stderr
    assert len(proc.stderr.splitlines()) == 1


def test_cli_digest_handles_non_ascii_names_and_subjects(repo, git_identity):
    git_identity(repo, "张三", "z@x")
    _commit_all(repo, "[log] first")
    git_identity(repo, "José", "j@x")
    _commit_all(repo, "[status] café — ünïcode ✓")
    proc = _ra(repo, "digest", "--person", "张三")
    assert proc.returncode == 0, proc.stderr
    assert "café — ünïcode ✓" in proc.stdout
