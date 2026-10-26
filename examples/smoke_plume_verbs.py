"""The protocol verbs that the history of the example project smoke-plume is made of.

Each verb writes files the way a person and their AI would, through the ra package only
(ra.newfile creates files, ra.frontmatter edits them), takes its text from
smoke_plume_content.py or smoke_plume_sessions.py, and returns the Write that
build_smoke_plume.py commits. Who, with which agent and on which day comes from the Step, so a
file and its commit always agree.
Import this module through build_smoke_plume.py, which puts template/protocol on sys.path.
"""

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import smoke_plume_content as content
import smoke_plume_sessions as sessions
from ra import frontmatter
from ra.newfile import new_decision, new_literature, new_log, new_question, new_topic

__all__ = [
    "Step",
    "Write",
    "accept_decision",
    "add_fact",
    "add_literature",
    "author",
    "close_question",
    "propose_decision",
    "propose_question",
    "reread_literature",
    "rewrite_status",
    "set_up_project",
    "supersede_decision",
    "write_log",
]

_PDFS = Path(__file__).resolve().parent / "smoke-plume-src" / "pdf"
_DECISION_SECTIONS = ("Decision", "Alternatives considered", "Rationale and evidence",
                      "Consequences")
_LOG_SECTIONS = ("Done", "Tried and failed", "Unfinished", "Suggested next step", "Files touched")
_HEADING = re.compile(r"^## (.+)$", re.MULTILINE)


@dataclass(frozen=True)
class Write:
    """A logical write that is done: its commit type, subject and the files it involves."""

    type_tag: str
    subject: str
    paths: tuple[str, ...]  # repo-relative files the write added or changed: staged
    cited: tuple[str, ...] = ()  # further repo-relative files the commit message links


@dataclass(frozen=True)
class Step:
    """One logical write of the history: when, by whom, with which agent, what, on which item."""

    when: str  # 'YYYY-MM-DD HH:MM', the time of its commit
    person: str
    agent: str
    verb: "Callable[[Path, Step], Write]"
    key: str = ""  # the content item the verb writes

    @property
    def day(self) -> date:
        """The day of the step."""
        return date.fromisoformat(self.when[:10])


def author(member: Mapping[str, Any]) -> str:
    """'Name <email>' of a member in content."""
    return f"{member['person']} <{member['email']}>"


# --- Markdown sections and small formats -----------------------------------------------------


def _sections(body: str) -> tuple[str, list[tuple[str, str]]]:
    """The text before the first '## ' heading, then each heading with the text under it."""
    marks = list(_HEADING.finditer(body))
    ends = [mark.start() for mark in marks[1:]] + [len(body)]
    head = body[: marks[0].start()] if marks else body
    return head, [(mark[1], body[mark.end() : end].strip("\n")) for mark, end in zip(marks, ends)]


def _section(body: str, heading: str) -> str:
    """The text under '## <heading>' in body, without the blank lines around it."""
    return dict(_sections(body)[1])[heading]


def _fill(body: str, texts: Mapping[str, str]) -> str:
    """body with the text under each heading named in texts replaced by the new text.

    This replaces a template's guidance lines rather than adding to them. Sections keep their
    order, one blank line apart, and the body ends with one newline.

    Raises:
        ValueError: body has no section of that name; the template has changed.
    """
    head, sections = _sections(body)
    missing = sorted(set(texts) - {heading for heading, _ in sections})
    if missing:
        raise ValueError(f"the body has no section {', '.join(missing)}")
    blocks = []
    for heading, text in sections:
        text = texts.get(heading, text).strip("\n")
        blocks.append(f"## {heading}\n{text}\n" if text else f"## {heading}\n")
    return head + "\n".join(blocks)


def _rewrite(path: Path, changes: Mapping[str, Any], texts: Mapping[str, str]) -> None:
    """Set the frontmatter keys in changes and replace the section texts of the file at path."""
    meta, body = frontmatter.parse(path)
    meta.update(changes)
    frontmatter.write(path, meta, _fill(body, texts) if texts else body)


