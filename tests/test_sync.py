"""Tests for ra.sync and 'python protocol/ra.py sync', on a bare origin and two real clones.

The two_clones fixture (conftest.py) gives clone a (Fan) and clone b (Lee). A conflict is made
the way two team members make one: both change the same lines, a pushes first, then b commits
and pulls. The command line tests run the protocol/ra.py that init_project copied into a clone.
"""

import subprocess
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest
from conftest import _append_fact, _commit_all
from ra.newfile import new_decision, new_question
from ra.sync import protected_conflicts, pull, push, unmerged_paths

DAY = date(2026, 10, 25)
FACT = Path("knowledge/goes-abi.md")
STATUS = Path("PROJECT.md")
DECISION = Path("decisions/D-2026-10-25-x.md")

Edit = Callable[[Path, str], None]  # an edit of one clone, by the person named in the text


def _git(repo: Path, *args: str) -> str:
    """Run git in repo and return its output without surrounding whitespace, read as UTF-8."""
    done = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return done.stdout.strip()


def _ra(clone: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the clone's own protocol/ra.py with the clone as working directory; read as UTF-8."""
    return subprocess.run(
        [sys.executable, str(clone / "protocol" / "ra.py"), *args],
        cwd=clone, capture_output=True, text=True, encoding="utf-8", check=False,
    )


def _fact(repo: Path, who: str) -> None:
    """Add a fact to knowledge/goes-abi.md, a protected file."""
    _append_fact(repo, "goes-abi", f"fact from {who}")


def _status(repo: Path, who: str) -> None:
    """Write a line under the 'Current status' heading of PROJECT.md, a file nobody protects."""
    path = repo / "PROJECT.md"
    heading = "## Current status\n"
    content = path.read_text(encoding="utf-8")
    assert heading in content
    filled = content.replace(heading, f"{heading}status from {who}\n", 1)
    path.write_text(filled, encoding="utf-8", newline="")


def _decision(repo: Path, who: str) -> None:
    """Create decisions/D-2026-10-25-x.md; the title tells who made it."""
    new_decision(repo, "x", f"title from {who}", "Fan", "codex", DAY, [])


def _diverge(a: Path, b: Path, *edits: Edit) -> None:
    """a makes the edits, commits and pushes; b makes the same edits and commits.

    b is then behind origin with a commit of its own, and each edit touches the same lines
    as a's, so b's pull has to merge them.
    """
    for edit in edits:
        edit(a, "A")
    _commit_all(a, "[log] a")
    push(a)
    for edit in edits:
        edit(b, "B")
    _commit_all(b, "[log] b")


def _conflicted(a: Path, b: Path, *edits: Edit) -> None:
    """_diverge, then b's pull, which stops on the conflict and leaves it in place."""
    _diverge(a, b, *edits)
    with pytest.raises(subprocess.CalledProcessError):
        pull(b)


def _push_a_question(repo: Path, slug: str) -> None:
    """Commit a new question in repo and push it."""
    new_question(repo, slug, "t", "Fan", "codex", DAY)
    _commit_all(repo, f"[question] {slug}")
    push(repo)


# --- the library: pull, push, unmerged_paths, protected_conflicts --------------------------


def test_protected_conflict_detected(two_clones):
    a, b = two_clones
    _append_fact(a, "goes-abi", "fact from A")
    _commit_all(a, "[knowledge] a")
    push(a)
    _append_fact(b, "goes-abi", "fact from B")
    _commit_all(b, "[knowledge] b")
    with pytest.raises(subprocess.CalledProcessError):
        pull(b)
    assert protected_conflicts(b) == [Path("knowledge/goes-abi.md")]
    assert unmerged_paths(b) == [FACT]  # the registry, changed alike by both, merged cleanly


def test_new_file_writes_never_conflict(two_clones):
    a, b = two_clones
    new_question(a, "qa", "t", "Fan", "codex", DAY)
    _commit_all(a, "[question] a")
    push(a)
    new_question(b, "qb", "t", "Lee", "claude-code", DAY)
    _commit_all(b, "[question] b")
    pull(b)
    assert unmerged_paths(b) == []
    questions = sorted(path.name for path in (b / "questions").glob("Q-*.md"))
    assert questions == ["Q-2026-10-25-qa.md", "Q-2026-10-25-qb.md"]
    assert _git(b, "rev-list", "--merges", "--count", "HEAD") == "1"


def test_a_conflicting_pull_leaves_the_conflict_in_place(two_clones):
    a, b = two_clones
    _conflicted(a, b, _fact)
    markers = (b / FACT).read_text(encoding="utf-8")
    assert "<<<<<<<" in markers and "fact from A" in markers and "fact from B" in markers
    assert (b / ".git" / "MERGE_HEAD").is_file()


def test_unmerged_paths_lists_a_conflict_outside_the_protected_folders(two_clones):
    a, b = two_clones
    _conflicted(a, b, _status)
    assert unmerged_paths(b) == [STATUS]
    assert protected_conflicts(b) == []


def test_unmerged_paths_are_sorted_and_protected_ones_are_under_knowledge_and_decisions(
    two_clones,
):
    a, b = two_clones
    _conflicted(a, b, _fact, _status, _decision)
    assert unmerged_paths(b) == [STATUS, DECISION, FACT]
    assert protected_conflicts(b) == [DECISION, FACT]


def test_no_unmerged_paths_after_the_merge_is_aborted(two_clones):
    a, b = two_clones
    _conflicted(a, b, _fact, _status)
    assert unmerged_paths(b) and protected_conflicts(b)
    _git(b, "merge", "--abort")
    assert unmerged_paths(b) == []
    assert protected_conflicts(b) == []


@pytest.mark.parametrize(
    "name",
    [
        "été notes.md",
        pytest.param(
            'say "hi".md',
            marks=pytest.mark.skipif(
                sys.platform == "win32", reason="a Windows file name cannot hold a double quote"
            ),
        ),
    ],
    ids=["non-ascii-and-space", "double-quote"],
)
def test_unmerged_paths_come_back_exactly_as_named(two_clones, name):
    # Plain 'git diff --name-only' writes names like these in quotes with escapes.
    a, b = two_clones
    path = Path("knowledge") / name
    (a / path).write_text("from A\n", encoding="utf-8")
    _commit_all(a, "[knowledge] a")
    push(a)
    (b / path).write_text("from B\n", encoding="utf-8")
    _commit_all(b, "[knowledge] b")
    with pytest.raises(subprocess.CalledProcessError):
        pull(b)
    assert unmerged_paths(b) == [path]
    assert protected_conflicts(b) == [path]


def test_push_then_pull_fast_forwards_the_other_clone(two_clones):
    a, b = two_clones
    pull(b)  # nothing new on origin yet: not an error
    _push_a_question(a, "qa")
    pull(b)
    assert _git(b, "rev-parse", "HEAD") == _git(a, "rev-parse", "HEAD")
    assert (b / "questions" / "Q-2026-10-25-qa.md").is_file()
    assert _git(b, "rev-list", "--merges", "--count", "HEAD") == "0"


@pytest.mark.parametrize(
    ("key", "value"), [("pull.rebase", "true"), ("pull.ff", "only"), ("merge.ff", "only")]
)
def test_pull_merges_whatever_the_users_git_says_about_rebasing_or_fast_forwards(
    two_clones, key, value
):
    # Ruling R44: set to 'only', pull.ff (on older git; git 2.50 lets --rebase=false override
    # it) and merge.ff (on any git) failed every pull after the histories diverged.
    a, b = two_clones
    _git(b, "config", key, value)
    _push_a_question(a, "qa")
    new_question(b, "qb", "t", "Lee", "codex", DAY)
    _commit_all(b, "[question] b")
    pull(b)
    assert _git(b, "rev-list", "--merges", "--count", "HEAD") == "1"


def test_push_is_refused_while_origin_has_newer_commits(two_clones):
    a, b = two_clones
    _push_a_question(a, "qa")
    new_question(b, "qb", "t", "Lee", "codex", DAY)
    _commit_all(b, "[question] b")
    with pytest.raises(subprocess.CalledProcessError):
        push(b)


# --- the command line: python protocol/ra.py sync ------------------------------------------


def test_cli_conflicts_without_conflicts_prints_one_line_and_exits_0(two_clones):
    _, b = two_clones
    proc = _ra(b, "sync", "conflicts")
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "sync: no conflicts\n", "")


