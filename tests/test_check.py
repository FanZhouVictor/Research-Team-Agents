"""Tests for ra.check, the repository validator behind 'python protocol/ra.py check'.

DECISION_EDITED, the rule that reads git history, is tested in test_check_decisions.py.
"""

import os
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import pytest
from conftest import _decision, _lit
from ra import check, knowledge
from ra.check import Finding, run_checks
from ra.frontmatter import parse, write
from ra.newfile import (
    DECISION_KEYS,
    LITERATURE_KEYS,
    LOG_KEYS,
    QUESTION_KEYS,
    TEMPLATES_DIR,
    new_log,
    new_question,
    new_topic,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "template" / "protocol" / "ra.py"
DAY = date(2026, 10, 25)
FOLDERS = ("questions", "decisions", "literature", "literature/pdf", "log", "knowledge")
FACT = (
    "- GOES-16 ABI band 7 is 3.9 µm with 2 km nadir resolution "
    "(src: smith2024-plume-goes §2.1 p.3 · Fan/codex 2026-10-25 · approved Fan · ok)"
)


def _found(repo: Path) -> set[tuple[str, str]]:
    """(code, POSIX path) of every finding in repo."""
    return {(f.code, f.path.as_posix()) for f in run_checks(repo)}


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="")


def _line_of(path: Path, line: str) -> int:
    """The 1-based number of the line of path that equals line."""
    return path.read_text(encoding="utf-8").split("\n").index(line) + 1


def _dispute(record: Path, claim: str) -> None:
    """Add a disputed-by sub-bullet to the claim of a _lit record whose text is claim."""
    text = record.read_text(encoding="utf-8")
    end = text.index("\n", text.index("  - by: ", text.index(f"- {claim}\n"))) + 1
    dispute = "  - disputed-by: Lee · claude-code · 2026-10-28 — misread\n"
    _write(record, text[:end] + dispute + text[end:])


def _topic(repo: Path, *lines: str) -> Path:
    """knowledge/goes-abi.md made (and registered) by new_topic, with lines appended."""
    path = new_topic(repo, "goes-abi", "GOES-16 ABI instrument facts")
    with path.open("a", encoding="utf-8", newline="") as handle:
        handle.writelines(f"{line}\n" for line in lines)
    return path


# A valid file of each frontmatter kind, made by make(repo, make_pdf), and its required keys.
KINDS = {
    "question": (lambda repo, make_pdf: new_question(repo, "x", "t", "Fan", "codex", DAY),
                 QUESTION_KEYS),
    "decision": (lambda repo, make_pdf: _decision(repo, "x", status="proposed"), DECISION_KEYS),
    "literature": (lambda repo, make_pdf: _lit(repo, make_pdf, "a2024-x"), LITERATURE_KEYS),
    "log": (lambda repo, make_pdf: new_log(repo, "Fan", "codex", datetime(2026, 10, 25, 14, 32)),
            LOG_KEYS),
}


# --- the brief's tests (its two DECISION_EDITED tests are in test_check_decisions.py) ----


def test_claim_without_where_flagged(repo, make_pdf):
    _lit(repo, make_pdf, "a2024-x", claims=[("Some claim", None)])
    assert {f.code for f in run_checks(repo)} == {"CLAIM_NO_WHERE"}


def test_pdf_path_must_match_citekey(repo, make_pdf):
    p = _lit(repo, make_pdf, "a2024-x")
    m, b = parse(p)
    m["pdf"] = "literature/pdf/other.pdf"
    write(p, m, b)
    assert "PDF_MISSING" in {f.code for f in run_checks(repo)}
    expected = "pdf: is literature/pdf/other.pdf, expected literature/pdf/a2024-x.pdf"
    assert run_checks(repo) == [Finding("PDF_MISSING", Path("literature/a2024-x.md"), expected)]


# --- clean repositories ------------------------------------------------------------------


def test_fresh_repo_has_no_findings(repo):
    assert run_checks(repo) == []


def test_valid_files_of_every_kind_and_dot_files_give_no_findings(repo, make_pdf):
    new_question(repo, "plume-baselines", "Which baselines?", "Fan", "claude-code", DAY)
    _decision(repo, "eval-metric", status="proposed")
    _lit(repo, make_pdf, "smith2024-plume-goes", doi="10.1/a", arxiv="2401.10250")
    _lit(repo, make_pdf, "lee2023-abi-spec", doi="10.1/b", claims=[("x", "Table 1"), ("y", "§2")])
    new_log(repo, "Fan Zhou", "codex", datetime(2026, 10, 25, 14, 32))
    log = new_log(repo, "张三", "claude-code", datetime(2026, 10, 25, 9, 5))
    _topic(repo, FACT)
    for folder in FOLDERS:
        (repo / folder / ".gitkeep").touch()
        (repo / folder / ".DS_Store").write_bytes(b"\x00\x01")
    assert log.name == "2026-10-25-张三-claude-code-0905.md"
    assert run_checks(repo) == []


