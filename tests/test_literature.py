"""Tests for ra.literature: reading the claims of a literature record."""

import dataclasses
from pathlib import Path

import pytest
from ra import literature
from ra.frontmatter import parse
from ra.literature import Claim, parse_claims
from ra.newfile import new_literature

TEMPLATE = (
    Path(__file__).resolve().parents[1] / "template" / "protocol" / "templates" / "literature.md"
)
HEADING = "## Claims for this project\n"


def _claims(*lines: str) -> list[Claim]:
    """parse_claims of a body made of the Claims heading (line 1) followed by lines."""
    return parse_claims(HEADING + "".join(f"{line}\n" for line in lines))


# --- the brief's test --------------------------------------------------------------------

BODY = """## Claims for this project
- Transformer beats U-Net by 4.2 mIoU
  - where: Table 3, p.7
  - bears on: Q-2026-10-25-plume-baselines — supports
  - kind: result · basis: stated by paper
  - by: Fan · codex · 2026-10-25
  - verified-by: Lee · claude-code · 2026-10-28
  - disputed-by: —
- Dataset has 1,204 scenes
  - bears on: Q-2026-10-25-plume-baselines — supports
  - by: Fan · codex · 2026-10-25
## Notes
"""


def test_parses_fields_and_missing_where():
    c = parse_claims(BODY)
    assert len(c) == 2
    assert c[0].where == "Table 3, p.7" and c[0].verified_by == ["Lee · claude-code · 2026-10-28"] and c[0].disputed_by == []
    assert c[1].where is None and c[1].bears_on == ["Q-2026-10-25-plume-baselines"]


# --- fields ------------------------------------------------------------------------------


def test_every_field_of_both_claims():
    assert parse_claims(BODY) == [
        Claim(
            text="Transformer beats U-Net by 4.2 mIoU",
            where="Table 3, p.7",
            bears_on=["Q-2026-10-25-plume-baselines"],
            kind="result",
            basis="stated by paper",
            by="Fan · codex · 2026-10-25",
            verified_by=["Lee · claude-code · 2026-10-28"],
            disputed_by=[],
            line=2,
        ),
        Claim(
            text="Dataset has 1,204 scenes",
            where=None,
            bears_on=["Q-2026-10-25-plume-baselines"],
            kind=None,
            basis=None,
            by="Fan · codex · 2026-10-25",
            verified_by=[],
            disputed_by=[],
            line=9,
        ),
    ]


def test_claim_fields_and_exports():
    names = [f.name for f in dataclasses.fields(Claim)]
    assert names == [
        "text", "where", "bears_on", "kind", "basis", "by", "verified_by", "disputed_by", "line",
    ]
    assert literature.__all__ == ["Claim", "parse_claims"]


def test_a_claim_without_sub_bullets_has_empty_fields():
    assert _claims("- bare") == [
        Claim(text="bare", where=None, bears_on=[], kind=None, basis=None, by=None,
              verified_by=[], disputed_by=[], line=2),
    ]


def test_kind_and_basis_parse_the_same_on_one_line_or_two():
    one = _claims("- c", "  - where: p.1", "  - kind: result · basis: stated by paper")
    two = _claims("- c", "  - where: p.1", "  - kind: result", "  - basis: stated by paper")
    assert (one[0].kind, one[0].basis) == ("result", "stated by paper")
    assert one == two


def test_trailing_comments_are_stripped_from_values():
    spec = """## Claims for this project
- Transformer segmentation beats U-Net by 4.2 mIoU on GOES-16 plume masks
  - where: Table 3, p.7
  - bears on: Q-2026-10-25-plume-baselines — supports
  - kind: result                 # result | method | dataset | definition | limitation
  - basis: stated by paper       # or: inferred by <agent>
  - by: Fan · codex · 2026-10-25
  - verified-by: Lee · claude-code · 2026-10-28
  - disputed-by: —
"""
    assert parse_claims(spec) == [
        Claim(
            text="Transformer segmentation beats U-Net by 4.2 mIoU on GOES-16 plume masks",
            where="Table 3, p.7",
            bears_on=["Q-2026-10-25-plume-baselines"],
            kind="result",
            basis="stated by paper",
            by="Fan · codex · 2026-10-25",
            verified_by=["Lee · claude-code · 2026-10-28"],
            disputed_by=[],
            line=2,
        ),
    ]
    commented = "  - kind: result · basis: stated by paper   # or: inferred by <agent>"
    one_line = _claims("- c", commented)[0]
    assert (one_line.kind, one_line.basis) == ("result", "stated by paper")


