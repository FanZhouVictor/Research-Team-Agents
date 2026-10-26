"""Validate a project repository: the one hard check both AIs run before every commit.

run_checks(repo) reads the files directly inside questions/, decisions/, literature/,
literature/pdf/, log/ and knowledge/ (names starting with '.' are skipped) and returns one
Finding per problem. Root files (PROJECT.md, PROTOCOL.md, ...) and protocol/ are never read.

    FM_INVALID             frontmatter unreadable, a required key missing, or the id or
                           citekey not equal to the file name
    BAD_FILENAME           a file name that breaks the naming rule of its folder
    CLAIM_NO_WHERE         a literature claim whose where is absent, empty or '—'
    PDF_MISSING            a record's pdf: empty, not literature/pdf/<citekey>.pdf, or no file
    DUP_LITERATURE         two records with the same DOI or arXiv id
    DISPUTED_IN_KNOWLEDGE  a knowledge fact whose source claim is disputed
    TOPIC_UNREGISTERED     a topic file without its '- <topic> — ' line in knowledge/README.md
    DECISION_EDITED        an accepted decision changed in a line other than status: or
                           superseded-by: (read from git history and the working tree)

Bad content never raises: it is reported as a finding. Fact and parse_fact_line live in
ra.knowledge and are re-exported here.
"""

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ra import frontmatter
from ra.knowledge import Fact, parse_fact_line, parse_facts
from ra.literature import Claim, parse_claims
from ra.newfile import DECISION_KEYS, LITERATURE_KEYS, LOG_KEYS, QUESTION_KEYS

