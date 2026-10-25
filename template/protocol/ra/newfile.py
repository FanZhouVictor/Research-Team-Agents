"""Create the files of the shared-repo protocol: questions, decisions, literature, logs, topics.

Each new_* function validates its input, builds the YAML frontmatter as a Python mapping
(so frontmatter.write decides quoting and typing) and takes the Markdown body from the
template file of the same kind in protocol/templates/, the single source of the body text.
A creator checks everything before it writes anything and never overwrites a file.

A template file becomes a body like this:
- The frontmatter block documents the keys with {placeholder} values. The code does not read
  it; a test keeps its keys equal to the *_KEYS tuples below.
- HTML comments are notes for people who edit the template. They are not copied.
- '{word}' tokens are replaced by the creator's values. Tokens it has no value for, and any
  other braces (BibTeX), stay as they are.
"""

import re
import shutil
from collections.abc import Mapping
from contextlib import ExitStack
from datetime import date, datetime
from pathlib import Path
from typing import Any

from ra import frontmatter

__all__ = [
    "AGENTS",
    "DECISION_KEYS",
    "LITERATURE_KEYS",
    "LOG_KEYS",
    "QUESTION_KEYS",
    "RELEVANCE",
    "TEMPLATES_DIR",
    "new_decision",
    "new_literature",
    "new_log",
    "new_question",
    "new_topic",
]

# Frontmatter keys of each file type, in file order. Every key is written, None (or [] for
# lists) when unknown; the validator in check.py requires all of them.
LITERATURE_KEYS: tuple[str, ...] = (
    "citekey", "title", "authors", "year", "venue", "doi", "arxiv", "pdf",
    "relevance", "bears-on", "readers", "code", "data", "related",
)
QUESTION_KEYS: tuple[str, ...] = (
    "id", "title", "status", "proposed-by", "approved-by", "answered-by", "closed-by",
)
DECISION_KEYS: tuple[str, ...] = (
    "id", "title", "status", "proposed-by", "accepted-by", "supersedes", "superseded-by", "links",
)
LOG_KEYS: tuple[str, ...] = ("date", "person", "agent", "session", "dual-run")

AGENTS: tuple[str, ...] = ("claude-code", "codex")
RELEVANCE: tuple[str, ...] = ("core", "supporting", "background", "not-useful")

# protocol/templates next to protocol/ra: the same in the framework repo (template/protocol/)
# and in a generated project (protocol/).
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

_DERIVED = ("citekey", "pdf", "readers")  # literature keys that new_literature sets itself
_READER = ("person", "agent", "date")  # meta entries that describe the first reader
_LISTS = ("authors", "bears-on", "related")  # literature keys that default to []

_NAME = re.compile(r"[a-z0-9-]+")
_DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_TOKEN = re.compile(r"\{(\w+)\}")
_COMMENT = re.compile(r"<!--.*?-->[ \t]*\n?", re.DOTALL)
_FRONTMATTER = re.compile(r"\A---\n.*?^---[ \t]*\n", re.DOTALL | re.MULTILINE)


def _check_name(value: str, label: str) -> None:
    """Raise ValueError unless value is made of lower-case letters, digits and hyphens."""
    if _NAME.fullmatch(value) is None:
        raise ValueError(f"{label} must match [a-z0-9-]+, got {value!r}")


def _check_who(person: Any, agent: Any) -> None:
    """Raise ValueError unless person is a non-blank string and agent is one of AGENTS."""
    if not isinstance(person, str) or not person.strip():
        raise ValueError("person must not be empty")
    if agent not in AGENTS:
        raise ValueError(f"agent must be one of {', '.join(AGENTS)}, got {agent!r}")


def _iso_day(value: object) -> str:
    """Return value (a date, or a 'YYYY-MM-DD' string) as 'YYYY-MM-DD'; ValueError otherwise."""
    if isinstance(value, date):  # a datetime is a date too: keep its day only
        return (value.date() if isinstance(value, datetime) else value).isoformat()
    if isinstance(value, str) and _DAY.fullmatch(value):
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError:
            pass  # right shape, not a real day, e.g. 2026-13-01
    raise ValueError(f"date must be a real day as YYYY-MM-DD, got {value!r}")