def test_only_a_hash_after_two_or_more_spaces_or_tabs_starts_a_comment():
    # Ruling R29: after one space a '#' is text, so 'Fig. #3' is not cut to 'Fig.'.
    c = _claims("- c", "  - where: Fig. #3", "  - kind: result  # result | method",
                "  - basis: stated by paper\t\t# or: inferred by <agent>", "  - by: Fan #1")[0]
    assert (c.where, c.kind, c.basis, c.by) == ("Fig. #3", "result", "stated by paper", "Fan #1")


def test_a_hash_not_preceded_by_whitespace_stays_and_claim_text_is_not_a_value():
    c = _claims(
        "- Ranked #1 on the benchmark",
        "  - where: Table 3#2",
        "  - basis: see https://x.org/a#b  # note",
    )[0]
    assert c.text == "Ranked #1 on the benchmark"
    assert c.where == "Table 3#2"
    assert c.basis == "see https://x.org/a#b"


def test_absent_empty_and_dash_values():
    c = _claims(
        "- c",
        "  - where:",
        "  - bears on: —",
        "  - kind:",
        "  - basis:      # nothing yet",
        "  - by:",
        "  - verified-by: —",
        "  - disputed-by:   ",
    )[0]
    assert (c.where, c.kind, c.basis, c.by) == (None, None, None, None)
    assert (c.bears_on, c.verified_by, c.disputed_by) == ([], [], [])


def test_semicolon_separated_entries():
    c = _claims(
        "- c",
        "  - bears on: Q-2026-10-25-a — supports; Q-2026-10-26-b — contradicts;  Q-2026-10-27-c",
        "  - verified-by: Lee · claude-code · 2026-10-28; Kim · codex · 2026-11-02",
        "  - disputed-by: Ana · codex · 2026-11-03;  —",
    )[0]
    assert c.bears_on == ["Q-2026-10-25-a", "Q-2026-10-26-b", "Q-2026-10-27-c"]
    assert c.verified_by == ["Lee · claude-code · 2026-10-28", "Kim · codex · 2026-11-02"]
    assert c.disputed_by == ["Ana · codex · 2026-11-03"]


def test_a_middle_dot_separates_fields_only_before_a_field_name():
    c = _claims(
        "- c",
        "  - by: Fan · codex · 2026-10-25 · verified-by: Lee · claude-code · 2026-10-28",
        "  - where: Table 3 · p.7",
    )[0]
    assert c.by == "Fan · codex · 2026-10-25"
    assert c.verified_by == ["Lee · claude-code · 2026-10-28"]
    assert c.where == "Table 3 · p.7"


def test_unknown_fields_and_prose_sub_bullets_are_ignored():
    claims = _claims(
        "- c", "  - where: p.1", "  - note: interesting",
        "  - see also Table 4", "  - Verified: Lee",
    )
    assert claims == [
        Claim(text="c", where="p.1", bears_on=[], kind=None, basis=None, by=None,
              verified_by=[], disputed_by=[], line=2),
    ]


def test_lookalike_letters_are_not_field_names():
    long_s, dotless_i = chr(0x17F), chr(0x131)  # Unicode case folding would match s and i
    c = _claims("- c", f"  - ba{long_s}is: x", f"  - bas{dotless_i}s: y", "  - kind: result")[0]
    assert (c.basis, c.kind) == (None, "result")