def _bullets(value: str | Sequence[str]) -> str:
    """Section text from content: a str as it is, a list as one '- ' line per item."""
    return value if isinstance(value, str) else "\n".join(f"- {item}" for item in value)


def _who(step: Step) -> str:
    """'<person> · <agent> · <day>': who wrote or verified a claim."""
    return f"{step.person} · {step.agent} · {step.day}"


def _note(step: Step, text: str) -> str:
    """A notes line: '- <day> · <person> · <agent>: <text>'."""
    return f"- {step.day} · {step.person} · {step.agent}: {text}"


def _rel(repo: Path, path: Path) -> str:
    """path relative to repo, with '/' separators."""
    return path.relative_to(repo).as_posix()


def _slug(step: Step, prefix: str) -> str:
    """The slug of the id step.key, which must be '<prefix>-<day of the step>-<slug>'."""
    lead = f"{prefix}-{step.day}-"
    if not step.key.startswith(lead):
        raise ValueError(f"{step.key} cannot be created on {step.day}")
    return step.key[len(lead) :]


# --- PROJECT.md and questions ----------------------------------------------------------------


def set_up_project(repo: Path, step: Step) -> Write:
    """Fill in PROJECT.md: the notice under the title, goals, phase and the second member."""
    path = repo / "PROJECT.md"
    meta, body = frontmatter.parse(path)
    title = f"# {content.NAME}\n"
    if not body.startswith(title):
        raise ValueError(f"PROJECT.md does not start with {title.strip()!r}")
    member = content.MEMBER
    row = (f"| {member['person']} | {author(member)} | {', '.join(member['platforms'])} "
           f"| {member['role']} |")
    body = _fill(body, {
        "Goals": "\n".join(content.PROJECT["goals"]),
        "Members": f"{_section(body, 'Members')}\n{row}",
        "Phase": content.PROJECT["phase"],
    })
    frontmatter.write(path, meta, body.replace(title, f"{title}\n{content.NOTICE}\n", 1))
    return Write("protocol", content.PROJECT["subject"], ("PROJECT.md",))


def rewrite_status(repo: Path, step: Step) -> Write:
    """Rewrite PROJECT.md's Current status after the session logged in step.key."""
    path = repo / "PROJECT.md"
    current = _section(frontmatter.parse(path)[1], "Current status").split("\n")
    comment = [line for line in current if line.startswith("<!--")]  # the section's guidance
    status = _bullets(sessions.STATUS[step.key])
    _rewrite(path, {}, {"Current status": "\n".join([*comment, status])})
    subject = f"current status after the {step.person}/{step.agent} session of {step.day}"
    return Write("status", subject, ("PROJECT.md",), (f"log/{step.key}.md",))


def propose_question(repo: Path, step: Step) -> Write:
    """Create the question step.key, approved at the gate by step.person."""
    item = content.QUESTIONS[step.key]
    path = new_question(repo, _slug(step, "Q"), item["title"], step.person, step.agent, step.day)
    texts = {"Context": item["context"], "Working notes": _note(step, item["note"])}
    _rewrite(path, {"approved-by": step.person}, texts)
    return Write("question", f"proposed {step.key} — {item['subject']}", (_rel(repo, path),))


def close_question(repo: Path, step: Step) -> Write:
    """step.person closes the question step.key as answered, with a closing note."""
    item = content.QUESTIONS[step.key]
    path = repo / "questions" / f"{step.key}.md"
    notes = f"{_section(frontmatter.parse(path)[1], 'Working notes')}\n"
    closed = {"status": "answered", "answered-by": item["answered-by"],
              "closed-by": f"{step.person} · {step.day}"}
    _rewrite(path, closed, {"Working notes": notes + _note(step, item["close note"])})
    return Write("question", f"closed {step.key}", (_rel(repo, path),), (item["answered-by"],))


# --- literature and knowledge ----------------------------------------------------------------


