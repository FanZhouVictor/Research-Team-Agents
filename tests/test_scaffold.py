"""Tests for init_project (ra.scaffold): the project it makes, its first commit, the caches it
leaves out and what it undoes when a step fails.

Its refusals are tested in test_scaffold_refusals.py and 'ra.py init' in test_cli_init.py. The
tests run real git, on the real template/ directory or on a scratch copy of it (the template
fixture) that a test changes on purpose.
"""

import re
import subprocess
from pathlib import Path

import pytest
from conftest import _CACHES, _init_project
from ra import scaffold
from ra.check import run_checks
from ra.commit import format_message
from ra.frontmatter import parse
from ra.newfile import new_topic
from ra.scaffold import init_project

SUBJECT = "initialise project from RA_Agent template 0.1.0"


def _git(repo: Path, *args: str) -> str:
    """Run git in repo and return its output, read as UTF-8."""
    done = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return done.stdout


def _cached(root: Path) -> list[str]:
    """The files and folders under root, outside .git, that are caches or leftovers."""
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if ".git" not in path.relative_to(root).parts
        and (path.name in _CACHES or path.suffix == ".pyc")
    )


# --- the project that init_project makes ---------------------------------------------------


def test_init_layout_and_first_commit(tmp_path):
    dest = tmp_path / "p"
    init_project(dest, "Smoke Plume", "Fan", "Fan <fan@x>", ["claude-code", "codex"], "PI")
    for d in ["questions", "knowledge", "decisions", "literature/pdf", "log", "protocol/templates"]:
        assert (dest / d).is_dir()
    assert ".ra/" in (dest / ".gitignore").read_text(encoding="utf-8")
    project = (dest / "PROJECT.md").read_text(encoding="utf-8")
    assert "| Fan | Fan <fan@x> | claude-code, codex | PI |" in project
    log = subprocess.run(
        ["git", "log", "--format=%s"], cwd=dest, capture_output=True, text=True, check=True
    ).stdout
    assert log.strip() == "[protocol] initialise project from RA_Agent template 0.1.0"
    assert run_checks(dest) == []


def test_project_md_has_the_version_the_title_and_the_spec_sections(tmp_path):
    dest = tmp_path / "p"
    _init_project(dest)
    meta, body = parse(dest / "PROJECT.md")
    assert meta == {"protocol-version": "0.1.0"}
    assert body.startswith("# Smoke Plume\n")
    assert re.findall(r"^## (.+)$", body, re.MULTILINE) == [
        "Goals", "Members", "Phase", "Current status", "Pointers",
    ]
    assert "| Person | Git author name | Platform(s) | Role |\n|---|---|---|---|\n" in body
    comment = "<!-- AI-editable section: 3–8 lines, rewritten by update-status at session end -->"
    assert comment in body
    assert re.search(r"\{\w+\}", body) is None  # every token is filled


def test_platforms_keep_their_order_and_the_first_one_signs_the_commit(tmp_path):
    dest = tmp_path / "p"
    _init_project(dest, platforms=["codex", "claude-code"])
    project = (dest / "PROJECT.md").read_text(encoding="utf-8")
    assert "| Fan | Fan <fan@x> | codex, claude-code | PI |" in project
    assert "\nAgent: codex\n" in _git(dest, "log", "-1", "--format=%B")


def test_the_first_commit_message_is_the_structured_message_of_spec_9(tmp_path):
    dest = tmp_path / "p"
    _init_project(dest)
    links = ["PROJECT.md", "PROTOCOL.md"]
    expected = format_message("protocol", SUBJECT, "Fan", "claude-code", links)
    stored = _git(dest, "cat-file", "commit", "HEAD").split("\n\n", 1)[1]
    assert stored == expected
    assert _git(dest, "rev-list", "--count", "HEAD").strip() == "1"


def test_the_first_commit_is_by_the_git_author_and_the_tree_is_clean(tmp_path):
    dest = tmp_path / "p"
    _init_project(dest, git_author="Lee Wang <lee.wang@example.org>")
    who = _git(dest, "log", "-1", "--format=%an <%ae>|%cn <%ce>").strip()
    assert who == "Lee Wang <lee.wang@example.org>|Lee Wang <lee.wang@example.org>"
    assert _git(dest, "config", "--local", "user.name").strip() == "Lee Wang"
    assert _git(dest, "config", "--local", "user.email").strip() == "lee.wang@example.org"
    assert _git(dest, "symbolic-ref", "--short", "HEAD").strip() == "main"
    assert _git(dest, "status", "--porcelain") == ""


def test_the_files_every_project_starts_with(tmp_path):
    dest = tmp_path / "p"
    _init_project(dest)
    assert (dest / ".gitattributes").read_text(encoding="utf-8").splitlines() == ["*.pdf binary"]
    assert (dest / ".gitignore").read_text(encoding="utf-8").splitlines() == [
        ".ra/", "NEWS.md", "__pycache__/", ".DS_Store",
    ]
    keeps = [f"{folder}/.gitkeep" for folder in ("questions", "decisions", "literature/pdf", "log")]
    assert all((dest / keep).read_bytes() == b"" for keep in keeps)
    tracked = set(_git(dest, "ls-files").split("\n"))
    assert {*keeps, "PROJECT.md", "PROTOCOL.md", ".gitignore", ".gitattributes"} <= tracked
    assert {"protocol/ra.py", "protocol/requirements.txt", "protocol/ra/scaffold.py"} <= tracked
    assert parse(dest / "PROTOCOL.md")[0] == {"version": "0.1.0"}
    assert (dest / "knowledge" / "glossary.md").read_text(encoding="utf-8") == "# Glossary\n\n"


