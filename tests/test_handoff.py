"""A two-clone handoff at file level, with ra calls only: no AI is involved.

Clone a is Fan working with claude-code, clone b is Lee working with codex (the git identities
come from the two_clones fixture; the agent is passed to each ra call). Fan adds a paper and
leaves an item in the session log; Lee pulls, re-reads the paper, closes the item in a log of
Lee's own and pushes; Fan pulls. The test pins that these writes (new files, one commit each)
need no merge, that the digest and the files say who did what, and that ra check and ra stats
agree. Human gates and PROJECT.md are left out; the handoff between two AI sessions is checked
by hand (Task 17).
"""

import re
import subprocess
from datetime import date, datetime
from pathlib import Path

from ra.check import run_checks
from ra.commit import commit
from ra.digest import commits_since_last, render
from ra.frontmatter import parse, write
from ra.newfile import new_literature, new_log, new_question
from ra.stats import stats
from ra.sync import pull, push, unmerged_paths

FAN = ("Fan", "claude-code")
LEE = ("Lee", "codex")
CITEKEY = "a2024-x"
QUESTION = "Q-2026-10-26-plume-baselines"
RECORD = Path("literature", f"{CITEKEY}.md")
PDF = Path("literature", "pdf", f"{CITEKEY}.pdf")
ITEM = f"verify the claims of {CITEKEY}"  # what Fan leaves unfinished and Lee finishes
CLAIMS = (  # (claim, where); both bear on QUESTION
    ("The method beats the best baseline by 4.2 mIoU on the held-out season.", "Table 3, p.7"),
    ("The model takes ABI bands 1, 3 and 7 as input.", "§2.1, p.3"),
)
LOG_HEADINGS = ("Done", "Tried and failed", "Unfinished", "Suggested next step", "Files touched")


def _git(repo: Path, *args: str) -> str:
    """Run git in repo and return its output without surrounding whitespace, read as UTF-8."""
    done = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return done.stdout.strip()


def _commit(
    repo: Path, who: tuple[str, str], tag: str, subject: str, *paths: Path,
    cites: tuple[str, ...] = (),
) -> None:
    """Commit paths (relative to repo) as one ra write by who = (person, agent).

    The links are the paths and cites, as the runbooks give them.
    """
    person, agent = who
    links = [path.as_posix() for path in paths] + list(cites)
    commit(repo, list(paths), tag, subject, person, agent, links)


def _section(path: Path, heading: str) -> str:
    """The text under '## <heading>' in the Markdown file at path, up to the next '## '."""
    body = parse(path)[1]
    pattern = rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)"
    found = re.search(pattern, body, re.DOTALL | re.MULTILINE)
    assert found, f"{path.name} has no section {heading!r}"
    return found.group(1).strip()


def _write_record(path: Path) -> None:
    """Replace the guidance of a new record with its first reader's text and two claims.

    Each claim has the seven fields of spec §10.3; verified-by and disputed-by are still '—'.
    """
    claims = "\n".join(
        f"- {text}\n  - where: {where}\n  - bears on: {QUESTION} — supports\n"
        "  - kind: result\n  - basis: stated by paper\n  - by: Fan · claude-code · 2026-10-26\n"
        "  - verified-by: —\n  - disputed-by: —"
        for text, where in CLAIMS
    )
    body = "\n".join([
        "## Summary", "A segmenter for smoke plumes in GOES-16 scenes, tested on a later season.",
        "", "## Why it matters here", f"Its Table 3 number is the bar for {QUESTION}.",
        "", "## Claims for this project", claims,
        "", "## Notes", "- 2026-10-26 · Fan · claude-code: read in full.",
        "", "## BibTeX", "```bibtex", "@article{" + CITEKEY + ", ...}", "```", "",
    ])
    write(path, parse(path)[0], body)


def _reread(path: Path) -> None:
    """Lee, with codex, verifies both claims (reread-literature steps 4, 6 and 7)."""
    meta, body = parse(path)
    assert body.count("verified-by: —") == len(CLAIMS)
    body = body.replace("verified-by: —", "verified-by: Lee · codex · 2026-10-27")
    summary_end = "\n\n## Why it matters here"
    revised = "\nrevised: 2026-10-27 Lee/codex — checked both claims against the PDF"
    body = body.replace(summary_end, revised + summary_end, 1)
    reader = {"person": "Lee", "agent": "codex", "date": "2026-10-27", "read": "full-text"}
    write(path, {**meta, "readers": [*meta["readers"], reader]}, body)