def test_field_names_ignore_case_and_accept_space_hyphen_or_underscore():
    c = _claims(
        "- c",
        "  - Where: p.1",
        "  - Bears-On: Q-2026-10-25-a",
        "  - verified_by: Lee · codex · 2026-10-28",
        "  - Disputed by: Kim · codex · 2026-10-29",
    )[0]
    assert (c.where, c.bears_on) == ("p.1", ["Q-2026-10-25-a"])
    assert c.verified_by == ["Lee · codex · 2026-10-28"]
    assert c.disputed_by == ["Kim · codex · 2026-10-29"]


def test_repeated_sub_bullets_add_up_lists_and_keep_the_first_value():
    c = _claims(
        "- c",
        "  - bears on: Q-2026-10-25-a — supports",
        "  - bears on: Q-2026-10-26-b — contradicts",
        "  - disputed-by: —",
        "  - disputed-by: Lee · codex · 2026-10-29",
        "  - disputed-by: —",  # a later '—' must not erase the dispute above it
        "  - disputed-by: Kim · codex · 2026-10-30",
        "  - verified-by: Ana · codex · 2026-10-27",
        "  - verified-by: Kim · claude-code · 2026-10-28",
        "  - where:",
        "  - where: p.1",
        "  - where: p.2",
    )[0]
    assert c.bears_on == ["Q-2026-10-25-a", "Q-2026-10-26-b"]
    assert c.disputed_by == ["Lee · codex · 2026-10-29", "Kim · codex · 2026-10-30"]
    assert c.verified_by == ["Ana · codex · 2026-10-27", "Kim · claude-code · 2026-10-28"]
    assert c.where == "p.1"


def test_non_ascii_text_survives():
    c = _claims("- Band 3.9 µm saturates — 烟羽", "  - where: Table 2 (3.9 µm) · row 3")[0]
    assert c.text == "Band 3.9 µm saturates — 烟羽"
    assert c.where == "Table 2 (3.9 µm) · row 3"


# --- section and line handling -----------------------------------------------------------


def test_only_the_claims_section_is_read():
    body = (
        "## Summary\n- not a claim\n  - where: nowhere\n"
        "## Claims for this project\n- first\n  - where: p.1\n"
        "### Details\n- second\n  - where: p.2\n"
        "## Notes\n- not a claim either\n  - where: nowhere\n"
    )
    assert [(c.text, c.where) for c in parse_claims(body)] == [("first", "p.1"), ("second", "p.2")]


@pytest.mark.parametrize(
    "body",
    [
        "",
        "plain text\n",
        "## Summary\n- c\n  - where: p.1\n",
        "## Claims\n- c\n  - where: p.1\n",
        "## Claims for this project and more\n- c\n",
        "  ## Claims for this project\n- c\n",
        "### Claims for this project\n- c\n",
    ],
)
def test_without_the_claims_heading_there_are_no_claims(body):
    assert parse_claims(body) == []


@pytest.mark.parametrize(
    "heading",
    ["## claims for this project", "##  Claims for this project  ", "## CLAIMS FOR THIS PROJECT\r"],
)
def test_heading_ignores_case_and_surrounding_spaces(heading):
    assert [c.text for c in parse_claims(f"{heading}\n- c\n")] == ["c"]


def test_crlf_and_trailing_whitespace_change_nothing():
    expected = parse_claims(BODY)
    assert expected[0].where == "Table 3, p.7"  # not two empty results compared with each other
    assert parse_claims(BODY.replace("\n", "\r\n")) == expected
    assert parse_claims(BODY.replace("\n", " \t \n")) == expected
    assert parse_claims(BODY.replace("\n", " \t \r\n")) == expected


def test_line_numbers_count_lines_of_the_body_from_one():
    body = "Intro\n\n## Claims for this project\n- first\n  - where: p.1\n\n- second\n"
    assert [(c.text, c.line) for c in parse_claims(body)] == [("first", 4), ("second", 7)]
    assert [c.line for c in parse_claims(body.replace("\n", "\r\n"))] == [4, 7]