def _as_list(key: str, value: Any) -> list[Any]:
    """Return a new list from a list or tuple; None gives []; anything else is a ValueError."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    raise ValueError(f"{key} must be a list, got {value!r}")


def _ordered(keys: tuple[str, ...], values: Mapping[str, Any]) -> dict[str, Any]:
    """Return the given keys in order, each with its value from values or None."""
    return {key: values.get(key) for key in keys}


def _body(name: str, values: Mapping[str, str]) -> str:
    """Return the body of TEMPLATES_DIR/<name>.md with its {word} tokens filled from values."""
    text = (TEMPLATES_DIR / f"{name}.md").read_text(encoding="utf-8")
    block = _FRONTMATTER.match(text)
    body = _COMMENT.sub("", text[block.end() :] if block else text)
    return _TOKEN.sub(lambda token: values.get(token.group(1), token.group(0)), body)


def _refuse_existing(repo: Path, *paths: Path) -> None:
    """Raise FileExistsError for the first of paths that exists."""
    for path in paths:
        if path.exists():
            raise FileExistsError(f"{path.relative_to(repo).as_posix()} already exists")


def _append_line(path: Path, line: str) -> None:
    """Append line to a text file, first ending its last line if that is unterminated."""
    existing = path.read_text(encoding="utf-8")
    lead = "" if not existing or existing.endswith("\n") else "\n"
    with path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(f"{lead}{line}\n")


def _create(repo: Path, rel: Path, template: str, meta: dict[str, Any]) -> Path:
    """Write the frontmatter file rel (relative to repo) from meta and the template's body."""
    path = repo / rel
    _refuse_existing(repo, path)
    frontmatter.write(path, meta, _body(template, {}))
    return path


def new_question(repo: Path, slug: str, title: str, person: str, agent: str, day: date) -> Path:
    """Create questions/Q-<day>-<slug>.md: an open question proposed by person and agent.

    The id and the file name carry day, so a slug can be reused on another day. person is
    written as given; agent is claude-code or codex; slug is [a-z0-9-]+. Returns the path.

    Raises:
        ValueError: slug, person, agent or day is invalid.
        FileExistsError: the file exists (same slug, same day); nothing is written.
    """
    _check_name(slug, "slug")
    _check_who(person, agent)
    stamp = _iso_day(day)
    qid = f"Q-{stamp}-{slug}"
    meta = _ordered(QUESTION_KEYS, {
        "id": qid,
        "title": title,
        "status": "open",
        "proposed-by": {"person": person, "agent": agent, "date": stamp},
    })
    return _create(repo, Path("questions", f"{qid}.md"), "question", meta)


def new_decision(
    repo: Path, slug: str, title: str, person: str, agent: str, day: date, links: list[str]
) -> Path:
    """Create decisions/D-<day>-<slug>.md: a decision in status proposed, by person and agent.

    links lists the question ids and repo paths the decision rests on (may be empty). The
    other arguments are as for new_question. Returns the path.

    Raises:
        ValueError: slug, person, agent or day is invalid.
        FileExistsError: the file exists (same slug, same day); nothing is written.
    """
    _check_name(slug, "slug")
    _check_who(person, agent)
    stamp = _iso_day(day)
    did = f"D-{stamp}-{slug}"
    meta = _ordered(DECISION_KEYS, {
        "id": did,
        "title": title,
        "status": "proposed",
        "proposed-by": {"person": person, "agent": agent, "date": stamp},
        "links": list(links),
    })
    return _create(repo, Path("decisions", f"{did}.md"), "decision", meta)


