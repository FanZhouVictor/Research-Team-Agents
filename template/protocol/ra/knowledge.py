"""Read the fact lines of a knowledge topic file: knowledge/<topic>.md (spec §11).

A topic file has no frontmatter: a '# <topic>' line and a scope line, then one fact per
line with its metadata in a trailing parenthesis:

    - <fact> (src: <citekey> <where> · <Person>/<agent> <date> · approved <Person> · <status>)

Status values: ok | CONFLICT with <ref> | superseded by <ref>. Like parse_claims, this is
a pure line scan for hand-edited files: it never raises, and a line it cannot read is not
a fact.
"""

import re
from dataclasses import dataclass, replace

__all__ = ["Fact", "parse_fact_line", "parse_facts"]

_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_BULLET = re.compile(r"-[ \t]+")  # a top-level bullet: '-' at column 0, then a space or tab
_CITEKEY = re.compile(r"[a-z0-9-]+")
_SEGMENT_GAP = re.compile(r"\s*·\s*")
_SRC = re.compile(r"src:\s*(.*)", re.IGNORECASE)
_APPROVED = re.compile(r"approved(?:\s+(.*))?", re.IGNORECASE)
_STATUS = re.compile(r"ok|conflict with\b.*|superseded by\b.*", re.IGNORECASE)


@dataclass
class Fact:
    """One fact line of a knowledge topic file.

    text is the fact before its metadata parenthesis; citekey, where, by, approved and status
    come from the metadata and are None when it does not give them; line is the 1-based line
    number in the topic file (0 from parse_fact_line, which sees one line only).
    """

    text: str
    citekey: str | None
    where: str | None
    by: str | None
    approved: str | None
    status: str | None
    line: int


def parse_fact_line(line: str) -> Fact | None:
    """Read one line of a topic file as a fact; None if it is not one.

    A fact is a top-level bullet ('- ' at column 0) that ends in a parenthesised metadata
    group. The group's segments are separated by '·': 'src:' gives the citekey (its first
    word, if that is [a-z0-9-]+) and the where (the rest); 'approved <name>' the approver;
    'ok', 'CONFLICT with <ref>' or 'superseded by <ref>' the status, kept as written; the
    first other segment is by. A missing segment gives None. The group must hold a src,
    approved or status segment, so a bullet that ends in an ordinary remark in parentheses
    is not a fact. Balanced parentheses inside the text or the where are fine.

    Args:
        line: One line, with or without its line ending.

    Returns:
        The fact with line 0, or None.
    """
    line = line.rstrip()
    bullet = _BULLET.match(line)
    start = _group_start(line) if line.endswith(")") else None
    if bullet is None or start is None:
        return None
    citekey = where = by = approved = status = None
    has_metadata = False
    for segment in _SEGMENT_GAP.split(line[start + 1 : -1].strip()):
        if (src := _SRC.fullmatch(segment)) is not None:
            words = src.group(1).split(None, 1)
            citekey = words[0] if words and _CITEKEY.fullmatch(words[0]) else None
            where = words[1].strip() if len(words) > 1 else None
            has_metadata = True
        elif (approval := _APPROVED.fullmatch(segment)) is not None:
            approved = (approval.group(1) or "").strip() or None
            has_metadata = True
        elif _STATUS.fullmatch(segment):
            status = segment
            has_metadata = True
        elif by is None and segment:
            by = segment
    if not has_metadata:
        return None
    return Fact(line[bullet.end() : start].strip(), citekey, where, by, approved, status, line=0)


def parse_facts(text: str) -> list[Fact]:
    """Return the facts of a topic file's text in file order, each with its line number.

    HTML comments are skipped, so the example fact in a raw copy of templates/topic.md is
    not a fact; line numbers still count the comment's lines.
    """
    text = _HTML_COMMENT.sub(lambda comment: "\n" * comment.group().count("\n"), text)
    facts = []
    for number, line in enumerate(text.split("\n"), start=1):
        fact = parse_fact_line(line)
        if fact is not None:
            facts.append(replace(fact, line=number))
    return facts


def _group_start(text: str) -> int | None:
    """Index of the '(' that matches the ')' ending text; None if there is none."""
    depth = 0
    for index in range(len(text) - 1, -1, -1):
        if text[index] == ")":
            depth += 1
        elif text[index] == "(":
            depth -= 1
            if depth == 0:
                return index
    return None
