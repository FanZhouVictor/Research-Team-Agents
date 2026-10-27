"""Tests for ra.commit: the commit message of spec §9 and the commit that carries it.

format_message is tested on its own. commit() and 'ra.py commit' run real git in the repo
fixture, and the tests read the history back with git.
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from conftest import _append_fact, _commit_all, _write
from ra.commit import AGENTS, TYPE_TAGS, commit, format_message
from ra.newfile import new_log
from ra.sync import pull, push

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "template" / "protocol" / "ra.py"

COMMIT = [
    "commit", "--type", "log", "--subject", "end of session", "--person", "Fan", "--agent", "codex",
]


def _git(repo: Path, *args: str) -> str:
    """Run git in repo and return its output, read as UTF-8."""
    done = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return done.stdout


def _stored_message(repo: Path) -> str:
    """The message of HEAD exactly as stored: what follows the headers of the commit object."""
    return _git(repo, "cat-file", "commit", "HEAD").split("\n\n", 1)[1]


def _committed_files(repo: Path, rev: str = "HEAD") -> list[str]:
    """The files a commit changed, sorted."""
    return sorted(_git(repo, "show", "--name-only", "--format=", rev).split())


def _note(repo: Path, rel: str, text: str = "x\n") -> Path:
    """Create the file rel (a POSIX path relative to repo) and return its path."""
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    _write(path, text)
    return path


def _message(**changes: Any) -> str:
    """format_message for a valid log entry by Fan, with some of its arguments replaced."""
    args: dict[str, Any] = {
        "type_tag": "log", "subject": "s", "person": "Fan", "agent": "codex", "links": [],
    }
    args.update(changes)
    return format_message(**args)


def _ra(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run 'python <ra.py> <args>' with cwd as the working directory; output is read as UTF-8."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=False,
    )


# --- the message format ------------------------------------------------------------------


def test_message_format_verbatim():
    assert format_message(
        "literature", "added Smith 2024", "Fan", "codex", ["literature/smith2024.md"]
    ) == (
        "[literature] added Smith 2024\n\nPerson: Fan\nAgent: codex\n"
        "Links: literature/smith2024.md\n"
    )


def test_message_reproduces_the_spec_example():
    assert format_message(
        "literature",
        "added Smith 2024 — plume segmentation from GOES imagery",
        "Fan",
        "codex",
        ["literature/smith2024-plume-goes.md", "questions/Q-2026-10-25-plume-baselines.md"],
    ) == (
        "[literature] added Smith 2024 — plume segmentation from GOES imagery\n"
        "\n"
        "Person: Fan\n"
        "Agent: codex\n"
        "Links: literature/smith2024-plume-goes.md, questions/Q-2026-10-25-plume-baselines.md\n"
    )


def test_message_without_links_keeps_an_empty_links_line():
    # R18: the three trailers are always there; 'Links:' has nothing after the colon.
    assert _message(links=[]) == "[log] s\n\nPerson: Fan\nAgent: codex\nLinks:\n"


def test_type_tags_and_agents_are_the_spec_values():
    assert TYPE_TAGS == (
        "literature", "question", "knowledge", "decision", "log", "status", "protocol",
    )
    assert AGENTS == ("claude-code", "codex")


@pytest.mark.parametrize("tag", TYPE_TAGS)
def test_every_type_tag_is_accepted(tag):
    assert _message(type_tag=tag).startswith(f"[{tag}] s\n\n")


@pytest.mark.parametrize("agent", AGENTS)
def test_every_agent_is_accepted(agent):
    assert f"\nAgent: {agent}\n" in _message(agent=agent)


def test_message_strips_whitespace_around_each_value():
    # git strips trailing whitespace from message lines; the returned text must survive that.
    padded = _message(subject="  s  ", person=" Fan ", links=[" a.md ", "b.md\t"])
    assert padded == _message(subject="s", person="Fan", links=["a.md", "b.md"])


@pytest.mark.parametrize(
    "changes",
    [
        {"type_tag": "experiment"},
        {"type_tag": "Log"},
        {"type_tag": ""},
        {"agent": "gemini"},
        {"agent": "Codex"},
        {"agent": ""},
        {"subject": ""},
        {"subject": "  \t "},
        {"subject": "two\nlines"},
        {"subject": "carriage\rreturn"},
        {"person": ""},
        {"person": " \t"},
        {"person": "Fan\nAgent: claude-code"},  # would add a second trailer
        {"links": ["a.md\nPerson: Lee"]},
        {"links": ["a.md, b.md"]},  # a comma would read back as two links
        {"links": [""]},
        {"links": ["  "]},
    ],
    ids=lambda changes: "-".join(f"{key}={value!r}" for key, value in changes.items()),
)
def test_invalid_input_raises_value_error(changes):
    with pytest.raises(ValueError):
        _message(**changes)


# --- commit() ----------------------------------------------------------------------------


def test_bad_tag_rejected(repo):
    with pytest.raises(ValueError):
        commit(repo, [], "experiment", "x", "Fan", "codex", [])


def test_bad_agent_rejected(repo):
    with pytest.raises(ValueError):
        commit(repo, [], "log", "x", "Fan", "gemini", [])


def test_invalid_message_input_stages_nothing(repo):
    note = _note(repo, "log/a.md")
    with pytest.raises(ValueError):
        commit(repo, [note], "experiment", "x", "Fan", "codex", [])
    assert _git(repo, "diff", "--cached", "--name-only") == ""


def test_commit_returns_the_sha_of_head_and_writes_the_message_exactly(repo):
    note = _note(repo, "log/a.md")
    message = format_message("log", "session end", "Fan", "codex", ["log/a.md"])
    sha = commit(repo, [note], "log", "session end", "Fan", "codex", ["log/a.md"])
    assert re.fullmatch(r"[0-9a-f]{40,64}", sha)
    assert sha == _git(repo, "rev-parse", "HEAD").strip()
    assert _git(repo, "log", "-1", "--pretty=format:%B") == message
    assert _stored_message(repo) == message


def test_commit_keeps_non_ascii_text_exact(repo):
    note = _note(repo, "log/a.md")
    subject, person, link = "ajout de Schröder — 张三", "张三", "literature/schröder2024.md"
    commit(repo, [note], "literature", subject, person, "claude-code", [link])
    expected = format_message("literature", subject, person, "claude-code", [link])
    assert _stored_message(repo) == expected


def test_commit_adds_only_the_given_paths(repo):
    _commit_all(repo, "base")
    a = _note(repo, "log/a.md")
    _note(repo, "log/b.md")
    commit(repo, [a], "log", "s", "Fan", "codex", [])
    assert _committed_files(repo) == ["log/a.md"]
    assert _git(repo, "status", "--porcelain") == "?? log/b.md\n"


def test_commit_takes_absolute_and_repo_relative_paths(repo):
    absolute = _note(repo, "log/a.md")
    _note(repo, "log/b.md")
    _note(repo, "questions/q.md")
    paths = [absolute, Path("log/b.md"), Path("log/../questions/q.md")]
    commit(repo, paths, "log", "s", "Fan", "codex", [])
    assert _committed_files(repo) == ["log/a.md", "log/b.md", "questions/q.md"]


def test_commit_without_paths_commits_what_is_already_staged(repo):
    _note(repo, "log/a.md")
    _git(repo, "add", "--", "log/a.md")
    sha = commit(repo, [], "log", "s", "Fan", "codex", [])
    assert _committed_files(repo, sha) == ["log/a.md"]


def test_commit_with_nothing_to_commit_raises_and_creates_no_empty_commit(repo):
    _commit_all(repo, "base")
    before = _git(repo, "rev-list", "--count", "HEAD")
    with pytest.raises(subprocess.CalledProcessError):
        commit(repo, [], "log", "s", "Fan", "codex", [])
    assert _git(repo, "rev-list", "--count", "HEAD") == before


def _outside(kind: str, repo: Path) -> Path:
    """A path that is not inside repo, in the way named by kind."""
    if kind == "absolute":
        return repo.parent / "elsewhere.md"
    if kind == "parent":
        return Path("..") / "elsewhere.md"
    if kind == "nested":
        return Path("log") / ".." / ".." / "elsewhere.md"
    return Path(f"{repo}-other") / "x.md"  # a sibling whose name starts with the repo's


def _forbidden(*args: object, **kwargs: object) -> None:
    raise AssertionError("git ran before the arguments were validated")


@pytest.mark.parametrize("kind", ["absolute", "parent", "nested", "sibling"])
def test_commit_rejects_a_path_outside_the_repo_before_any_git_call(repo, monkeypatch, kind):
    inside = _note(repo, "log/a.md")
    with monkeypatch.context() as patch:
        patch.setattr(subprocess, "run", _forbidden)
        with pytest.raises(ValueError, match="not inside"):
            commit(repo, [inside, _outside(kind, repo)], "log", "s", "Fan", "codex", [])
    assert _git(repo, "diff", "--cached", "--name-only") == ""


def test_commit_refuses_while_a_merge_conflict_is_in_place_and_stages_nothing(two_clones):
    # Ruling R63: git refused the commit only after 'git add' had staged the entry, and the
    # human's merge commit would then have taken it in (PROTOCOL.md §9).
    a, b = two_clones
    _append_fact(a, "goes-abi", "fact from A")
    _commit_all(a, "[knowledge] a")
    push(a)
    _append_fact(b, "goes-abi", "fact from B")
    _commit_all(b, "[knowledge] b")
    with pytest.raises(subprocess.CalledProcessError):
        pull(b)  # stops on the conflict in knowledge/goes-abi.md and leaves it in place
    entry = new_log(b, "Lee", "codex", datetime(2026, 10, 25, 14, 32))
    rel = entry.relative_to(b).as_posix()
    before = _git(b, "status", "--short")
    assert f"?? {rel}\n" in before
    refusal = "a merge conflict is in place (knowledge/goes-abi.md); nothing was staged"
    with pytest.raises(ValueError, match=re.escape(refusal)):
        commit(b, [entry], "log", "s", "Lee", "codex", [rel])
    proc = _ra(b, *COMMIT, "--", rel)
    assert (proc.returncode, proc.stdout, proc.stderr) == (1, "", f"error: {refusal}\n")
    assert _git(b, "status", "--short") == before


# --- python protocol/ra.py commit ----------------------------------------------------------


def test_cli_commit_prints_the_sha_and_writes_the_message(repo):
    _note(repo, "log/a.md")
    links = ["log/a.md", "questions/Q-2026-10-25-x.md"]
    proc = _ra(repo, *COMMIT, "--links", *links, "--", "log/a.md")
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""
    assert proc.stdout == _git(repo, "rev-parse", "HEAD")
    assert _stored_message(repo) == format_message("log", "end of session", "Fan", "codex", links)
    assert _committed_files(repo) == ["log/a.md"]


def test_cli_commit_collects_repeated_links_flags(repo):
    _note(repo, "log/a.md")
    proc = _ra(repo, *COMMIT, "--links", "a.md", "--links", "b.md", "--", "log/a.md")
    assert proc.returncode == 0, proc.stderr
    assert "\nLinks: a.md, b.md\n" in _stored_message(repo)


def test_cli_commit_without_links_writes_an_empty_links_line(repo):
    _note(repo, "log/a.md")
    proc = _ra(repo, *COMMIT, "--", "log/a.md")
    assert proc.returncode == 0, proc.stderr
    assert _stored_message(repo).endswith("\nAgent: codex\nLinks:\n")


def test_cli_commit_without_paths_commits_the_staged_files(repo):
    _note(repo, "log/a.md")
    _git(repo, "add", "--", "log/a.md")
    proc = _ra(repo, *COMMIT)
    assert proc.returncode == 0, proc.stderr
    assert _committed_files(repo) == ["log/a.md"]


def test_cli_commit_with_nothing_staged_is_one_error_line(repo, monkeypatch):
    monkeypatch.setenv("LC_ALL", "C")  # git's wording is translated otherwise
    _commit_all(repo, "base")
    before = _git(repo, "rev-list", "--count", "HEAD")
    proc = _ra(repo, *COMMIT)
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("error: git commit -F - failed: ")
    assert "nothing to commit" in proc.stderr  # git says it on stdout; the line carries it
    assert len(proc.stderr.splitlines()) == 1
    assert _git(repo, "rev-list", "--count", "HEAD") == before


def test_cli_commit_reports_a_failed_git_add_as_one_error_line(repo, monkeypatch):
    monkeypatch.setenv("LC_ALL", "C")
    proc = _ra(repo, *COMMIT, "--", "missing.md")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr == (
        "error: git add -- missing.md failed: "
        "fatal: pathspec 'missing.md' did not match any files\n"
    )


def test_cli_commit_rejects_a_path_outside_the_repo(repo):
    before = _git(repo, "rev-list", "--all", "--count")
    proc = _ra(repo, *COMMIT, "--", str(repo.parent / "elsewhere.md"))
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("error: ") and "not inside" in proc.stderr
    assert _git(repo, "rev-list", "--all", "--count") == before


def test_cli_commit_reports_an_unknown_agent_as_an_error_line(repo):
    proc = _ra(
        repo, "commit", "--type", "log", "--subject", "s", "--person", "Fan", "--agent", "gemini"
    )
    assert proc.returncode == 1
    assert proc.stderr.startswith("error: agent must be one of claude-code, codex")


def test_cli_commit_rejects_an_unknown_type_with_usage(repo):
    proc = _ra(
        repo, "commit", "--type", "experiment", "--subject", "s", "--person", "Fan",
        "--agent", "codex",
    )
    assert proc.returncode == 2
    assert "invalid choice" in proc.stderr and "literature" in proc.stderr