def test_blank_lines_inside_the_section_are_allowed():
    body = (
        "## Claims for this project\n\n- first\n\n  - where: p.1\n\n"
        "  - kind: result\n\n- second\n\n"
    )
    got = [(c.text, c.where, c.kind, c.line) for c in parse_claims(body)]
    assert got == [("first", "p.1", "result", 3), ("second", None, None, 9)]


def test_a_wrapped_claim_text_is_joined_with_single_spaces():
    claims = _claims(
        "- Transformer segmentation beats U-Net by",
        "  4.2 mIoU on GOES-16",
        "    plume masks   ",
        "  - where: Table 3",
        "  A note after a sub-bullet is not claim text.",
        "- next",
    )
    text = "Transformer segmentation beats U-Net by 4.2 mIoU on GOES-16 plume masks"
    assert [c.text for c in claims] == [text, "next"]
    assert claims[0].where == "Table 3"


@pytest.mark.parametrize("indent", ["  ", "   ", "    ", "\t"])
def test_sub_bullets_are_indented_two_to_four_spaces_or_a_tab(indent):
    c = _claims("- c", f"{indent}- where: p.1", f"{indent}- kind: result")[0]
    assert (c.where, c.kind) == ("p.1", "result")


@pytest.mark.parametrize("indent", [" ", "     ", "\t\t"])
def test_other_indentation_is_not_a_sub_bullet(indent):
    c = _claims("- c", f"{indent}- where: p.1")[0]
    assert c.where is None
    assert c.text == "c"


def test_an_empty_bullet_is_not_a_claim_and_owns_its_sub_bullets():
    claims = _claims(
        "- first", "  - where: p.1", "-", "  - where: stray", "- ", "  - where: stray too",
        "- second", "  - where: p.2",
    )
    assert [(c.text, c.where) for c in claims] == [("first", "p.1"), ("second", "p.2")]


def test_an_indented_bare_dash_is_not_wrapped_text():
    assert [(c.text, c.where) for c in _claims("- c", "  -", "  - where: p.1")] == [("c", "p.1")]


def test_an_empty_h2_heading_ends_the_section():
    body = "## Claims for this project\n- first\n## \n- second\n"
    assert [c.text for c in parse_claims(body)] == ["first"]


def test_html_comments_are_not_claims():
    body = (
        "## Claims for this project\n<!-- Format:\n- <the claim>\n  - where: <section>\n-->\n"
        "- real claim <!-- inline note -->\n  - where: p.1\n"
    )
    assert [(c.text, c.where, c.line) for c in parse_claims(body)] == [("real claim", "p.1", 6)]


def test_a_raw_copy_of_the_template_has_no_claims():
    assert parse_claims(TEMPLATE.read_text(encoding="utf-8")) == []


def test_a_new_literature_record_has_no_claims_until_one_is_added(repo, make_pdf):
    src = repo.parent / "s.pdf"
    make_pdf(src, "hello")
    who = {"person": "Fan", "agent": "codex", "date": "2026-10-25"}
    record = new_literature(repo, "smith2024-plume-goes", who, src)
    _, body = parse(record)
    assert parse_claims(body) == []
    assert HEADING in body
    added = body.replace(HEADING, HEADING + "- A claim\n  - where: p.1\n", 1)
    assert [(c.text, c.where) for c in parse_claims(added)] == [("A claim", "p.1")]


@pytest.mark.parametrize(
    "body",
    [
        "## Claims for this project",
        "## Claims for this project\n-",
        "## Claims for this project\n  - where: p.1\n",
        "## Claims for this project\n- c\n  - :\n  - where\n  - : x\n  -\n",
        "## Claims for this project\n- c\n  - kind: · · ·\n  - by: ;;;\n  - bears on: —; ;—\n",
        "## Claims for this project\n<!-- never closed\n- c\n  - where: p.1\n",
        "## Claims for this project\r- c\r  - where: p.1\r",
        "## Claims for this project\n- c\u2028  - where: p.1\x00\n",
    ],
)
def test_malformed_content_never_raises(body):
    assert isinstance(parse_claims(body), list)
