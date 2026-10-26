"""Tests for ra.dedup, the duplicate lookup behind 'python protocol/ra.py dedup' (spec §10.2)."""

import subprocess
import sys
from pathlib import Path

import pytest
from conftest import _lit
from ra.dedup import find_existing, normalize_arxiv, normalize_doi, normalize_title
from ra.frontmatter import parse, write

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "template" / "protocol" / "ra.py"

# What a person writes when a field has no value: none of these can identify a paper.
PLACEHOLDERS = [
    "", "   ", "—", "-", "--", "?", "...", "/", "n/a", "N/A", "na", "NA", "none", "None",
    "null", "NULL", "tbd", "TBD", "todo", "ToDo", "unknown", "Unknown",
]

# One file for each way a frontmatter block can be unusable (every FrontmatterError case).
UNPARSEABLE = [
    b"no frontmatter at all\n",
    b"---\ndoi: [unclosed\n---\nbody\n",
    b"---\ndoi: 10.1/x\nno closing line\n",
    b"---\n- a list, not a mapping\n---\n",
    b"---\ndoi: \xff\xfe\n---\n",
]


def _edit(path: Path, **changes: object) -> None:
    """Set keys in the frontmatter of the record at path, as a hand edit would."""
    meta, body = parse(path)
    meta.update(changes)
    write(path, meta, body)


# --- the brief's tests --------------------------------------------------------------------


def test_doi_match_beats_title(repo, make_pdf):
    _lit(repo, make_pdf, "a2024-x", doi="10.1016/J.RSE.2024.1", title="Alpha")
    _lit(repo, make_pdf, "b2024-y", doi="10.1/other", title="Beta")
    found = find_existing(repo, doi="https://doi.org/10.1016/j.rse.2024.1", title="Beta")
    assert found.name == "a2024-x.md"


def test_title_normalisation(repo, make_pdf):
    _lit(repo, make_pdf, "c2023-z", title="Smoke-Plume Segmentation: A Study")
    assert find_existing(repo, title="smoke plume segmentation a study").name == "c2023-z.md"
    assert find_existing(repo, title="Unrelated") is None


# --- normalisers --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "10.1016/j.rse.2024.1", "10.1016/J.RSE.2024.1", "  10.1016/j.rse.2024.1\n",
        "doi:10.1016/j.rse.2024.1", "DOI: 10.1016/J.RSE.2024.1",
        "https://doi.org/10.1016/j.rse.2024.1", "HTTPS://DOI.ORG/10.1016/J.RSE.2024.1",
        "http://doi.org/10.1016/j.rse.2024.1",
        "https://dx.doi.org/10.1016/j.rse.2024.1", "http://dx.doi.org/10.1016/J.RSE.2024.1",
    ],
)
def test_normalize_doi_drops_prefix_whitespace_and_case(raw):
    assert normalize_doi(raw) == "10.1016/j.rse.2024.1"


def test_normalize_doi_drops_only_one_prefix():
    assert normalize_doi("doi:https://doi.org/10.1/x") == "https://doi.org/10.1/x"


@pytest.mark.parametrize(
    "raw",
    [
        "2401.10250", " 2401.10250 ", "2401.10250v1", "2401.10250V12", "arXiv:2401.10250",
        "ARXIV: 2401.10250v3", "https://arxiv.org/abs/2401.10250",
        "http://arxiv.org/abs/2401.10250v2",
    ],
)
def test_normalize_arxiv_drops_prefix_version_whitespace_and_case(raw):
    assert normalize_arxiv(raw) == "2401.10250"


def test_normalize_arxiv_handles_an_old_style_id_with_a_slash():
    assert normalize_arxiv("arXiv:HEP-TH/9901001v2") == "hep-th/9901001"


def test_normalize_title_keeps_only_casefolded_letters_and_digits():
    assert normalize_title("Smoke-Plume Segmentation: A Study") == "smokeplumesegmentationastudy"
    assert normalize_title("  GOES-16 ABI: 3.9 um (2 km)\n") == "goes16abi39um2km"


