"""Tests for ra.stats and 'python protocol/ra.py stats': the pilot metrics of spec §16.

test_stats_on_example pins the counts of the example project (conftest.py: example_repo). The
other tests build the smallest project on the repo fixture that shows one count.
"""

import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from conftest import _commit_all, _decision, _lit
from ra.frontmatter import parse, write
from ra.newfile import new_question, new_topic
from ra.stats import stats

KEYS = [
    "papers", "claims", "unverified_claims", "disputed_claims",
    "duplicate_records", "decisions_edited", "open_questions", "conflict_facts",
]
LEE = "Lee · codex · 2026-10-27"  # not Fan, the author of every claim that _lit writes
FACT = "- {text} (src: seed2024-x §1 · Fan/codex 2026-10-25 · approved Fan · {status})\n"


def _annotate(path: Path, claim: str, *sub_bullets: str) -> None:
    """Add sub-bullets such as 'verified-by: ...' at the end of the claim whose text is claim."""
    meta, body = parse(path)
    lines = body.split("\n")
    end = lines.index(f"- {claim}") + 1
    while end < len(lines) and lines[end].startswith("  - "):
        end += 1
    lines[end:end] = [f"  - {text}" for text in sub_bullets]
    write(path, meta, "\n".join(lines))


def _topic(repo: Path, topic: str, *facts: tuple[str, str]) -> None:
    """Create knowledge/<topic>.md with these (text, status) facts, in the spec §11 form."""
    path = new_topic(repo, topic, f"{topic} facts")
    with path.open("a", encoding="utf-8", newline="") as handle:
        for text, status in facts:
            handle.write(FACT.format(text=text, status=status))


def _question(repo: Path, slug: str, status: str) -> None:
    """Create the question questions/Q-2026-10-25-<slug>.md and set its status."""
    path = new_question(repo, slug, "t", "Fan", "codex", date(2026, 10, 25))
    meta, body = parse(path)
    meta["status"] = status
    write(path, meta, body)


def test_stats_on_example(example_repo):
    # Lee verified two claims of smith2024-plume-goes and disputed its third; jones2023-plume-unet
    # has two claims nobody has verified; brown2022-cloud-masks was read and rejected.
    assert stats(example_repo) == {
        "papers": 3, "claims": 5, "unverified_claims": 3, "disputed_claims": 1,
        "duplicate_records": 0, "decisions_edited": 0, "open_questions": 2, "conflict_facts": 2,
    }


def test_an_empty_project_is_all_zeros(repo):
    result = stats(repo)
    assert list(result) == KEYS
    assert set(result.values()) == {0}


def test_a_directory_that_is_no_project_is_all_zeros(tmp_path):
    assert set(stats(tmp_path).values()) == {0}


# --- papers and claims -----------------------------------------------------------------------


def test_papers_and_claims_are_counted_over_all_records(repo, make_pdf):
    _lit(repo, make_pdf, "a2024-x", claims=(("c1", "p.1"), ("c2", "p.2")))
    _lit(repo, make_pdf, "b2024-y", claims=(("c3", "p.3"),))
    _lit(repo, make_pdf, "c2024-z", claims=())  # a record with no claim is still a paper
    result = stats(repo)
    assert (result["papers"], result["claims"]) == (3, 3)


@pytest.mark.parametrize(
    ("verified_by", "unverified"),
    [
        ("—", 1),  # nobody has verified the claim
        (LEE, 0),  # another person has
        ("Fan · claude-code · 2026-10-27", 1),  # the author on another platform: no second reader
        (f"Fan · claude-code · 2026-10-27; {LEE}", 0),  # a second reader among several
    ],
)
def test_a_claim_is_unverified_until_another_person_verifies_it(
    repo, make_pdf, verified_by, unverified
):
    path = _lit(repo, make_pdf, "a2024-x", claims=(("c", "p.1"),))
    _annotate(path, "c", f"verified-by: {verified_by}")
    assert stats(repo)["unverified_claims"] == unverified


def test_a_claim_without_a_by_is_unverified_only_when_nobody_verified_it(repo, make_pdf):
    path = _lit(repo, make_pdf, "a2024-x", claims=(("c1", "p.1"), ("c2", "p.2")))
    meta, body = parse(path)
    write(path, meta, body.replace("  - by: Fan · codex · 2026-10-25\n", ""))
    _annotate(path, "c2", "verified-by: Fan · codex · 2026-10-26")  # no author to differ from
    assert stats(repo)["unverified_claims"] == 1


def test_a_disputed_claim_is_disputed_and_still_unverified(repo, make_pdf):
    claims = (("c1", "p.1"), ("c2", "p.2"), ("c3", "p.3"))
    path = _lit(repo, make_pdf, "a2024-x", claims=claims)
    two_disputes = f"{LEE} — the table says 9.1; Kim · codex · 2026-10-28 — same"
    _annotate(path, "c1", f"disputed-by: {two_disputes}")
    _annotate(path, "c2", f"verified-by: {LEE}", "disputed-by: —")
    result = stats(repo)
    assert (result["claims"], result["disputed_claims"], result["unverified_claims"]) == (3, 1, 2)


@pytest.mark.parametrize("arxiv", [None, "2401.10250"])
def test_two_records_with_one_doi_are_one_duplicate(repo, make_pdf, arxiv):
    _lit(repo, make_pdf, "a2024-x", doi="10.1/same", arxiv=arxiv)
    _lit(repo, make_pdf, "b2024-y", doi="10.1/same", arxiv=arxiv)  # one pair, whatever the ids
    _lit(repo, make_pdf, "c2024-z", doi="10.1/other")
    assert stats(repo)["duplicate_records"] == 1


