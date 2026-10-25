"""Tests for the new_* creators in ra.newfile.

Rules shared by every creator are in test_newfile_rules.py, the template files in
test_templates.py and the command line in test_cli_new.py.
"""

import copy
import re
from datetime import date, datetime

import pytest
from ra import newfile
from ra.frontmatter import parse
from ra.newfile import (
    DECISION_KEYS,
    LITERATURE_KEYS,
    LOG_KEYS,
    QUESTION_KEYS,
    new_decision,
    new_literature,
    new_log,
    new_question,
    new_topic,
)

DAY = date(2026, 10, 25)
WHO = {"person": "Fan", "agent": "codex", "date": "2026-10-25"}


# --- the brief's tests -------------------------------------------------------------------


def test_question_path_and_frontmatter(repo):
    p = new_question(
        repo, "plume-baselines", "What are the strongest baselines?",
        "Fan", "claude-code", date(2026, 10, 25),
    )
    assert p == repo/"questions"/"Q-2026-10-25-plume-baselines.md"
    m, _ = parse(p)
    assert m["id"] == "Q-2026-10-25-plume-baselines" and m["status"] == "open"
    assert m["proposed-by"] == {"person": "Fan", "agent": "claude-code", "date": "2026-10-25"}


def test_same_slug_same_day_refused(repo):
    new_question(repo, "x", "t", "Fan", "codex", date(2026, 10, 25))
    with pytest.raises(FileExistsError):
        new_question(repo, "x", "t2", "Lee", "claude-code", date(2026, 10, 25))


def test_literature_copies_pdf_and_sets_reader(repo, make_pdf):
    src = repo.parent/"s.pdf"
    make_pdf(src, "hello")
    p = new_literature(
        repo, "smith2024-plume-goes",
        {"title": "T", "year": 2024, "person": "Fan", "agent": "codex", "date": "2026-10-25"},
        src,
    )
    m, _ = parse(p)
    assert (repo/"literature"/"pdf"/"smith2024-plume-goes.pdf").exists()
    assert m["pdf"] == "literature/pdf/smith2024-plume-goes.pdf"
    assert m["readers"][0]["read"] == "full-text"


def test_log_filename_uses_start_time(repo):
    p = new_log(repo, "fan", "codex", datetime(2026, 10, 25, 14, 32))
    assert p.name == "2026-10-25-fan-codex-1432.md"


def test_topic_registers_in_readme(repo):
    new_topic(repo, "goes-abi", "GOES-16 ABI instrument facts")
    readme = (repo/"knowledge"/"README.md").read_text(encoding="utf-8")
    assert "- goes-abi — GOES-16 ABI instrument facts" in readme


def test_bad_slug_rejected(repo):
    with pytest.raises(ValueError):
        new_decision(repo, "Eval Metric", "t", "Fan", "codex", date(2026, 10, 25), [])


# --- question and decision ---------------------------------------------------------------


def test_question_writes_every_key_in_order(repo):
    p = new_question(repo, "plume-baselines", "What are the best baselines?", "Fan", "codex", DAY)
    m, body = parse(p)
    assert list(m) == list(QUESTION_KEYS)
    assert m["title"] == "What are the best baselines?"
    assert [m[k] for k in ("approved-by", "answered-by", "closed-by")] == [None, None, None]
    assert list(m["proposed-by"]) == ["person", "agent", "date"]
    assert body.startswith("\n## Context\n") and "## Working notes" in body


def test_decision_path_and_frontmatter(repo):
    links = ["Q-2026-10-25-plume-baselines", "literature/smith2024-plume-goes.md"]
    title = "Use mIoU as the primary metric"
    p = new_decision(repo, "eval-metric", title, "Fan", "codex", DAY, links)
    assert p == repo/"decisions"/"D-2026-10-25-eval-metric.md"
    m, body = parse(p)
    assert list(m) == list(DECISION_KEYS)
    assert m["id"] == "D-2026-10-25-eval-metric" and m["status"] == "proposed"
    assert m["proposed-by"] == {"person": "Fan", "agent": "codex", "date": "2026-10-25"}
    assert m["links"] == links
    assert [m[k] for k in ("accepted-by", "supersedes", "superseded-by")] == [None, None, None]
    headings = ("Decision", "Alternatives considered", "Rationale and evidence", "Consequences")
    assert re.findall(r"^## (.+)$", body, re.MULTILINE) == list(headings)