def test_normalize_title_keeps_the_letters_of_every_script():
    assert normalize_title("基于深度学习的烟雾羽流分割：一项研究") == "基于深度学习的烟雾羽流分割一项研究"
    assert normalize_title("Étude: Über-Größe") == "étudeübergrösse"


@pytest.mark.parametrize("normalise", [normalize_doi, normalize_arxiv, normalize_title])
@pytest.mark.parametrize("raw", [None, *PLACEHOLDERS])
def test_a_value_with_nothing_to_compare_normalises_to_none(normalise, raw):
    assert normalise(raw) is None


@pytest.mark.parametrize(
    ("normalise", "raw"),
    [
        (normalize_doi, "doi:"), (normalize_doi, "https://doi.org/"), (normalize_doi, "doi: N/A"),
        (normalize_arxiv, "arXiv:"), (normalize_arxiv, "https://arxiv.org/abs/"),
        (normalize_arxiv, "arxiv:none"),
    ],
)
def test_a_prefix_with_nothing_after_it_normalises_to_none(normalise, raw):
    assert normalise(raw) is None


def test_a_value_that_only_contains_a_placeholder_word_is_kept():
    assert normalize_doi("10.1/tbd") == "10.1/tbd"
    assert normalize_title("None of the Above") == "noneoftheabove"
    assert normalize_title("Unknown Unknowns") == "unknownunknowns"


# --- find_existing ------------------------------------------------------------------------


def test_priority_is_doi_then_arxiv_then_title_whatever_the_file_order(repo, make_pdf):
    # The title match sorts first and the DOI match last: only the priority can pick c.
    _lit(repo, make_pdf, "a2024-x", title="Alpha")
    _lit(repo, make_pdf, "b2024-y", arxiv="2401.10250", title="Beta")
    _lit(repo, make_pdf, "c2024-z", doi="10.1/c", title="Gamma")
    literature = repo / "literature"
    assert find_existing(repo, "10.1/c", "2401.10250", "Alpha") == literature / "c2024-z.md"
    assert find_existing(repo, "10.1/no", "2401.10250", "Alpha") == literature / "b2024-y.md"
    assert find_existing(repo, "10.1/no", "2499.99999", "Alpha") == literature / "a2024-x.md"


def test_arxiv_is_tried_when_the_doi_matches_nothing(repo, make_pdf):
    _lit(repo, make_pdf, "a2024-x", doi="10.1/a", arxiv="2401.10250")
    _lit(repo, make_pdf, "b2024-y", doi="10.1/b", arxiv="2402.00001")
    found = find_existing(repo, doi="10.1/not-there", arxiv="arXiv:2402.00001v2")
    assert found == repo / "literature" / "b2024-y.md"


def test_a_query_that_normalises_to_none_is_skipped_not_matched(repo, make_pdf):
    _lit(repo, make_pdf, "a2024-x", doi="10.1/a", title="Alpha")
    found = find_existing(repo, doi="—", arxiv="n/a", title="Alpha")
    assert found == repo / "literature" / "a2024-x.md"


def test_the_first_record_in_file_name_order_wins(repo, make_pdf):
    _lit(repo, make_pdf, "c2024-z", doi="https://doi.org/10.1/same")
    _lit(repo, make_pdf, "b2024-y", doi="DOI:10.1/SAME")
    _lit(repo, make_pdf, "a2024-x", doi="10.1/same")
    assert find_existing(repo, doi="10.1/same").name == "a2024-x.md"


@pytest.mark.parametrize("query", ["", "   ", "—", "n/a", "?!"])
@pytest.mark.parametrize("stored", ["", "—", "n/a", None])
def test_a_title_with_nothing_to_compare_matches_nothing(repo, make_pdf, stored, query):
    _edit(_lit(repo, make_pdf, "a2024-x"), title=stored)
    assert find_existing(repo, title=query) is None


@pytest.mark.parametrize("stored", ["", "—", "n/a", "TBD", None])
def test_placeholder_identifiers_match_nothing(repo, make_pdf, stored):
    _edit(_lit(repo, make_pdf, "a2024-x"), doi=stored, arxiv=stored)
    assert find_existing(repo, doi="—", arxiv="—") is None
    assert find_existing(repo, doi="n/a", arxiv="n/a") is None
    assert find_existing(repo, doi="TBD", arxiv="") is None