def new_literature(repo: Path, citekey: str, meta: Mapping[str, Any], pdf_src: Path) -> Path:
    """Create literature/<citekey>.md and copy the paper to literature/pdf/<citekey>.pdf.

    The first reader is built from the person, agent and date entries of meta, which are
    not kept as top-level keys. meta is not modified.

    Args:
        repo: Project root.
        citekey: [a-z0-9-]+, e.g. smith2024-plume-goes.
        meta: person, agent and date (required), plus any of title, authors, year, venue,
            doi, arxiv, relevance, bears-on, code, data, related. Missing keys become None;
            authors, bears-on and related become []. citekey, pdf and readers are derived
            here and not accepted.
        pdf_src: The paper's PDF.

    Returns:
        Path of the new record.

    Raises:
        ValueError: citekey or meta is invalid (unexpected key, missing person, agent or date,
            bad agent or relevance, bad date, a list key that is not a list).
        FileNotFoundError: pdf_src is not a file.
        FileExistsError: the record or its PDF exists; nothing is written.
    """
    _check_name(citekey, "citekey")
    allowed = [key for key in LITERATURE_KEYS if key not in _DERIVED] + list(_READER)
    stray = sorted(str(key) for key in meta if key not in allowed)
    if stray:
        raise ValueError(
            f"unexpected meta key(s): {', '.join(stray)} (allowed: {', '.join(allowed)})"
        )
    missing = [key for key in _READER if key not in meta]
    if missing:
        raise ValueError(f"meta must name the first reader, missing: {', '.join(missing)}")
    _check_who(meta["person"], meta["agent"])
    stamp = _iso_day(meta["date"])
    relevance = meta.get("relevance")
    if relevance is not None and relevance not in RELEVANCE:
        raise ValueError(f"relevance must be one of {', '.join(RELEVANCE)}, got {relevance!r}")

    pdf_rel = Path("literature", "pdf", f"{citekey}.pdf")
    values: dict[str, Any] = {key: meta[key] for key in meta if key in LITERATURE_KEYS}
    values.update({key: _as_list(key, meta.get(key)) for key in _LISTS})
    values["citekey"] = citekey
    values["pdf"] = pdf_rel.as_posix()
    values["readers"] = [
        {"person": meta["person"], "agent": meta["agent"], "date": stamp, "read": "full-text"}
    ]
    front = _ordered(LITERATURE_KEYS, values)

    if not pdf_src.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_src}")
    record = repo / "literature" / f"{citekey}.md"
    pdf_dest = repo / pdf_rel
    _refuse_existing(repo, record, pdf_dest)
    body = _body("literature", {"citekey": citekey})
    with ExitStack() as undo:  # an error below removes the copied PDF
        undo.callback(pdf_dest.unlink, missing_ok=True)
        shutil.copyfile(pdf_src, pdf_dest)
        frontmatter.write(record, front, body)
        undo.pop_all()
    return record


def new_log(repo: Path, person: str, agent: str, start: datetime) -> Path:
    """Create log/<date>-<person>-<agent>-<HHMM>.md for a session that starts at start.

    The file name uses the lower-cased person (which must match [a-z0-9-]+), the frontmatter
    keeps the given spelling. The session value is the start time followed by an en dash
    ("14:32–"); session-end fills in the end time. Returns the path.

    Raises:
        ValueError: person or agent is invalid.
        FileExistsError: the file exists (same person, agent and minute); nothing is written.
    """
    _check_who(person, agent)
    _check_name(person.lower(), "lower-cased person (it names the log file)")
    stamp = start.date().isoformat()
    meta = _ordered(LOG_KEYS, {
        "date": stamp,
        "person": person,
        "agent": agent,
        "session": f"{start:%H:%M}–",
    })
    name = f"{stamp}-{person.lower()}-{agent}-{start:%H%M}.md"
    return _create(repo, Path("log", name), "log", meta)


def new_topic(repo: Path, topic: str, scope: str) -> Path:
    """Create knowledge/<topic>.md and add '- <topic> — <scope>' to knowledge/README.md.

    The file has no frontmatter: a '# <topic>' line, the scope line and a blank line; fact
    lines are appended later by other commands. topic is [a-z0-9-]+, scope is one non-empty
    line. Returns the path.

    Raises:
        ValueError: topic or scope is invalid.
        FileNotFoundError: knowledge/README.md does not exist.
        FileExistsError: the topic file exists; nothing is written.
    """
    _check_name(topic, "topic")
    if not scope.strip() or scope.splitlines() != [scope]:
        raise ValueError("scope must be one non-empty line of text")
    path = repo / "knowledge" / f"{topic}.md"
    registry = repo / "knowledge" / "README.md"
    _refuse_existing(repo, path)
    if not registry.is_file():
        raise FileNotFoundError("knowledge/README.md (the topic registry) not found")
    text = _body("topic", {"topic": topic, "scope": scope})
    with ExitStack() as undo:  # an error below removes the topic file again
        undo.callback(path.unlink, missing_ok=True)
        path.write_text(text, encoding="utf-8", newline="")
        _append_line(registry, f"- {topic} — {scope}")
        undo.pop_all()
    return path