def test_decision_without_links_writes_an_empty_list(repo):
    m, _ = parse(new_decision(repo, "x", "t", "Fan", "codex", DAY, []))
    assert m["links"] == []


# --- literature --------------------------------------------------------------------------


def test_literature_writes_every_key_in_order(repo, paper):
    meta = {**WHO, "title": "Smoke plume segmentation", "year": 2024, "venue": "RSE"}
    p = new_literature(repo, "smith2024-plume-goes", meta, paper)
    assert p == repo/"literature"/"smith2024-plume-goes.md"
    m, _ = parse(p)
    assert list(m) == list(LITERATURE_KEYS)
    assert m["citekey"] == "smith2024-plume-goes" and m["title"] == "Smoke plume segmentation"
    assert m["year"] == 2024 and m["venue"] == "RSE"
    assert (m["authors"], m["bears-on"], m["related"]) == ([], [], [])
    assert [m[k] for k in ("doi", "arxiv", "relevance", "code", "data")] == [None] * 5
    reader = {"person": "Fan", "agent": "codex", "date": "2026-10-25", "read": "full-text"}
    assert m["readers"] == [reader]
    assert not {"person", "agent", "date"} & set(m)
    copied = repo/"literature"/"pdf"/"smith2024-plume-goes.pdf"
    assert copied.read_bytes() == paper.read_bytes()


def test_literature_every_field_and_unicode_round_trip(repo, paper):
    meta = {
        "title": "Mapping smoke at 3.9 µm – a study", "authors": ["张三", "Lee K"], "year": 2024,
        "venue": "Remote Sensing of Environment", "doi": "10.1016/j.rse.2024.113",
        "arxiv": "2401.10250", "relevance": "core", "bears-on": ["Q-2026-10-25-plume-baselines"],
        "code": "https://github.com/x/y", "data": "https://zenodo.org/records/1",
        "related": ["jones2023-plume-unet"],
    }
    m, _ = parse(new_literature(repo, "zhang2024-smoke", {**WHO, **meta}, paper))
    assert {key: m[key] for key in meta} == meta


def test_literature_body_has_the_spec_sections_and_no_claims(repo, paper):
    _, body = parse(new_literature(repo, "smith2024-plume-goes", dict(WHO), paper))
    headings = ["Summary", "Why it matters here", "Claims for this project", "Notes", "BibTeX"]
    assert re.findall(r"^## (.+)$", body, re.MULTILINE) == headings
    claims = body.split("## Claims for this project\n", 1)[1].split("\n## ", 1)[0]
    assert claims.strip() == ""
    assert "@article{smith2024-plume-goes, ...}" in body


def test_literature_accepts_a_date_object(repo, paper):
    meta = {"person": "Fan", "agent": "codex", "date": DAY}
    m, _ = parse(new_literature(repo, "a2024-x", meta, paper))
    assert m["readers"][0]["date"] == "2026-10-25"


def test_literature_does_not_modify_meta(repo, paper):
    meta = {**WHO, "title": "T", "authors": ["A"]}
    before = copy.deepcopy(meta)
    new_literature(repo, "a2024-x", meta, paper)
    assert meta == before


@pytest.mark.parametrize(
    "bad",
    [
        {"foo": 1},
        {"pdf": "literature/pdf/other.pdf"},
        {"readers": []},
        {"citekey": "other"},
        {"person": ""},
        {"person": "   "},
        {"agent": "claude"},
        {"date": "25/10/2026"},
        {"date": "2026-13-01"},
        {"relevance": "important"},
        {"authors": "Smith J"},
    ],
    ids=[
        "unknown-key", "pdf-is-derived", "readers-is-derived", "citekey-is-derived",
        "empty-person", "blank-person", "bad-agent", "bad-date-format", "impossible-date",
        "bad-relevance", "authors-not-a-list",
    ],
)
def test_literature_rejects_bad_meta_and_writes_nothing(repo, paper, files_of, bad):
    before = files_of(repo)
    with pytest.raises(ValueError):
        new_literature(repo, "a2024-x", {**WHO, **bad}, paper)
    assert files_of(repo) == before