__all__ = ["Fact", "Finding", "decision_edited_in_place", "parse_fact_line", "run_checks"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Finding:
    """One problem: its code, the file (relative to the repository) and a one-line message."""

    code: str
    path: Path
    message: str


@dataclass(frozen=True)
class _Folder:
    """A scanned folder: its file-name rule and, for frontmatter files, the required keys."""

    path: str
    name: re.Pattern[str]
    rule: str  # the naming rule in words, for BAD_FILENAME messages
    keys: tuple[str, ...] = ()
    identity: str | None = None  # the key whose value must equal the file name without .md


@dataclass(frozen=True)
class _Record:
    """A frontmatter file that parsed: its repo-relative path, frontmatter and body."""

    path: Path
    meta: dict[Any, Any]
    body: str


_FOLDERS = (
    _Folder("questions", re.compile(r"Q-\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.md"),
            "Q-<YYYY-MM-DD>-<slug>.md, slug [a-z0-9-]+", QUESTION_KEYS, "id"),
    _Folder("decisions", re.compile(r"D-\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.md"),
            "D-<YYYY-MM-DD>-<slug>.md, slug [a-z0-9-]+", DECISION_KEYS, "id"),
    _Folder("literature", re.compile(r"[a-z0-9-]+\.md"),
            "<citekey>.md, citekey [a-z0-9-]+", LITERATURE_KEYS, "citekey"),
    _Folder("literature/pdf", re.compile(r"[a-z0-9-]+\.pdf"), "<citekey>.pdf, citekey [a-z0-9-]+"),
    _Folder("log", re.compile(r"\d{4}-\d{2}-\d{2}-[\w-]+-(claude-code|codex)-\d{4}\.md"),
            "<YYYY-MM-DD>-<person>-<claude-code|codex>-<HHMM>.md", LOG_KEYS),
    _Folder("knowledge", re.compile(r"[a-z0-9-]+\.md"), "<topic>.md, topic [a-z0-9-]+"),
)
_REGISTRY = Path("knowledge", "README.md")
_NOT_TOPICS = (_REGISTRY, Path("knowledge", "glossary.md"))

_DOI_PREFIXES = ("doi:", "https://doi.org/", "http://doi.org/", "https://dx.doi.org/")
_ARXIV_PREFIXES = ("arxiv:", "https://arxiv.org/abs/")
_ARXIV_VERSION = re.compile(r"v[0-9]+$")

_SETTLED = ("accepted", "superseded")  # decision statuses whose text is frozen
_MAY_CHANGE = ("status:", "superseded-by:")  # the only lines an accepted decision may change
_SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


def run_checks(repo: Path) -> list[Finding]:
    """Check the project repository at repo.

    Returns:
        The findings, sorted by path, code and message; [] for a clean repository. Bad
        content never raises: an unreadable or malformed file gives a finding. If repo is
        not a git repository, DECISION_EDITED is skipped with a logged warning.
    """
    findings: list[Finding] = []
    parsed: dict[str, list[_Record]] = {folder.path: [] for folder in _FOLDERS}
    topics: list[Path] = []
    for folder in _FOLDERS:
        for rel in _files(repo, folder.path):
            if rel not in _NOT_TOPICS and folder.name.fullmatch(rel.name) is None:
                findings.append(_finding("BAD_FILENAME", rel, f"the name should be {folder.rule}"))
            if rel.suffix != ".md":
                continue
            if folder.keys:
                problems, record = _read_record(repo, rel, folder)
                findings += problems
                if record is not None:
                    parsed[folder.path].append(record)
            elif folder.path == "knowledge":
                topics.append(rel)
    papers = parsed["literature"]
    claims = {paper.path.stem: parse_claims(paper.body) for paper in papers}
    findings += _claims_without_where(repo, papers, claims)
    findings += _pdfs(repo, papers)
    findings += _duplicates(papers)
    findings += _knowledge(repo, topics, claims)
    findings += _edited_decisions(repo, parsed["decisions"])
    return sorted(findings, key=lambda found: (str(found.path), found.code, found.message))


def decision_edited_in_place(repo: Path, path: Path) -> bool:
    """True if an accepted decision changed in a line other than status: or superseded-by:.

    The reference is the oldest commit whose diff added or removed 'status: accepted' in
    the file (git log --reverse -S); it is compared with the working tree, so an
    uncommitted edit counts. Only lines inside the diff's hunks are read.

    Args:
        repo: Root of the git work tree.
        path: The decision file: absolute, or relative to repo.

    Returns:
        True if a changed line starts with neither prefix. False when the file has no such
        commit or git fails (git failures are logged as warnings).
    """
    rel = _relative(repo, path).as_posix()
    log = _git(repo, "log", "--reverse", "-Sstatus: accepted", "--format=%H", "--", rel)
    first = next((word for word in (log or "").split() if _SHA.fullmatch(word)), None)
    if first is None:
        return False
    diff = _git(repo, "diff", "--no-color", "--no-ext-diff", first, "--", rel)
    return any(not line.lstrip().startswith(_MAY_CHANGE) for line in _changed_lines(diff or ""))


# --- files and frontmatter -----------------------------------------------------------------


def _files(repo: Path, folder: str) -> list[Path]:
    """The files directly inside repo/folder, relative to repo and sorted; '.' names skipped."""
    directory = repo / folder
    if not directory.is_dir():
        return []
    return sorted(
        Path(folder, entry.name)
        for entry in directory.iterdir()
        if entry.is_file() and not entry.name.startswith(".")
    )


def _read(path: Path) -> str | None:
    """The text of path as UTF-8, undecodable bytes replaced; None if it cannot be read."""
    try:
        with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
            return handle.read()
    except OSError:
        return None


def _finding(code: str, path: Path, message: str) -> Finding:
    """A Finding whose message is folded onto one line."""
    return Finding(code, path, " ".join(message.split()))


def _read_record(repo: Path, rel: Path, folder: _Folder) -> tuple[list[Finding], _Record | None]:
    """Parse a frontmatter file: FM_INVALID findings, and the record (None if unparseable)."""
    path = repo / rel
    try:
        meta, body = frontmatter.parse(path)
    except frontmatter.FrontmatterError as exc:
        return [_finding("FM_INVALID", rel, str(exc).removeprefix(f"{path}: "))], None
    except OSError as exc:
        return [_finding("FM_INVALID", rel, f"cannot read the file: {exc.strerror or exc}")], None
    findings = []
    missing = [key for key in folder.keys if key not in meta]
    if missing:
        findings.append(_finding("FM_INVALID", rel, f"missing key(s): {', '.join(missing)}"))
    key = folder.identity
    if key is not None and key in meta and meta[key] != rel.stem:
        message = f"{key} is {meta[key]!r}, expected {rel.stem!r} (the file name)"
        findings.append(_finding("FM_INVALID", rel, message))
    return findings, _Record(rel, meta, body)


# --- literature ----------------------------------------------------------------------------


def _claims_without_where(
    repo: Path, papers: list[_Record], claims: dict[str, list[Claim]]
) -> list[Finding]:
    """CLAIM_NO_WHERE for each claim whose where is absent, empty or '—', with its file line."""
    findings = []
    for paper in papers:
        bad = [claim for claim in claims[paper.path.stem]
               if (claim.where or "").strip() in ("", "—")]
        if not bad:
            continue
        text = _read(repo / paper.path) or ""
        # Claim.line counts within the body; the lines before the body are the frontmatter.
        head = text[: len(text) - len(paper.body)] if text.endswith(paper.body) else ""
        for claim in bad:
            number = head.count("\n") + claim.line
            message = f'line {number}: claim without a where: "{_clip(claim.text)}"'
            findings.append(_finding("CLAIM_NO_WHERE", paper.path, message))
    return findings


def _clip(text: str, limit: int = 60) -> str:
    """text cut to at most limit characters, ending in '...' when it was cut."""
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _pdfs(repo: Path, papers: list[_Record]) -> list[Finding]:
    """PDF_MISSING when pdf: is empty, is not literature/pdf/<citekey>.pdf, or has no file."""
    findings = []
    for paper in papers:
        expected = f"literature/pdf/{paper.path.stem}.pdf"
        pdf = paper.meta.get("pdf")
        if not pdf:
            problem = f"no pdf: given, expected {expected}"
        elif pdf != expected:
            problem = f"pdf: is {pdf}, expected {expected}"
        elif not (repo / expected).is_file():
            problem = f"{expected} does not exist"
        else:
            continue
        findings.append(_finding("PDF_MISSING", paper.path, problem))
    return findings


def _normalised(value: object, prefixes: tuple[str, ...]) -> str:
    """value stripped and case-folded, minus the first of prefixes it starts with; '' if not str."""
    if not isinstance(value, str):
        return ""
    text = value.strip().casefold()
    for prefix in prefixes:
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def _doi(value: object) -> str:
    """A DOI for comparison: case-folded, without a doi: or doi.org prefix; '' if none."""
    return _normalised(value, _DOI_PREFIXES)


def _arxiv(value: object) -> str:
    """An arXiv id for comparison: case-folded, without an arxiv: prefix or vN version."""
    return _ARXIV_VERSION.sub("", _normalised(value, _ARXIV_PREFIXES))


def _duplicates(papers: list[_Record]) -> list[Finding]:
    """DUP_LITERATURE once per pair of records sharing a DOI or arXiv id, on the later file."""
    shared: dict[tuple[Path, Path], list[str]] = {}
    for key, normalise in (("doi", _doi), ("arxiv", _arxiv)):
        groups: dict[str, list[Path]] = {}
        for paper in papers:
            value = normalise(paper.meta.get(key))
            if value:
                groups.setdefault(value, []).append(paper.path)
        for value, paths in groups.items():
            ordered = sorted(paths, key=str)
            for index, later in enumerate(ordered):
                for earlier in ordered[:index]:
                    shared.setdefault((earlier, later), []).append(f"{key} {value}")
    return [
        _finding("DUP_LITERATURE", later, f"same {' and '.join(keys)} as {earlier.as_posix()}")
        for (earlier, later), keys in shared.items()
    ]


# --- knowledge -----------------------------------------------------------------------------


def _knowledge(repo: Path, topics: list[Path], claims: dict[str, list[Claim]]) -> list[Finding]:
    """TOPIC_UNREGISTERED and DISPUTED_IN_KNOWLEDGE for the .md files of knowledge/."""
    registry = [line.strip() for line in (_read(repo / _REGISTRY) or "").split("\n")]
    findings = []
    for rel in topics:
        entry = f"- {rel.stem} — "
        if rel not in _NOT_TOPICS and not any(line.startswith(entry) for line in registry):
            message = f"no '{entry}<scope>' line in knowledge/README.md"
            findings.append(_finding("TOPIC_UNREGISTERED", rel, message))
        for fact in parse_facts(_read(repo / rel) or ""):
            if _cites_disputed_claim(fact, claims):
                source = f'{fact.citekey} "{fact.where}"'
                message = f"line {fact.line}: source {source} is a disputed claim"
                findings.append(_finding("DISPUTED_IN_KNOWLEDGE", rel, message))
    return findings


def _squash(text: str | None) -> str:
    """text with runs of whitespace made one space, case-folded; '' for None."""
    return " ".join((text or "").split()).casefold()


def _cites_disputed_claim(fact: Fact, claims: dict[str, list[Claim]]) -> bool:
    """Whether the record fact.citekey has a claim at fact.where with a disputed-by entry."""
    where = _squash(fact.where)
    if fact.citekey is None or not where:
        return False
    return any(
        claim.disputed_by and _squash(claim.where) == where
        for claim in claims.get(fact.citekey, [])
    )


# --- decisions -----------------------------------------------------------------------------


def _edited_decisions(repo: Path, decisions: list[_Record]) -> list[Finding]:
    """DECISION_EDITED for accepted or superseded decisions edited since their acceptance."""
    settled = [decision.path for decision in decisions if decision.meta.get("status") in _SETTLED]
    if not settled:
        return []
    if not (repo / ".git").exists():
        logger.warning("%s is not a git repository: DECISION_EDITED was not checked", repo)
        return []
    message = "edited after acceptance: only status: and superseded-by: may change"
    return [_finding("DECISION_EDITED", rel, message)
            for rel in settled if decision_edited_in_place(repo, rel)]


def _relative(repo: Path, path: Path) -> Path:
    """path relative to repo; path is absolute, starts with repo, or is relative to repo.

    Only an absolute path is resolved: a relative one never depends on the current directory.
    """
    try:
        return path.relative_to(repo)
    except ValueError:
        pass
    if path.is_absolute():
        try:
            return path.resolve().relative_to(repo.resolve())
        except ValueError:
            pass
    return path


def _git(repo: Path, *args: str) -> str | None:
    """Run git with args in repo and return its output; None, with a warning, if it fails."""
    try:
        done = subprocess.run(
            ["git", "-c", "core.quotepath=false", *args],
            check=True, text=True, capture_output=True, cwd=repo,
            encoding="utf-8", errors="replace",
        )
    except subprocess.CalledProcessError as exc:
        logger.warning("git %s failed in %s: %s", args[0], repo, exc.stderr.strip())
        return None
    except OSError as exc:
        logger.warning("cannot run git in %s: %s", repo, exc)
        return None
    return done.stdout


def _changed_lines(diff: str) -> list[str]:
    """The added and removed lines of a one-file diff, without their '+' or '-' marker.

    Only lines after the first '@@' hunk header count: the '---' and '+++' file header is
    skipped, while a removed '---' line of the file itself (diff line '----') still counts.
    """
    changed = []
    in_hunks = False
    for line in diff.split("\n"):
        if line.startswith("@@"):
            in_hunks = True
        elif in_hunks and line[:1] in ("+", "-"):
            changed.append(line[1:])
    return changed
