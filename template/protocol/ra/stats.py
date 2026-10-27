"""The pilot metrics of spec §16: what 'ra stats' prints for a project repository.

stats(repo) counts, in this order:

    papers             the records in literature/
    claims             the claims of all records
    unverified_claims  claims with no verified-by entry from a person other than their author
    disputed_claims    claims with a disputed-by entry
    duplicate_records  DUP_LITERATURE findings of ra.check
    decisions_edited   DECISION_EDITED findings of ra.check
    open_questions     question records with status: open
    conflict_facts     fact lines of knowledge/ whose status is CONFLICT

No count opens a PDF (spec §7.1). A file that does not parse is skipped here; ra.check reports
it as FM_INVALID. Bad content never raises, and nothing is printed: ra.cli_stats prints.
"""

from collections import Counter
from pathlib import Path
from typing import Any

from ra import frontmatter
from ra.check import run_checks
from ra.knowledge import parse_facts
from ra.literature import Claim, parse_claims

__all__ = ["stats"]

_NOT_TOPICS = ("README.md", "glossary.md")  # as in ra.check: files of knowledge/ with no facts


def stats(repo: Path) -> dict[str, int]:
    """Count the pilot metrics of the project repository at repo.

    A paper is a literature/*.md file whose frontmatter parses. An unverified claim has no
    verified-by entry whose person (the text before the first ' · ') differs from the person
    in its by; a claim without a by is unverified only if it has no verified-by entry at all,
    and a disputed-by entry is no verification (spec §14). A claim with a disputed-by entry is
    disputed. Duplicate records and edited decisions are the DUP_LITERATURE and DECISION_EDITED
    findings of run_checks, one per pair and one per decision. An open question is a
    questions/*.md file with 'status: open'. A fact is in conflict when its status starts with
    CONFLICT in any case, as ra.knowledge reads the status; knowledge/README.md and
    knowledge/glossary.md are not read. Names starting with '.' are skipped everywhere.

    Args:
        repo: Root of the project repository.

    Returns:
        The eight counts, keyed as in the module docstring and in that order.
    """
    papers = _records(repo, "literature")
    claims = [claim for _, body in papers for claim in parse_claims(body)]
    findings = Counter(finding.code for finding in run_checks(repo))
    topics = [path for path in _markdown(repo / "knowledge") if path.name not in _NOT_TOPICS]
    return {
        "papers": len(papers),
        "claims": len(claims),
        "unverified_claims": sum(_unverified(claim) for claim in claims),
        "disputed_claims": sum(bool(claim.disputed_by) for claim in claims),
        "duplicate_records": findings["DUP_LITERATURE"],
        "decisions_edited": findings["DECISION_EDITED"],
        "open_questions": sum(
            meta.get("status") == "open" for meta, _ in _records(repo, "questions")
        ),
        "conflict_facts": sum(_in_conflict(path) for path in topics),
    }


def _markdown(directory: Path) -> list[Path]:
    """The .md files directly inside directory, sorted; names starting with '.' are skipped."""
    if not directory.is_dir():
        return []
    return sorted(
        entry for entry in directory.iterdir()
        if entry.is_file() and entry.suffix == ".md" and not entry.name.startswith(".")
    )


def _records(repo: Path, folder: str) -> list[tuple[dict[Any, Any], str]]:
    """The (frontmatter, body) of each .md file inside repo/folder whose frontmatter parses."""
    records = []
    for path in _markdown(repo / folder):
        try:
            records.append(frontmatter.parse(path))
        except (frontmatter.FrontmatterError, OSError):
            continue  # ra.check reports the file as FM_INVALID
    return records


def _person(entry: str) -> str:
    """The person of a 'Person · agent · date' entry: the text before the first ' · '."""
    return entry.split(" · ", 1)[0].strip()


def _unverified(claim: Claim) -> bool:
    """True if no verified-by entry of claim is from a person other than the one in its by."""
    author = _person(claim.by) if claim.by else None  # without an author, any verifier counts
    return not any(_person(entry) != author for entry in claim.verified_by)


def _in_conflict(topic: Path) -> int:
    """The number of fact lines of the topic file whose status starts with CONFLICT."""
    try:
        text = topic.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return 0
    return sum((fact.status or "").casefold().startswith("conflict") for fact in parse_facts(text))
