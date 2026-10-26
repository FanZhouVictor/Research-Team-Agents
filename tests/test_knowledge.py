"""Tests for ra.knowledge: reading the fact lines of a knowledge topic file."""

import pytest
from ra.knowledge import Fact, parse_fact_line, parse_facts

FACT = (
    "- GOES-16 ABI band 7 is 3.9 µm with 2 km nadir resolution "
    "(src: smith2024-plume-goes §2.1 p.3 · Fan/codex 2026-10-25 · approved Fan · ok)"
)


def test_parse_fact_line_reads_every_field():
    assert parse_fact_line(FACT) == Fact(
        text="GOES-16 ABI band 7 is 3.9 µm with 2 km nadir resolution",
        citekey="smith2024-plume-goes", where="§2.1 p.3", by="Fan/codex 2026-10-25",
        approved="Fan", status="ok", line=0,
    )


def test_parse_fact_line_reads_a_conflict_status_and_keeps_inner_parentheses():
    fact = parse_fact_line(
        "- Band 7 (3.9 µm) nadir resolution is 1 km (src: lee2023-abi-spec Table 1 (top) · "
        "Lee/claude-code 2026-10-28 · approved Lee · CONFLICT with line above)\r\n"
    )
    assert fact is not None
    assert (fact.text, fact.citekey, fact.where, fact.by, fact.approved, fact.status) == (
        "Band 7 (3.9 µm) nadir resolution is 1 km", "lee2023-abi-spec", "Table 1 (top)",
        "Lee/claude-code 2026-10-28", "Lee", "CONFLICT with line above",
    )


def test_parse_fact_line_leaves_missing_segments_none():
    assert parse_fact_line("- Fact (src: a2024-x · superseded by line 9)") == Fact(
        "Fact", "a2024-x", None, None, None, "superseded by line 9", 0
    )


def test_parse_fact_line_keeps_no_citekey_that_breaks_the_citekey_rule():
    fact = parse_fact_line("- Fact (src: ../Secret p.2 · approved Fan · ok)")
    assert fact is not None and (fact.citekey, fact.where) == (None, "p.2")


@pytest.mark.parametrize(
    "line",
    [
        "- A bullet without metadata",
        "- mIoU — mean intersection over union (a segmentation metric)",
        "  - Indented (src: a2024-x p.1 · Fan/codex 2026-10-25 · approved Fan · ok)",
        "Not a bullet (src: a2024-x p.1 · Fan/codex 2026-10-25 · approved Fan · ok)",
        "- Unbalanced src: a2024-x p.1 · approved Fan · ok)",
        "# goes-abi",
        "",
    ],
)
def test_parse_fact_line_returns_none_for_other_lines(line):
    assert parse_fact_line(line) is None


def test_parse_facts_numbers_file_lines_and_skips_html_comments():
    text = f"# goes-abi\nGOES facts\n<!-- example:\n{FACT}\n-->\n{FACT}\n- plain bullet\n"
    facts = parse_facts(text)
    assert [fact.line for fact in facts] == [6]
    assert facts[0].citekey == "smith2024-plume-goes"