def _claim(fields: Mapping[str, str]) -> str:
    """One claim in the spec §10.3 form: its bullet, then one sub-bullet per other field."""
    lines = [f"- {fields['claim']}"]
    lines += [f"  - {name}: {value}" for name, value in fields.items() if name != "claim"]
    return "\n".join(lines)


def add_literature(repo: Path, step: Step) -> Write:
    """Create the record step.key and its PDF: step.person read it in full with step.agent."""
    item = content.LITERATURE[step.key]
    meta = {**item["meta"], "person": step.person, "agent": step.agent,
            "date": step.day.isoformat()}
    path = new_literature(repo, step.key, meta, _PDFS / f"{step.key}.pdf")
    provenance = {"by": _who(step), "verified-by": "—", "disputed-by": "—"}
    _rewrite(path, {}, {
        "Summary": item["summary"],
        "Why it matters here": item["why"],
        "Claims for this project": "\n".join(_claim({**c, **provenance}) for c in item["claims"]),
        "Notes": _note(step, item["note"]),
        "BibTeX": f"```bibtex\n{item['bibtex']}\n```",
    })
    pdf = f"literature/pdf/{step.key}.pdf"
    questions = tuple(f"questions/{qid}.md" for qid in item["meta"].get("bears-on", []))
    subject = f"added {step.key} — {item['subject']}"
    return Write("literature", subject, (_rel(repo, path), pdf), questions)


def _mark(claims: str, field: str, values: Mapping[int, str]) -> str:
    """A claims section with the empty '<field>: —' of claim n (0-based) set to values[n]."""
    lines = claims.split("\n")
    number, done = -1, set()
    for index, line in enumerate(lines):
        if line.startswith("- "):
            number += 1
        elif number in values and line == f"  - {field}: —":
            lines[index] = f"  - {field}: {values[number]}"
            done.add(number)
    if done != set(values):
        raise ValueError(f"no empty {field} in claim(s) {sorted(set(values) - done)}")
    return "\n".join(lines)


def reread_literature(repo: Path, step: Step) -> Write:
    """step.person re-reads the record step.key in full (spec §10.4 rules 6 and 7)."""
    item = content.REREADS[step.key]
    path = repo / "literature" / f"{step.key}.md"
    meta, body = frontmatter.parse(path)
    reader = {"person": step.person, "agent": step.agent, "date": step.day.isoformat(),
              "read": "full-text"}
    who = _who(step)
    claims = _mark(_section(body, "Claims for this project"), "verified-by",
                   dict.fromkeys(item["verified"], who))
    disputes = {number: f"{who} — {why}" for number, why in item["disputed"].items()}
    summary = _section(body, "Summary").split("\n")
    summary[0] += f" {item['summary']}"  # added detail joins the summary paragraph
    summary.append(f"revised: {step.day} {step.person}/{step.agent} — {item['revised']}")
    _rewrite(path, {"readers": [*meta["readers"], reader]}, {
        "Summary": "\n".join(summary),
        "Claims for this project": _mark(claims, "disputed-by", disputes),
        "Notes": f"{_section(body, 'Notes')}\n{_note(step, item['note'])}",
    })
    counts = f"verified {len(item['verified'])}, disputed {len(disputes)}, added 0 claims"
    return Write("literature", f"re-read {step.key} — {counts}", (_rel(repo, path),))