# --- decisions, questions, knowledge ---------------------------------------------------------


def test_an_accepted_decision_edited_in_place_is_counted(repo):
    path = _decision(repo, "eval-metric", status="proposed")
    _commit_all(repo, "[decision] proposed")
    meta, body = parse(path)
    meta["status"] = "accepted"
    meta["accepted-by"] = "Fan · 2026-10-26"
    write(path, meta, body)
    _commit_all(repo, "[decision] accepted")
    assert stats(repo)["decisions_edited"] == 0
    write(path, meta, body + "\nchanged rationale\n")
    _commit_all(repo, "oops")
    assert stats(repo)["decisions_edited"] == 1


def test_only_questions_with_status_open_are_counted(repo):
    for slug, status in (("q1", "open"), ("q2", "open"), ("q3", "answered"), ("q4", "dropped")):
        _question(repo, slug, status)
    assert stats(repo)["open_questions"] == 2


def test_every_fact_line_in_conflict_is_counted(repo):
    _topic(
        repo, "goes-abi",
        ("band 7 is 3.9 µm with 2 km nadir resolution", "CONFLICT with line below"),
        ("band 7 nadir resolution is 1 km", "CONFLICT with line above"),
        ("band 1 is 0.47 µm", "ok"),
        ("band 2 is 0.64 µm", "superseded by D-2026-11-01-resolve-conflict"),
    )
    _topic(repo, "loss", ("Dice loss alone labels cloud edges as smoke", "conflict with goes-abi"))
    _topic(repo, "labels", ("HMS polygons over-cover thin smoke", "ok"))
    assert stats(repo)["conflict_facts"] == 3  # a status is read in any case, as ra.knowledge does


def test_facts_in_the_glossary_count_like_those_of_any_topic(repo):
    # glossary.md holds the project's terms as fact lines (PROTOCOL.md §3, propose-knowledge
    # step 2); ra.check reads them like the facts of a topic.
    with (repo / "knowledge" / "glossary.md").open("a", encoding="utf-8", newline="") as handle:
        handle.write(FACT.format(text="plume means smoke", status="CONFLICT with line below"))
        handle.write(FACT.format(text="plume means cloud", status="CONFLICT with line above"))
    assert stats(repo)["conflict_facts"] == 2


def test_registry_lines_are_not_facts(repo):
    new_topic(repo, "goes-abi", "GOES-16 ABI facts (bands and resolutions)")  # ends in a ')'
    new_topic(repo, "loss", "loss functions")
    registry = (repo / "knowledge" / "README.md").read_text(encoding="utf-8")
    assert "- goes-abi — GOES-16 ABI facts (bands and resolutions)\n" in registry
    assert stats(repo)["conflict_facts"] == 0


# --- bad content never raises ----------------------------------------------------------------


def test_files_that_do_not_parse_and_other_files_are_skipped(repo, make_pdf):
    record = _lit(repo, make_pdf, "a2024-x", claims=(("c", "p.1"),))
    _question(repo, "q1", "open")
    _topic(repo, "goes-abi", ("band 7 is 3.9 µm", "CONFLICT with line below"))
    text = record.read_text(encoding="utf-8")
    literature, questions, knowledge = repo / "literature", repo / "questions", repo / "knowledge"
    # Each broken file sorts before the valid one, so a scan that stopped at it would miss that.
    (literature / "0-broken.md").write_text("no frontmatter\n", encoding="utf-8")
    (questions / "0-broken.md").write_text("---\nstatus: [open\n---\n", encoding="utf-8")
    (knowledge / "0-broken.md").write_bytes(b"\xff\xfe\x00 not UTF-8\n")
    # Not records: a dot-file, a file that is not Markdown, a folder named like one.
    (literature / ".copy.md").write_text(text, encoding="utf-8")
    (literature / "notes.txt").write_text(text, encoding="utf-8")
    (literature / "folder.md").mkdir()
    (knowledge / ".draft.md").write_text(
        FACT.format(text="x", status="CONFLICT with line below"), encoding="utf-8"
    )
    assert stats(repo) == {
        **dict.fromkeys(KEYS, 0),
        "papers": 1, "claims": 1, "unverified_claims": 1, "open_questions": 1, "conflict_facts": 1,
    }


def test_a_topic_file_that_cannot_be_read_is_skipped(repo, monkeypatch):
    _topic(repo, "goes-abi", ("band 7 is 3.9 µm", "CONFLICT with line below"))
    opened = Path.open

    def refuse(self, *args, **kwargs):
        if self.name == "goes-abi.md":
            raise PermissionError(13, "Permission denied")
        return opened(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", refuse)
    assert stats(repo)["conflict_facts"] == 0


# --- the command -----------------------------------------------------------------------------


def test_the_command_prints_one_line_per_count_and_exits_0(repo, make_pdf):
    _lit(repo, make_pdf, "a2024-x", claims=(("c1", "p.1"), ("c2", "p.2")))
    done = subprocess.run(
        [sys.executable, str(repo / "protocol" / "ra.py"), "stats"],
        cwd=repo, capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert (done.returncode, done.stderr) == (0, "")
    assert done.stdout == (
        "papers: 1\nclaims: 2\nunverified_claims: 2\ndisputed_claims: 0\nduplicate_records: 0\n"
        "decisions_edited: 0\nopen_questions: 0\nconflict_facts: 0\n"
    )
    assert [line.split(": ")[0] for line in done.stdout.splitlines()] == KEYS