def test_root_files_and_protocol_folder_are_not_scanned(repo):
    shutil.copytree(TEMPLATES_DIR, repo / "protocol" / "templates", dirs_exist_ok=True)
    _write(repo / "protocol" / "notes.txt", "x\n")
    for name in ("PROTOCOL.md", "CLAUDE.md", "AGENTS.md", "notes.txt"):
        _write(repo / name, "no frontmatter\n")
    assert run_checks(repo) == []


# --- FM_INVALID --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content",
    [
        b"---\ntitle: [unclosed\n---\n",
        b"no frontmatter block\n",
        b"---\nid: x\n",
        b"---\n- a\n- b\n---\n",
        b"---\nid: \xff\n---\n",
    ],
    ids=["yaml-error", "no-block", "unterminated", "not-a-mapping", "not-utf8"],
)
def test_unparseable_frontmatter_is_one_fm_invalid_finding(repo, content):
    (repo / "questions" / "Q-2026-10-25-x.md").write_bytes(content)
    [finding] = run_checks(repo)
    assert (finding.code, finding.path) == ("FM_INVALID", Path("questions/Q-2026-10-25-x.md"))
    assert "\n" not in finding.message and str(repo) not in finding.message


@pytest.mark.parametrize("kind", KINDS)
def test_missing_keys_are_one_fm_invalid_finding_listing_them_in_order(repo, make_pdf, kind):
    make, keys = KINDS[kind]
    path = make(repo, make_pdf)
    _, body = parse(path)
    write(path, {}, body)
    found = [f.message for f in run_checks(repo) if f.code == "FM_INVALID"]
    assert found == [f"missing key(s): {', '.join(keys)}"]


@pytest.mark.parametrize(("kind", "key"), [("question", "id"), ("decision", "id"),
                                           ("literature", "citekey")])
def test_id_or_citekey_must_equal_the_file_name(repo, make_pdf, kind, key):
    path = KINDS[kind][0](repo, make_pdf)
    meta, body = parse(path)
    meta[key] = "other-name"
    write(path, meta, body)
    [finding] = run_checks(repo)
    assert (finding.code, finding.path) == ("FM_INVALID", path.relative_to(repo))
    assert finding.message == f"{key} is 'other-name', expected '{path.stem}' (the file name)"


@pytest.mark.skipif(
    os.name == "nt" or getattr(os, "geteuid", lambda: 1)() == 0,
    reason="needs POSIX file permissions and a non-root user",
)
def test_unreadable_file_is_fm_invalid_not_an_exception(repo):
    path = KINDS["question"][0](repo, None)
    path.chmod(0)
    try:
        [finding] = run_checks(repo)
    finally:
        path.chmod(0o644)
    assert finding.code == "FM_INVALID" and finding.message.startswith("cannot read the file")


# --- BAD_FILENAME ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rel",
    [
        "questions/notes.txt",
        "questions/q-2026-10-25-lower-q.md",
        "questions/Q-2026-10-25-Upper.md",
        "decisions/D-2026-10-25.md",
        "decisions/D-26-10-25-short-year.md",
        "literature/Smith2024.md",
        "literature/foo.pdf",
        "literature/pdf/a2024 x.pdf",
        "literature/pdf/a2024-x.md",
        "log/2026-10-25-fan-gpt-1432.md",
        "log/2026-10-25-fan-codex-14h32.md",
        "knowledge/GOES ABI.md",
        "knowledge/notes.txt",
    ],
)
def test_misnamed_file_is_bad_filename(repo, rel):
    _write(repo / rel, "x\n")
    assert ("BAD_FILENAME", rel) in _found(repo)


def test_bad_filename_message_states_the_rule(repo):
    _write(repo / "questions" / "notes.txt", "x\n")
    expected = "the name should be Q-<YYYY-MM-DD>-<slug>.md, slug [a-z0-9-]+"
    assert run_checks(repo) == [Finding("BAD_FILENAME", Path("questions/notes.txt"), expected)]


# --- CLAIM_NO_WHERE ----------------------------------------------------------------------


