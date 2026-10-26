"""Find the literature record that already exists, so that a second one is never created.

Spec §10.2: before a record is created, match on DOI, then arXiv id, then normalised title.
find_existing() does the lookup in literature/. The three normalisers say when two values
name the same paper; ra.check uses the DOI and arXiv ones for its DUP_LITERATURE rule.

A value with nothing to compare normalises to None, and None never matches anything: no
text, no letter or digit in it (only punctuation or dashes such as '—'), or a placeholder
word (n/a, na, none, null, tbd, todo, unknown).
"""

import logging
import re
from pathlib import Path
from typing import Any

from ra import frontmatter

__all__ = ["find_existing", "normalize_arxiv", "normalize_doi", "normalize_title"]

logger = logging.getLogger(__name__)

_DOI_PREFIXES = (
    "doi:", "https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/",
)
_ARXIV_PREFIXES = ("arxiv:", "https://arxiv.org/abs/", "http://arxiv.org/abs/")
_ARXIV_VERSION = re.compile(r"v[0-9]+$")
_PLACEHOLDERS = frozenset({"n/a", "na", "none", "null", "tbd", "todo", "unknown"})


def normalize_doi(value: str | None) -> str | None:
    """A DOI as it is compared: stripped, one doi: or doi.org prefix removed, case-folded.

    'https://doi.org/10.1016/J.RSE.2024.1' gives '10.1016/j.rse.2024.1'. The result is
    None for None, for anything that is not a str, and for a value with nothing to compare.
    """
    return _comparable(_unprefixed(value, _DOI_PREFIXES))


def normalize_arxiv(value: str | None) -> str | None:
    """An arXiv id as it is compared: prefix and version removed, case-folded.

    Stripped, then one leading arxiv: or arxiv.org/abs prefix and a trailing version vN are
    removed: 'arXiv:2401.10250v2' gives '2401.10250'. The result is None for None, for
    anything that is not a str, and for a value with nothing to compare.
    """
    text = _unprefixed(value, _ARXIV_PREFIXES)
    return _comparable(None if text is None else _ARXIV_VERSION.sub("", text))


def normalize_title(value: str | None) -> str | None:
    """A title as it is compared: case-folded, keeping only letters and digits (any script).

    'Smoke-Plume Segmentation: A Study' gives 'smokeplumesegmentationastudy'. The result
    is None for None, for anything that is not a str, and for a value with nothing to compare.
    """
    if not isinstance(value, str):
        return None
    return _comparable("".join(char for char in value.casefold() if char.isalnum()))


def find_existing(
    repo: Path, doi: str | None = None, arxiv: str | None = None, title: str | None = None
) -> Path | None:
    """The record in repo/literature that is the paper described by doi, arxiv or title.

    The priority is strict: the first record whose DOI equals doi; if there is none, the
    first whose arXiv id equals arxiv; if there is none, the first whose title equals title.
    Both sides are normalised first, a query that normalises to None is not tried, and
    "first" is file-name order. Only the .md files directly inside literature/ are read,
    dot-files skipped; a record whose frontmatter cannot be parsed is skipped silently
    (ra check reports it).

    Args:
        repo: Project root.
        doi: DOI of the paper, in any form normalize_doi accepts.
        arxiv: arXiv id of the paper, in any form normalize_arxiv accepts.
        title: Title of the paper.

    Returns:
        Path of the record, repo / "literature" / "<citekey>.md"; None if no record
        matches or repo has no literature folder.

    Raises:
        ValueError: doi, arxiv and title are all None.
        OSError: a record cannot be read.
    """
    if doi is None and arxiv is None and title is None:
        raise ValueError("give at least one of doi, arxiv or title to look for")
    queries = (
        ("doi", normalize_doi, normalize_doi(doi)),
        ("arxiv", normalize_arxiv, normalize_arxiv(arxiv)),
        ("title", normalize_title, normalize_title(title)),
    )
    records = _records(repo)
    for key, normalise, wanted in queries:
        if wanted is None:
            continue
        for path, meta in records:
            if normalise(meta.get(key)) == wanted:
                return path
    return None


def _records(repo: Path) -> list[tuple[Path, dict[Any, Any]]]:
    """The records in repo/literature whose frontmatter parses, as (path, frontmatter)."""
    folder = repo / "literature"
    if not folder.is_dir():
        return []
    records = []
    for path in sorted(folder.iterdir()):
        if path.suffix != ".md" or path.name.startswith(".") or not path.is_file():
            continue
        try:
            meta, _ = frontmatter.parse(path)
        except frontmatter.FrontmatterError as exc:
            logger.debug("skipped %s: %s", path, exc)
            continue
        records.append((path, meta))
    return records


def _unprefixed(value: object, prefixes: tuple[str, ...]) -> str | None:
    """value stripped and case-folded, without the first of prefixes it starts with.

    None if value is not a str. Whitespace after the prefix is stripped too.
    """
    if not isinstance(value, str):
        return None
    text = value.strip().casefold()
    for prefix in prefixes:
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def _comparable(text: str | None) -> str | None:
    """text, or None when it has nothing to compare: see the module docstring."""
    if text is None or text in _PLACEHOLDERS or not any(char.isalnum() for char in text):
        return None
    return text