@pytest.mark.parametrize("content", UNPARSEABLE)
def test_an_unparseable_record_is_skipped_silently(repo, make_pdf, content, capsys):
    (repo / "literature" / "a-broken.md").write_bytes(content)
    _lit(repo, make_pdf, "b2024-y", doi="10.1/x", title="Beta")
    assert find_existing(repo, doi="10.1/x").name == "b2024-y.md"
    assert find_existing(repo, title="Beta").name == "b2024-y.md"
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("name", [".hidden.md", "notes.txt", "sub/c.md", "pdf/d.md"])
def test_only_visible_md_files_directly_in_literature_are_scanned(repo, make_pdf, name):
    record = _lit(repo, make_pdf, "a2024-x", doi="10.1/ignored")
    assert find_existing(repo, doi="10.1/ignored") == record
    target = repo / "literature" / name
    target.parent.mkdir(exist_ok=True)
    record.replace(target)
    assert find_existing(repo, doi="10.1/ignored") is None


def test_non_text_frontmatter_values_are_ignored(repo, make_pdf):
    path = _lit(repo, make_pdf, "a2024-x")
    _edit(path, doi=10, arxiv=["2401.10250"], title={"en": "Alpha"})
    assert find_existing(repo, doi="10", arxiv="2401.10250", title="Alpha") is None


def test_a_repo_without_a_literature_folder_has_no_match(tmp_path):
    assert find_existing(tmp_path, doi="10.1/x", arxiv="2401.10250", title="Alpha") is None


def test_a_lookup_without_any_query_is_a_value_error(repo):
    with pytest.raises(ValueError, match="at least one"):
        find_existing(repo)


# --- the command line ---------------------------------------------------------------------


def _ra_dedup(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run 'python template/protocol/ra.py dedup <args>' in cwd; output is read as UTF-8."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), "dedup", *args],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=False,
    )


def test_cli_prints_the_matching_path_relative_to_the_repo(repo, make_pdf):
    _lit(repo, make_pdf, "a2024-x", doi="10.1016/J.RSE.2024.1", title="Alpha")
    proc = _ra_dedup(repo, "--doi", "https://doi.org/10.1016/j.rse.2024.1")
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "literature/a2024-x.md\n", "")


def test_cli_prints_none_and_exits_0_when_nothing_matches(repo, make_pdf):
    _lit(repo, make_pdf, "a2024-x", doi="10.1/a", arxiv="2401.10250", title="Alpha")
    proc = _ra_dedup(repo, "--doi", "10.1/b", "--arxiv", "2402.00001", "--title", "Unrelated")
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "none\n", "")


def test_cli_prints_none_for_a_project_without_records(repo):
    proc = _ra_dedup(repo, "--title", "Alpha")
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "none\n", "")


def test_cli_applies_the_priority_doi_then_arxiv_then_title(repo, make_pdf):
    _lit(repo, make_pdf, "a2024-x", title="Alpha")
    _lit(repo, make_pdf, "b2024-y", arxiv="2401.10250", title="Beta")
    proc = _ra_dedup(repo, "--title", "Alpha", "--arxiv", "arXiv:2401.10250v2")
    assert (proc.returncode, proc.stdout) == (0, "literature/b2024-y.md\n")
    proc = _ra_dedup(repo, "--title", "ALPHA")
    assert (proc.returncode, proc.stdout) == (0, "literature/a2024-x.md\n")


def test_cli_matches_a_non_ascii_title(repo, make_pdf):
    _lit(repo, make_pdf, "a2024-x", title="基于深度学习的烟雾羽流分割")
    proc = _ra_dedup(repo, "--title", "基于深度学习的 烟雾羽流分割。")
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "literature/a2024-x.md\n", "")


def test_cli_without_a_query_is_a_usage_error_with_exit_2(repo):
    proc = _ra_dedup(repo)
    assert proc.returncode == 2
    assert proc.stdout == ""
    assert "usage" in proc.stderr.lower()
    assert "at least one of --doi, --arxiv or --title" in proc.stderr