def test_cli_conflicts_marks_a_protected_conflict_and_exits_2(two_clones):
    a, b = two_clones
    _conflicted(a, b, _fact)
    proc = _ra(b, "sync", "conflicts")
    assert (proc.returncode, proc.stdout, proc.stderr) == (
        2, "protected knowledge/goes-abi.md\n", ""
    )


def test_cli_conflicts_exits_2_for_a_conflict_outside_the_protected_folders_too(two_clones):
    a, b = two_clones
    _conflicted(a, b, _status)
    proc = _ra(b, "sync", "conflicts")
    assert (proc.returncode, proc.stdout, proc.stderr) == (2, "other PROJECT.md\n", "")


def test_cli_conflicts_lists_the_protected_paths_first(two_clones):
    a, b = two_clones
    _conflicted(a, b, _status, _decision, _fact)
    proc = _ra(b, "sync", "conflicts")
    assert proc.returncode == 2
    assert proc.stdout == (
        "protected decisions/D-2026-10-25-x.md\n"
        "protected knowledge/goes-abi.md\n"
        "other PROJECT.md\n"
    )


def test_cli_conflicts_finds_nothing_once_the_merge_is_aborted(two_clones):
    a, b = two_clones
    _conflicted(a, b, _fact)
    _git(b, "merge", "--abort")
    proc = _ra(b, "sync", "conflicts")
    assert (proc.returncode, proc.stdout) == (0, "sync: no conflicts\n")