@pytest.mark.parametrize("missing", ["person", "agent", "date"])
def test_literature_meta_must_name_the_reader(repo, paper, missing):
    meta = {key: value for key, value in WHO.items() if key != missing}
    with pytest.raises(ValueError, match=missing):
        new_literature(repo, "a2024-x", meta, paper)


def test_literature_missing_pdf_source_raises_and_writes_nothing(repo, tmp_path, files_of):
    before = files_of(repo)
    with pytest.raises(FileNotFoundError, match="nope.pdf"):
        new_literature(repo, "a2024-x", dict(WHO), tmp_path/"nope.pdf")
    assert files_of(repo) == before


def test_literature_refuses_when_only_the_pdf_target_exists(repo, paper):
    target = repo/"literature"/"pdf"/"a2024-x.pdf"
    target.write_bytes(b"old")
    with pytest.raises(FileExistsError, match="a2024-x.pdf"):
        new_literature(repo, "a2024-x", dict(WHO), paper)
    assert target.read_bytes() == b"old"
    assert not (repo/"literature"/"a2024-x.md").exists()


def test_literature_write_failure_removes_the_copied_pdf(repo, paper, files_of, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(newfile.frontmatter, "write", fail)
    before = files_of(repo)
    with pytest.raises(OSError, match="disk full"):
        new_literature(repo, "a2024-x", dict(WHO), paper)
    assert files_of(repo) == before


# --- log ---------------------------------------------------------------------------------


def test_log_frontmatter_and_person_spelling(repo):
    p = new_log(repo, "Fan", "codex", datetime(2026, 10, 25, 14, 32, 59))
    assert p == repo/"log"/"2026-10-25-fan-codex-1432.md"
    m, body = parse(p)
    assert list(m) == list(LOG_KEYS)
    assert m == {
        "date": "2026-10-25", "person": "Fan", "agent": "codex",
        "session": "14:32–", "dual-run": None,
    }
    headings = ["Done", "Tried and failed", "Unfinished", "Suggested next step", "Files touched"]
    assert re.findall(r"^## (.+)$", body, re.MULTILINE) == headings


def test_log_person_must_be_usable_in_a_file_name(repo):
    with pytest.raises(ValueError, match="person"):
        new_log(repo, "Fan Zhou", "codex", datetime(2026, 10, 25, 14, 32))
    assert not list((repo/"log").iterdir())


# --- topic -------------------------------------------------------------------------------


def test_topic_file_is_a_two_line_header_without_frontmatter(repo):
    p = new_topic(repo, "goes-abi", "GOES-16 ABI instrument facts")
    assert p == repo/"knowledge"/"goes-abi.md"
    assert p.read_text(encoding="utf-8") == "# goes-abi\nGOES-16 ABI instrument facts\n\n"


def test_topic_registry_line_starts_on_its_own_line(repo):
    registry = repo/"knowledge"/"README.md"
    registry.write_text("# Topic registry\n\n- old — Old facts", encoding="utf-8", newline="")
    new_topic(repo, "goes-abi", "GOES-16 ABI instrument facts")
    assert registry.read_text(encoding="utf-8") == (
        "# Topic registry\n\n- old — Old facts\n- goes-abi — GOES-16 ABI instrument facts\n"
    )


@pytest.mark.parametrize("scope", ["", "   ", "two\nlines", "ends with newline\n", "cr\rhere"])
def test_topic_scope_must_be_one_non_empty_line(repo, files_of, scope):
    before = files_of(repo)
    registry = (repo/"knowledge"/"README.md").read_bytes()
    with pytest.raises(ValueError, match="scope"):
        new_topic(repo, "goes-abi", scope)
    assert files_of(repo) == before
    assert (repo/"knowledge"/"README.md").read_bytes() == registry


def test_topic_needs_the_registry_file(repo):
    (repo/"knowledge"/"README.md").unlink()
    with pytest.raises(FileNotFoundError, match="README"):
        new_topic(repo, "goes-abi", "GOES-16 ABI instrument facts")
    assert not (repo/"knowledge"/"goes-abi.md").exists()


def test_topic_registration_failure_removes_the_topic_file(repo, files_of, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(newfile, "_append_line", fail)
    before = files_of(repo)
    with pytest.raises(OSError, match="disk full"):
        new_topic(repo, "goes-abi", "GOES-16 ABI instrument facts")
    assert files_of(repo) == before
