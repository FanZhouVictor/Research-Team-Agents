"""Rules that every creator in ra.newfile follows: input checks, no overwriting, clean output."""

import re
from datetime import date, datetime
from pathlib import Path

import pytest
from ra import newfile
from ra.newfile import new_decision, new_literature, new_log, new_question, new_topic

DAY = date(2026, 10, 25)
BAD_NAMES = ["Eval Metric", "a_b", "", "é", "a/b", "../x", "x\n", "UPPER", "a.b"]
NAMED = ["question", "decision", "literature", "topic"]
WITH_AUTHOR = ["question", "decision", "literature", "log"]
WITH_TITLE = ["question", "decision", "literature"]
ALL = ["question", "decision", "literature", "log", "topic"]


def _create(
    kind: str, repo: Path, paper: Path, *, name="x", person="Fan", agent="codex", title="t"
) -> Path:
    """Call the creator for kind with valid defaults; name is the slug, citekey or topic."""
    if kind == "question":
        return new_question(repo, name, title, person, agent, DAY)
    if kind == "decision":
        return new_decision(repo, name, title, person, agent, DAY, [])
    if kind == "literature":
        meta = {"person": person, "agent": agent, "date": "2026-10-25", "title": title}
        return new_literature(repo, name, meta, paper)
    if kind == "log":
        return new_log(repo, person, agent, datetime(2026, 10, 25, 14, 32))
    return new_topic(repo, name, "scope")


@pytest.mark.parametrize("name", BAD_NAMES)
def test_names_must_be_lower_case_letters_digits_and_hyphens(repo, files_of, name):
    before = files_of(repo)
    with pytest.raises(ValueError, match=r"slug must match \[a-z0-9-\]\+"):
        new_question(repo, name, "t", "Fan", "codex", DAY)
    assert files_of(repo) == before


@pytest.mark.parametrize("kind", NAMED)
def test_every_creator_checks_its_slug_citekey_or_topic(repo, paper, files_of, kind):
    before = files_of(repo)
    with pytest.raises(ValueError, match="must match"):
        _create(kind, repo, paper, name="Bad Name")
    assert files_of(repo) == before


@pytest.mark.parametrize("agent", ["claude", "Codex", "", "gpt"])
def test_agent_must_be_claude_code_or_codex(repo, files_of, agent):
    before = files_of(repo)
    with pytest.raises(ValueError, match="agent must be one of claude-code, codex"):
        new_question(repo, "x", "t", "Fan", agent, DAY)
    assert files_of(repo) == before


@pytest.mark.parametrize("person", ["", "   "])
def test_person_must_not_be_blank(repo, files_of, person):
    before = files_of(repo)
    with pytest.raises(ValueError, match="person must not be empty"):
        new_question(repo, "x", "t", person, "codex", DAY)
    assert files_of(repo) == before


@pytest.mark.parametrize("kind", WITH_AUTHOR)
def test_every_creator_with_an_author_checks_person_and_agent(repo, paper, files_of, kind):
    before = files_of(repo)
    with pytest.raises(ValueError, match="agent"):
        _create(kind, repo, paper, agent="claude")
    with pytest.raises(ValueError, match="person"):
        _create(kind, repo, paper, person="")
    assert files_of(repo) == before


@pytest.mark.parametrize("kind", WITH_TITLE)
def test_a_blank_title_is_rejected(repo, paper, files_of, kind):
    before = files_of(repo)
    for title in ("", "   ", "\n"):
        with pytest.raises(ValueError, match="title must not be empty"):
            _create(kind, repo, paper, title=title)
    assert files_of(repo) == before


@pytest.mark.parametrize("kind", ["question", "decision", "literature", "log"])
def test_a_failed_write_leaves_no_partial_file(repo, paper, files_of, monkeypatch, kind):
    def write_half_then_fail(path, meta, body):
        path.write_text("---\ntitle: half", encoding="utf-8")
        raise OSError("disk full")

    monkeypatch.setattr(newfile.frontmatter, "write", write_half_then_fail)
    before = files_of(repo)  # for literature this also covers the copied PDF
    with pytest.raises(OSError, match="disk full"):
        _create(kind, repo, paper)
    assert files_of(repo) == before


@pytest.mark.parametrize("kind", ALL)
def test_existing_file_is_refused_and_left_untouched(repo, paper, kind):
    first = _create(kind, repo, paper)
    first.write_text(first.read_text(encoding="utf-8") + "\nhand edit\n", encoding="utf-8")
    edited = first.read_bytes()
    shown = re.escape(first.relative_to(repo).as_posix())
    with pytest.raises(FileExistsError, match=shown):
        _create(kind, repo, paper)
    assert first.read_bytes() == edited


@pytest.mark.parametrize("kind", ALL)
def test_generated_files_keep_no_template_notes_or_unfilled_tokens(repo, paper, kind):
    text = _create(kind, repo, paper).read_text(encoding="utf-8")
    assert "<!--" not in text
    assert not re.search(r"\{\w+\}", text)