@pytest.mark.parametrize("where", [None, "", "—", " — "], ids=["absent", "empty", "dash", "spaced"])
def test_claim_with_absent_empty_or_dash_where_is_flagged(repo, make_pdf, where):
    _lit(repo, make_pdf, "a2024-x", claims=[("Located claim", "p.1"), ("Bad claim", where)])
    [finding] = run_checks(repo)
    assert (finding.code, finding.path) == ("CLAIM_NO_WHERE", Path("literature/a2024-x.md"))
    assert '"Bad claim"' in finding.message


def test_claim_finding_gives_the_file_line_and_a_shortened_text(repo, make_pdf):
    text = "Transformer segmentation beats U-Net on every GOES-16 plume mask of the held-out set"
    path = _lit(repo, make_pdf, "a2024-x", claims=[("Located", "p.1"), (text, None)])
    [finding] = run_checks(repo)
    assert finding.message.startswith(f"line {_line_of(path, f'- {text}')}: claim without a where")
    assert text[:50] in finding.message and text not in finding.message


# --- PDF_MISSING -------------------------------------------------------------------------


def test_pdf_key_empty_or_absent_is_pdf_missing(repo, make_pdf):
    path = _lit(repo, make_pdf, "a2024-x")
    meta, body = parse(path)
    meta["pdf"] = None
    write(path, meta, body)
    assert _found(repo) == {("PDF_MISSING", "literature/a2024-x.md")}
    del meta["pdf"]
    write(path, meta, body)
    assert _found(repo) == {("PDF_MISSING", "literature/a2024-x.md"),
                            ("FM_INVALID", "literature/a2024-x.md")}


def test_pdf_file_absent_is_pdf_missing(repo, make_pdf):
    _lit(repo, make_pdf, "a2024-x")
    (repo / "literature" / "pdf" / "a2024-x.pdf").unlink()
    assert run_checks(repo) == [
        Finding("PDF_MISSING", Path("literature/a2024-x.md"),
                "literature/pdf/a2024-x.pdf does not exist")
    ]


# --- DUP_LITERATURE ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "other",
    ["10.1016/j.rse.2024.1", " doi:10.1016/J.RSE.2024.1", "https://doi.org/10.1016/j.rse.2024.1",
     "http://doi.org/10.1016/J.rse.2024.1", "https://dx.doi.org/10.1016/j.RSE.2024.1"],
)
def test_same_doi_after_normalising_is_dup_on_the_later_file(repo, make_pdf, other):
    _lit(repo, make_pdf, "a2024-x", doi="10.1016/J.RSE.2024.1")
    _lit(repo, make_pdf, "b2024-y", doi=other)
    _lit(repo, make_pdf, "c2024-z", doi="10.1016/j.rse.2024.10")
    assert run_checks(repo) == [
        Finding("DUP_LITERATURE", Path("literature/b2024-y.md"),
                "same doi 10.1016/j.rse.2024.1 as literature/a2024-x.md")
    ]


@pytest.mark.parametrize(
    "other",
    ["2401.10250v2", "arXiv:2401.10250", "https://arxiv.org/abs/2401.10250v3", " 2401.10250 "],
)
def test_same_arxiv_id_after_normalising_is_dup(repo, make_pdf, other):
    _lit(repo, make_pdf, "a2024-x", arxiv="2401.10250")
    _lit(repo, make_pdf, "b2024-y", arxiv=other)
    _lit(repo, make_pdf, "c2024-z", arxiv="2401.10251")
    assert _found(repo) == {("DUP_LITERATURE", "literature/b2024-y.md")}


def test_one_dup_finding_per_pair_naming_every_shared_key(repo, make_pdf):
    _lit(repo, make_pdf, "a2024-x", doi="10.1/same", arxiv="2401.00001")
    _lit(repo, make_pdf, "b2024-y", doi="10.1/same", arxiv="2401.00001v2")
    _lit(repo, make_pdf, "c2024-z", doi="10.1/same")
    assert [(f.path.as_posix(), f.message) for f in run_checks(repo)] == [
        ("literature/b2024-y.md",
         "same doi 10.1/same and arxiv 2401.00001 as literature/a2024-x.md"),
        ("literature/c2024-z.md", "same doi 10.1/same as literature/a2024-x.md"),
        ("literature/c2024-z.md", "same doi 10.1/same as literature/b2024-y.md"),
    ]


# --- DISPUTED_IN_KNOWLEDGE ---------------------------------------------------------------