def _fill_log(path: Path, end: str, items: dict[str, list[str]]) -> None:
    """Write the end of the session and the bullets of a new log entry; '- none' where absent."""
    meta = parse(path)[0]
    sections = [
        f"## {heading}\n" + "".join(f"- {item}\n" for item in items.get(heading, ["none"]))
        for heading in LOG_HEADINGS
    ]
    write(path, {**meta, "session": meta["session"] + end}, "\n".join(sections))


def test_handoff_round_trip_file_level(two_clones, tmp_path, make_pdf):
    a, b = two_clones  # a = Fan / claude-code, b = Lee / codex

    # A asks a question, adds a paper that bears on it, leaves an item in the log and pushes.
    question = new_question(a, "plume-baselines", "Which baselines?", *FAN, date(2026, 10, 26))
    meta, body = parse(question)
    write(question, {**meta, "approved-by": "Fan"}, body)
    _commit(a, FAN, "question", f"proposed {QUESTION} — strongest baselines",
            question.relative_to(a))
    paper = tmp_path / f"{CITEKEY}.pdf"
    make_pdf(paper, CITEKEY)
    info = {
        "title": "Plume segmentation from GOES-16", "year": 2024, "doi": "10.1/a2024",
        "person": "Fan", "agent": "claude-code", "date": "2026-10-26",
        "relevance": "core", "bears-on": [QUESTION],
    }
    _write_record(new_literature(a, CITEKEY, info, paper))
    _commit(a, FAN, "literature", f"added {CITEKEY} — plume segmentation from GOES-16",
            RECORD, PDF, cites=(f"questions/{QUESTION}.md",))
    log_a = new_log(a, *FAN, datetime(2026, 10, 26, 14, 32)).relative_to(a)
    _fill_log(a / log_a, "16:05", {
        "Done": [f"proposed {QUESTION}", f"added {CITEKEY}, read in full"],
        "Unfinished": [ITEM],
        "Suggested next step": [f"a second reader re-reads {CITEKEY}"],
        "Files touched": [f"questions/{QUESTION}.md", RECORD.as_posix(), PDF.as_posix(),
                          log_a.as_posix()],
    })
    _commit(a, FAN, "log", "session Fan/claude-code 2026-10-26 14:32–16:05", log_a)
    push(a)

    # B pulls, finds the paper and the unfinished item in the digest and the log it points to,
    # re-reads the paper, closes the item in its own log and pushes.
    pull(b)
    news = commits_since_last(b, "Lee")  # Lee has made no commit yet: the last 20 of the project
    digest = render(news)
    assert f"added {CITEKEY}" in digest and "## log (1)" in digest
    fan_log = next(c.links[0] for c in news if c.type_tag == "log")
    assert fan_log == log_a.as_posix()
    assert ITEM in _section(b / fan_log, "Unfinished")
    _reread(b / RECORD)
    _commit(b, LEE, "literature", f"re-read {CITEKEY} — verified 2, disputed 0, added 0 claims",
            RECORD)
    log_b = new_log(b, *LEE, datetime(2026, 10, 27, 9, 10)).relative_to(b)
    _fill_log(b / log_b, "10:00", {
        "Done": [f"re-read {CITEKEY} in full and verified both claims",
                 f"finished the item of {fan_log}: {ITEM}"],
        "Files touched": [RECORD.as_posix(), log_b.as_posix()],
    })
    _commit(b, LEE, "log", "session Lee/codex 2026-10-27 09:10–10:00", log_b)
    push(b)

    # A pulls: a fast-forward that brings B's two commits, attributed to Lee / codex.
    pull(a)
    assert unmerged_paths(a) == []
    assert _git(a, "rev-parse", "HEAD") == _git(b, "rev-parse", "HEAD")
    assert _git(a, "rev-list", "--merges", "--count", "HEAD") == "0"
    assert len(parse(a / RECORD)[0]["readers"]) == 2
    news = commits_since_last(a, "Fan")
    assert [(c.type_tag, c.person, c.agent) for c in news] == [
        ("log", "Lee", "codex"), ("literature", "Lee", "codex"),
    ]
    digest = render(news)
    assert f"re-read {CITEKEY} — verified 2, disputed 0, added 0 claims — Lee/codex" in digest
    assert "session Lee/codex 2026-10-27 09:10–10:00 — Lee/codex" in digest
    assert ITEM in _section(a / news[0].links[0], "Done")
    assert run_checks(a) == [] and run_checks(b) == []
    assert stats(a)["unverified_claims"] == 0