def test_cli_pull_brings_in_the_new_commits_and_prints_nothing(two_clones):
    a, b = two_clones
    _push_a_question(a, "qa")
    proc = _ra(b, "sync", "pull")
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")
    assert (b / "questions" / "Q-2026-10-25-qa.md").is_file()


def test_cli_push_publishes_the_commits_and_prints_nothing(two_clones):
    a, b = two_clones
    new_question(a, "qa", "t", "Fan", "codex", DAY)
    _commit_all(a, "[question] a")
    proc = _ra(a, "sync", "push")
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")
    pull(b)
    assert _git(b, "rev-parse", "HEAD") == _git(a, "rev-parse", "HEAD")


def test_cli_pull_on_a_conflict_is_one_error_line_and_the_unmerged_paths(two_clones, monkeypatch):
    monkeypatch.setenv("LC_ALL", "C")  # git's wording is translated otherwise
    a, b = two_clones
    _diverge(a, b, _fact, _status)
    proc = _ra(b, "sync", "pull")
    assert proc.returncode == 1
    assert proc.stdout == "protected knowledge/goes-abi.md\nother PROJECT.md\n"
    lines = proc.stderr.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("error: git pull --rebase=false --ff --no-edit failed: ")
    assert "CONFLICT" in lines[0] and "Automatic merge failed" in lines[0]
    assert (b / ".git" / "MERGE_HEAD").is_file()  # the command leaves the conflict in place


def test_cli_pull_on_a_conflict_shows_the_error_line_before_the_paths(two_clones):
    a, b = two_clones
    _diverge(a, b, _fact)
    proc = subprocess.run(  # one stream, as a shell shows it with 2>&1
        [sys.executable, str(b / "protocol" / "ra.py"), "sync", "pull"],
        cwd=b, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        check=False,
    )
    lines = proc.stdout.splitlines()
    assert proc.returncode == 1
    assert lines[0].startswith("error: git pull ")
    assert lines[1:] == ["protected knowledge/goes-abi.md"]


def test_cli_pull_that_fails_without_a_conflict_is_one_error_line_and_nothing_else(repo):
    proc = _ra(repo, "sync", "pull")  # the repo fixture has no remote
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("error: git pull --rebase=false --ff --no-edit failed: ")
    assert len(proc.stderr.splitlines()) == 1


def test_cli_push_that_origin_refuses_is_one_error_line(two_clones):
    a, b = two_clones
    _push_a_question(a, "qa")
    new_question(b, "qb", "t", "Lee", "codex", DAY)
    _commit_all(b, "[question] b")
    proc = _ra(b, "sync", "push")
    assert (proc.returncode, proc.stdout) == (1, "")
    assert proc.stderr.startswith("error: git push failed: ")
    assert len(proc.stderr.splitlines()) == 1


def test_cli_sync_without_an_action_prints_usage_and_exits_2(two_clones):
    proc = _ra(two_clones[0], "sync")
    assert (proc.returncode, proc.stdout) == (2, "")
    assert "usage" in proc.stderr.lower()
