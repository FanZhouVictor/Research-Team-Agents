"""Read the claims of a literature record: the bullet list under '## Claims for this project'.

    ## Claims for this project
    - <the claim>
      - where: <section, table, figure or page>
      - bears on: <question id> — supports
      - kind: result · basis: stated by paper
      - by: <person> · <agent> · <date>
      - verified-by: <person> · <agent> · <date>; <person> · <agent> · <date>
      - disputed-by: —

parse_claims() is a pure, line-oriented scan: no Markdown library and no I/O. It is written for
files that people edit by hand: it never raises, and a line it cannot parse is skipped.
"""

import re
from dataclasses import dataclass

__all__ = ["Claim", "parse_claims"]

# Names and headings ignore case, in ASCII only: with Unicode case folding a long s (U+017F) or
# a dotless i (U+0131) would pass for 's' or 'i' and give a field name that no Claim has.
_ANY_CASE = re.IGNORECASE | re.ASCII
# A sub-bullet field name. A space, hyphen or underscore are interchangeable: 'bears on',
# 'Bears-On' and 'bears_on' name the same field.
_NAME = r"(?:where|bears[ _-]on|kind|basis|by|verified[ _-]by|disputed[ _-]by)"
_FIELD = re.compile(rf"({_NAME})[ \t]*:(.*)", _ANY_CASE)
# A '·' joins two fields on one line only when a field name and a colon follow it; any other
# '·' belongs to the value ('by: Fan · codex · 2026-10-25').
_JOIN = re.compile(rf"·(?=[ \t]*{_NAME}[ \t]*:)", _ANY_CASE)
_NAME_GAP = re.compile(r"[ _-]")
_COMMENT_START = re.compile(r"(?<=[ \t])#")  # a '#' after whitespace: the rest is a comment

_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_ANY_H2 = re.compile(r"##(?:[ \t]|$)")
_CLAIMS_H2 = re.compile(r"##[ \t]+claims for this project", _ANY_CASE)
_CLAIM = re.compile(r"-(?:[ \t]+(.*))?")  # '- text'; a bare '-' is an empty bullet
_SUB_BULLET = re.compile(r"(?: {2,4}|\t)-[ \t]+(.*)")
_WRAPPED = re.compile(r"[ \t]+(?!-(?:[ \t]|$))(\S.*)")  # indented text that is not a bullet


@dataclass
class Claim:
    """One claim of a literature record.

    text: the claim's line after '- ', stripped; a wrapped line is joined on with one space.
    where: section, table, figure or page; None when the sub-bullet is absent or empty.
    bears_on: question ids; any '— relation' suffix is dropped.
    kind, basis, by: the stripped values; None when absent or empty.
    verified_by, disputed_by: the ';'-separated entries; [] for '—' or an empty value.
    line: 1-based line number of the claim's bullet within the body that was parsed.
    """

    text: str
    where: str | None
    bears_on: list[str]
    kind: str | None
    basis: str | None
    by: str | None
    verified_by: list[str]
    disputed_by: list[str]
    line: int


def _new_claim(text: str, line: int) -> Claim:
    """Return a claim with this text and line number and every other field empty."""
    return Claim(
        text=text, where=None, bears_on=[], kind=None, basis=None, by=None,
        verified_by=[], disputed_by=[], line=line,
    )


def _line_breaks(comment: re.Match[str]) -> str:
    """Stand-in for an HTML comment: only its line breaks, so line numbers do not move."""
    return "\n" * comment.group().count("\n")


def _entries(value: str) -> list[str]:
    """Split value on ';' into stripped entries; empty entries and '—' (none) are dropped."""
    parts = (part.strip() for part in value.split(";"))
    return [part for part in parts if part and part != "—"]


def _question_ids(value: str) -> list[str]:
    """Split a 'bears on' value on ';' and keep, per entry, the text before a '— relation'."""
    parts = (part.split("—", 1)[0].strip() for part in value.split(";"))
    return [part for part in parts if part]


def _store(claim: Claim, name: str, value: str) -> None:
    """Set one field of claim. A text field keeps its first non-empty value; lists add up."""
    if name == "bears_on":
        claim.bears_on.extend(_question_ids(value))
    elif name == "verified_by":
        claim.verified_by.extend(_entries(value))
    elif name == "disputed_by":
        claim.disputed_by.extend(_entries(value))
    elif value and getattr(claim, name) is None:  # where, kind, basis, by
        setattr(claim, name, value)


def _read_fields(claim: Claim, text: str) -> None:
    """Store the 'field: value' pairs of one sub-bullet on claim; unknown fields are ignored."""
    comment = _COMMENT_START.search(text)
    if comment:
        text = text[: comment.start()]
    for part in _JOIN.split(text):
        pair = _FIELD.fullmatch(part.strip())
        if pair:
            _store(claim, _NAME_GAP.sub("_", pair.group(1).lower()), pair.group(2).strip())


def parse_claims(body: str) -> list[Claim]:
    """Return the claims in the body of a literature record, in file order.

    A claim is a top-level bullet ('- ' at column 0) between the heading
    '## Claims for this project' (any case) and the next '## ' heading or the end of body;
    without the heading the result is []. Its sub-bullets, indented 2-4 spaces or one tab,
    are 'field: value' lines for where, bears on, kind, basis, by, verified-by and
    disputed-by (names ignore case; space, hyphen and underscore are interchangeable). One
    line may hold several pairs joined by '·' ('kind: result · basis: stated by paper').
    A repeated field adds to the lists and leaves the first value of the other fields; any
    other field is ignored.

    Tolerated: blank lines in the section, CRLF line endings, trailing whitespace, a
    trailing '# comment' on a sub-bullet (cut from the value), and claim text wrapped onto
    indented lines right after the bullet. HTML comments are skipped, so the example claim
    in a raw copy of templates/literature.md is not a claim.

    Args:
        body: The text after the frontmatter.

    Returns:
        The claims. Each line number counts from 1 at the first line of body. Malformed
        lines are skipped; the function does not raise.
    """
    claims: list[Claim] = []
    claim: Claim | None = None  # the claim whose sub-bullets are being read
    in_section = False
    wrapping = False  # the last line was the claim's bullet or a wrapped part of it
    for number, raw in enumerate(_HTML_COMMENT.sub(_line_breaks, body).split("\n"), start=1):
        line = raw.rstrip()
        if _ANY_H2.match(line):
            in_section = _CLAIMS_H2.fullmatch(line) is not None
            claim, wrapping = None, False
        elif not in_section or not line:
            wrapping = False
        elif (top := _CLAIM.fullmatch(line)) is not None:
            text = (top.group(1) or "").strip()
            claim = _new_claim(text, number) if text else None
            wrapping = claim is not None
            if claim is not None:
                claims.append(claim)
        elif claim is None:
            continue  # a sub-bullet or text that belongs to no claim
        elif (sub := _SUB_BULLET.fullmatch(line)) is not None:
            _read_fields(claim, sub.group(1))
            wrapping = False
        elif wrapping and (more := _WRAPPED.fullmatch(line)) is not None:
            claim.text += " " + more.group(1)
        else:
            wrapping = False
    return claims