def test_the_topic_registry_starts_with_an_explanation_and_a_blank_line(tmp_path):
    dest = tmp_path / "p"
    _init_project(dest)
    registry = (dest / "knowledge" / "README.md").read_text(encoding="utf-8")
    assert registry.startswith("# Topic registry\n") and registry.endswith("\n\n")
    prose = [line for line in registry.splitlines()[1:] if line.strip()]
    assert len(prose) == 1 and not prose[0].startswith("- ")  # no topic is registered yet
    new_topic(dest, "goes-abi", "GOES-16 ABI")
    lines = (dest / "knowledge" / "README.md").read_text(encoding="utf-8").splitlines()
    assert lines[-2:] == ["", "- goes-abi — GOES-16 ABI"]
    assert run_checks(dest) == []


def test_the_version_comes_from_the_frontmatter_of_protocol_md(tmp_path, template):
    dest = tmp_path / "p"
    (template / "PROTOCOL.md").write_text("---\nversion: 9.9.9\n---\nbody\n", encoding="utf-8")
    _init_project(dest, template)
    assert parse(dest / "PROJECT.md")[0] == {"protocol-version": "9.9.9"}
    subject = _git(dest, "log", "-1", "--format=%s").strip()
    assert subject == "[protocol] initialise project from RA_Agent template 9.9.9"


def test_a_value_is_stripped_and_braces_in_a_value_are_left_alone(tmp_path):
    dest = tmp_path / "p"
    _init_project(dest, name="  Plume {person} {x} \n", role="{role}")
    body = parse(dest / "PROJECT.md")[1]
    assert body.startswith("# Plume {person} {x}\n")
    assert "| Fan | Fan <fan@x> | claude-code, codex | {role} |" in body


def test_non_ascii_names_reach_project_md_the_git_identity_and_the_commit(tmp_path):
    dest = tmp_path / "p"
    _init_project(dest, name="烟羽 Plume", person="张三", git_author="张三 <zs@x>")
    body = parse(dest / "PROJECT.md")[1]
    assert body.startswith("# 烟羽 Plume\n")
    assert "| 张三 | 张三 <zs@x> | claude-code, codex | PI |" in body
    assert _git(dest, "log", "-1", "--format=%an <%ae>").strip() == "张三 <zs@x>"
    assert "\nPerson: 张三\n" in _git(dest, "log", "-1", "--format=%B")


def test_a_relative_destination_is_read_from_the_current_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_project(Path("rel"))
    assert (tmp_path / "rel" / "PROJECT.md").is_file()
    assert run_checks(tmp_path / "rel") == []


def test_an_empty_existing_destination_is_filled(tmp_path):
    dest = tmp_path / "p"
    dest.mkdir()
    _init_project(dest)
    assert (dest / "PROJECT.md").is_file() and run_checks(dest) == []


# --- caches are never copied ---------------------------------------------------------------


def test_caches_in_the_template_are_not_copied(tmp_path, template, files_of):
    planted = [
        "protocol/ra/__pycache__/scaffold.cpython-312.pyc",
        "protocol/__pycache__/x.cpython-312.pyc",
        "protocol/.mypy_cache/3.12/meta.json",
        "protocol/.ruff_cache/CACHEDIR.TAG",
        ".pytest_cache/README.md",
        "protocol/ra/stray.pyc",
        "protocol/ra/.DS_Store",
        ".DS_Store",
    ]
    for rel in planted:
        (template / rel).parent.mkdir(parents=True, exist_ok=True)
        (template / rel).write_bytes(b"cache")
    dest = tmp_path / "p"
    _init_project(dest, template)
    assert files_of(dest) == files_of(template) - set(planted)
    assert _cached(dest) == []  # not even an empty __pycache__ folder


def test_a_project_made_from_the_real_template_has_no_caches(tmp_path):
    dest = tmp_path / "p"
    _init_project(dest)
    assert _cached(dest) == []


# --- a failure after the copy ---------------------------------------------------------------


@pytest.mark.parametrize("existed", [False, True], ids=["new-directory", "empty-directory"])
def test_a_failure_before_git_ran_leaves_what_there_was_before(tmp_path, monkeypatch, existed):
    dest = tmp_path / "p"
    if existed:
        dest.mkdir()
    monkeypatch.setenv("PATH", str(tmp_path / "no-git-here"))
    with pytest.raises(FileNotFoundError):
        _init_project(dest)
    assert dest.exists() is existed
    assert not existed or list(dest.iterdir()) == []


@pytest.mark.parametrize("existed", [False, True], ids=["new-directory", "empty-directory"])
def test_a_failure_in_the_first_commit_removes_the_project_but_not_the_directory(
    tmp_path, monkeypatch, existed
):
    def refuse(*args: object, **kwargs: object) -> str:
        raise subprocess.CalledProcessError(1, ["git", "commit"])

    dest = tmp_path / "p"
    if existed:
        dest.mkdir()
    monkeypatch.setattr(scaffold, "commit", refuse)
    with pytest.raises(subprocess.CalledProcessError):
        _init_project(dest)
    assert dest.exists() is existed
    assert not existed or list(dest.iterdir()) == []  # also no .git left behind
