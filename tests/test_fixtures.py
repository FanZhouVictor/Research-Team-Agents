"""Tests for the shared fixtures in conftest.py: make_pdf, git_identity and repo."""

import os
import re
import subprocess
from pathlib import Path


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def test_make_pdf_writes_a_pdf_containing_the_text(tmp_path, make_pdf):
    pdf = tmp_path / "paper.pdf"
    make_pdf(pdf, "hello")
    data = pdf.read_bytes()
    assert data.startswith(b"%PDF-")
    assert b"(hello)" in data


def test_make_pdf_escapes_text_and_has_consistent_xref_offsets(tmp_path, make_pdf):
    pdf = tmp_path / "paper.pdf"
    make_pdf(pdf, "a(b)c\\d")
    data = pdf.read_bytes()
    assert rb"(a\(b\)c\\d)" in data
    assert data.rstrip().endswith(b"%%EOF")
    xref_at = int(re.search(rb"startxref\n(\d+)\n", data).group(1))
    assert data[xref_at:].startswith(b"xref\n")
    offsets = [int(o) for o in re.findall(rb"^(\d{10}) 00000 n $", data, re.MULTILINE)]
    assert len(offsets) == 5
    for number, offset in enumerate(offsets, start=1):
        assert data[offset:].startswith(b"%d 0 obj\n" % number)


def test_git_identity_sets_local_config(repo, git_identity):
    git_identity(repo, "Lee", "lee@x")
    assert _git(repo, "config", "--local", "user.name") == "Lee"
    assert _git(repo, "config", "--local", "user.email") == "lee@x"


def test_repo_fixture_layout_and_git_state(repo):
    expected_dirs = [
        "questions",
        "decisions",
        "literature/pdf",
        "log",
        "knowledge",
        "protocol/templates",
    ]
    for rel in expected_dirs:
        assert (repo / rel).is_dir(), rel
    project = (repo / "PROJECT.md").read_text(encoding="utf-8")
    assert "# Test Project" in project and "## Current status" in project
    registry = (repo / "knowledge" / "README.md").read_text(encoding="utf-8")
    assert registry == "# Topic registry\n\n"
    glossary = (repo / "knowledge" / "glossary.md").read_text(encoding="utf-8")
    assert glossary.startswith("# Glossary")
    assert _git(repo, "symbolic-ref", "--short", "HEAD") == "main"
    assert _git(repo, "config", "user.name") == "Fan"
    assert _git(repo, "config", "user.email") == "fan@x"


def test_git_config_comes_only_from_the_repo(repo):
    listing = _git(repo, "config", "--list", "--show-origin")
    origins = {line.split("\t", 1)[0] for line in listing.splitlines()}
    assert origins and all(origin.endswith(".git/config") for origin in origins), origins


def test_home_variables_point_at_one_scratch_directory_without_gitconfig():
    homes = {os.environ[name] for name in ("HOME", "XDG_CONFIG_HOME", "USERPROFILE")}
    assert len(homes) == 1
    home = Path(homes.pop())
    assert home.is_dir() and not (home / ".gitconfig").exists()


def test_home_redirect_alone_hides_the_users_git_config(repo):
    # Without GIT_CONFIG_GLOBAL, git < 2.32 (which ignores that variable) must still
    # find no global config: it looks in HOME and XDG_CONFIG_HOME.
    env = {k: v for k, v in os.environ.items() if k != "GIT_CONFIG_GLOBAL"}
    done = subprocess.run(
        ["git", "config", "--list", "--show-origin"],
        cwd=repo,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    origins = {line.split("\t", 1)[0] for line in done.stdout.splitlines()}
    assert origins and all(origin.endswith(".git/config") for origin in origins), origins