def add_fact(repo: Path, step: Step) -> Write:
    """Add the fact step.key, approved by step.person; a new topic is registered with it.

    A fact that 'conflicts with' another goes right below it with the status 'CONFLICT with
    line above', and the other fact's status becomes 'CONFLICT with line below': the one edit
    anyone may make to a fact someone else wrote (spec §7).
    """
    fact = content.FACTS[step.key]
    path = repo / "knowledge" / f"{content.TOPIC['name']}.md"
    changed = [_rel(repo, path)]
    if not path.exists():
        new_topic(repo, content.TOPIC["name"], content.TOPIC["scope"])
        changed.append("knowledge/README.md")
    lines = path.read_text(encoding="utf-8").removesuffix("\n").split("\n")
    status = "ok"
    if "conflicts with" in fact:
        if not lines[-1].startswith(f"- {content.FACTS[fact['conflicts with']]['text']} ("):
            raise ValueError(f"{fact['conflicts with']} is not the last line of {path.name}")
        lines[-1] = f"{lines[-1].rpartition(' · ')[0]} · CONFLICT with line below)"
        status = "CONFLICT with line above"
    lines.append(f"- {fact['text']} (src: {fact['src']} · {step.person}/{step.agent} {step.day} "
                 f"· approved {step.person} · {status})")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")
    source = f"literature/{fact['src'].split()[0]}.md"
    return Write("knowledge", fact["subject"], tuple(changed), (source,))


# --- decisions and logs ----------------------------------------------------------------------


def _cited(links: Sequence[str]) -> tuple[str, ...]:
    """The files a decision's links name: a question or decision id becomes its path."""
    folders = {"Q": "questions", "D": "decisions"}
    return tuple(link if "/" in link else f"{folders[link[0]]}/{link}.md" for link in links)


def _new_decision(repo: Path, step: Step, changes: Mapping[str, Any]) -> Path:
    """Create the decision step.key with its four sections, changes set in its frontmatter."""
    item = content.DECISIONS[step.key]
    path = new_decision(repo, _slug(step, "D"), item["title"], step.person, step.agent,
                        step.day, item["links"])
    _rewrite(path, changes, {heading: _bullets(item[heading]) for heading in _DECISION_SECTIONS})
    return path


def _acceptance(step: Step) -> dict[str, str]:
    """The frontmatter of a decision that step.person accepts on the day of step."""
    return {"status": "accepted", "accepted-by": f"{step.person} · {step.day}"}


def propose_decision(repo: Path, step: Step) -> Write:
    """Create the decision step.key in status proposed, with supersedes: if it replaces one."""
    item = content.DECISIONS[step.key]
    path = _new_decision(repo, step, {"supersedes": item.get("supersedes")})
    subject = f"proposed {step.key} — {item['subject']}"
    return Write("decision", subject, (_rel(repo, path),), _cited(item["links"]))


def accept_decision(repo: Path, step: Step) -> Write:
    """step.person accepts the decision step.key."""
    path = repo / "decisions" / f"{step.key}.md"
    _rewrite(path, _acceptance(step), {})
    return Write("decision", f"accepted {step.key}", (_rel(repo, path),))


def supersede_decision(repo: Path, step: Step) -> Write:
    """Give the decision that the accepted decision step.key supersedes its one edit.

    That edit, status superseded and superseded-by, is the only change ever made to an
    accepted decision (spec §7); the commit touches nothing else.

    Raises:
        ValueError: step.key is not accepted yet.
    """
    item = content.DECISIONS[step.key]
    new = repo / "decisions" / f"{step.key}.md"
    if frontmatter.parse(new)[0].get("status") != "accepted":
        raise ValueError(f"{step.key} must be accepted before it supersedes another decision")
    old = repo / "decisions" / f"{item['supersedes']}.md"
    _rewrite(old, {"status": "superseded", "superseded-by": step.key}, {})
    subject = f"superseded {item['supersedes']} by {step.key}"
    return Write("decision", subject, (_rel(repo, old),), (_rel(repo, new),))


def write_log(repo: Path, step: Step) -> Write:
    """Write the session log step.key of step.person and step.agent."""
    item = sessions.LOGS[step.key]
    start = datetime.combine(step.day, time.fromisoformat(item["start"]))
    path = new_log(repo, step.person, step.agent, start)
    if path.stem != step.key:
        raise ValueError(f"the log of this session is {path.name}, not {step.key}.md")
    session = f"{item['start']}–{item['end']}"
    _rewrite(path, {"session": session}, {h: _bullets(item[h]) for h in _LOG_SECTIONS})
    subject = f"session {step.person}/{step.agent} {step.day} {session}"
    return Write("log", subject, (_rel(repo, path),))