def test_fact_citing_a_disputed_claim_is_flagged(repo, make_pdf):
    claims = [("Band 7 is 3.9 µm", "§2.1  P.3")]  # where: spacing and case differ from FACT
    record = _lit(repo, make_pdf, "smith2024-plume-goes", claims=claims)
    _dispute(record, "Band 7 is 3.9 µm")
    topic = _topic(repo, "- A line that is not a fact", FACT)
    assert run_checks(repo) == [
        Finding("DISPUTED_IN_KNOWLEDGE", Path("knowledge/goes-abi.md"),
                f'line {_line_of(topic, FACT)}: source smith2024-plume-goes "§2.1 p.3" '
                "is a disputed claim")
    ]


def test_fact_citing_an_undisputed_claim_an_unknown_source_or_in_a_comment_passes(repo, make_pdf):
    record = _lit(repo, make_pdf, "smith2024-plume-goes", claims=[("Band 7", "§2.1 p.3"),
                                                                   ("Other", "Table 1")])
    _dispute(record, "Other")
    commented = FACT.replace("§2.1 p.3", "Table 1")
    _topic(repo, FACT, FACT.replace("smith2024-plume-goes", "nobody2020-none"),
           "<!--", commented, "-->")
    assert run_checks(repo) == []


# --- TOPIC_UNREGISTERED ------------------------------------------------------------------


def test_topic_without_its_registry_line_is_unregistered(repo):
    _write(repo / "knowledge" / "goes-abi.md", "# goes-abi\nGOES facts\n")
    _write(repo / "knowledge" / "plumes.md", "# plumes\nPlume facts\n")
    _write(repo / "knowledge" / "README.md",
           "# Topic registry\n\n  - plumes — Plume facts  \n- goes-abi-old — x\n- goes-abi: y\n")
    assert run_checks(repo) == [
        Finding("TOPIC_UNREGISTERED", Path("knowledge/goes-abi.md"),
                "no '- goes-abi — <scope>' line in knowledge/README.md")
    ]


def test_without_a_registry_every_topic_is_unregistered_but_not_readme_or_glossary(repo):
    new_topic(repo, "goes-abi", "GOES facts")
    _write(repo / "knowledge" / "plumes.md", "# plumes\n")
    (repo / "knowledge" / "README.md").unlink()
    assert _found(repo) == {("TOPIC_UNREGISTERED", "knowledge/goes-abi.md"),
                            ("TOPIC_UNREGISTERED", "knowledge/plumes.md")}


# --- robustness and output order ---------------------------------------------------------


def test_bad_content_everywhere_gives_sorted_findings_not_exceptions(repo):
    for rel in ("questions/Q-2026-10-25-x.md", "decisions/D-2026-10-25-x.md",
                "literature/a2024-x.md", "log/2026-10-25-fan-codex-1432.md"):
        (repo / rel).write_bytes(b"---\n\xff: [\n")
    (repo / "knowledge" / "goes-abi.md").write_bytes(b"\xff\n- x (src: \xff \xb7 ok)\n")
    (repo / "knowledge" / "README.md").write_bytes(b"\xff\xfe\n")
    found = run_checks(repo)
    assert found == sorted(found, key=lambda f: (str(f.path), f.code, f.message))
    assert {(f.code, f.path.as_posix()) for f in found} == {
        ("FM_INVALID", "questions/Q-2026-10-25-x.md"),
        ("FM_INVALID", "decisions/D-2026-10-25-x.md"),
        ("FM_INVALID", "literature/a2024-x.md"),
        ("FM_INVALID", "log/2026-10-25-fan-codex-1432.md"),
        ("TOPIC_UNREGISTERED", "knowledge/goes-abi.md"),
    }


# --- the command line --------------------------------------------------------------------


def _ra_check(cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run 'python template/protocol/ra.py check' in cwd; output is read as UTF-8."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), "check"],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=False,
    )


def test_cli_prints_each_finding_and_exits_1(repo, make_pdf):
    _lit(repo, make_pdf, "a2024-x", claims=[("Some claim", None)])
    _write(repo / "questions" / "notes.txt", "x\n")
    proc = _ra_check(repo)
    assert (proc.returncode, proc.stderr) == (1, "")
    lines = proc.stdout.splitlines()
    assert lines == [f"{f.code} {f.path.as_posix()}: {f.message}" for f in run_checks(repo)]
    assert lines[0].startswith("CLAIM_NO_WHERE literature/a2024-x.md: line ")
    assert lines[1].startswith("BAD_FILENAME questions/notes.txt: the name should be ")


def test_cli_on_a_clean_repo_prints_no_findings_and_exits_0(repo):
    proc = _ra_check(repo)
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "check: no findings\n", "")


def test_fact_parser_is_re_exported_by_check():
    # Fact and parse_fact_line are tested in test_knowledge.py; check exports them too.
    assert (check.Fact, check.parse_fact_line) == (knowledge.Fact, knowledge.parse_fact_line)
