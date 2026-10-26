"""Read the repository's git log as a what's-new digest (spec §9).

commits_since_last(repo, person) lists what was committed since a person's own last commit,
and render(commits) turns the list into a short text grouped by commit type. Messages are read
with parse_message, which takes any text: a commit whose subject does not start with a known
'[<tag>] ' (a human's hand-written message, a merge) is kept as an untagged commit and shown
under 'other'. No message in the log makes the digest raise.
"""

import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

from ra.commit import TYPE_TAGS

__all__ = ["Commit", "commits_since_last", "parse_message", "render"]

_OTHER = "other"  # the heading of the commits without a type tag
_FIELD = "\x1f"  # separates the fields of one commit in the git log output
_RECORD = "\x1e"  # ends each commit in the git log output
_TRAILERS = ("Person", "Agent", "Links")


@dataclass(frozen=True)
class Commit:
    """One commit as the digest shows it.

    type_tag is None when the subject has no known '[<tag>] ' prefix; subject is then the whole
    first line. person and agent are None when their trailer is missing or empty. date is the
    author date as YYYY-MM-DD.
    """

    sha: str
    date: str
    type_tag: str | None
    subject: str
    person: str | None
    agent: str | None
    links: list[str]


def _split_subject(line: str) -> tuple[str | None, str]:
    """('<tag>', '<rest>') for '[<tag>] <rest>' with a known tag; otherwise (None, line)."""
    for tag in TYPE_TAGS:
        prefix = f"[{tag}] "
        if line.startswith(prefix):
            return tag, line[len(prefix):].strip()
    return None, line


def _trailers(lines: list[str]) -> dict[str, str]:
    """The stripped value of the first Person, Agent and Links line in lines, as far as present."""
    found: dict[str, str] = {}
    for line in lines:
        key, colon, value = line.partition(":")
        if colon and key in _TRAILERS and key not in found:
            found[key] = value.strip()
    return found


def parse_message(msg: str) -> Commit:
    """Parse a commit message into a Commit whose sha and date are '' (the caller fills them).

    The first non-blank line is the subject line. If it starts with '[<tag>] ' for a tag in
    TYPE_TAGS, type_tag is the tag and subject the rest; otherwise type_tag is None and subject
    the whole line ('[experiment] x' is untagged). The lines after it are searched for 'Person:',
    'Agent:' and 'Links:' (the first of each counts); Links is split on commas, and a missing or
    empty Links line gives []. A message with no text gives an untagged commit with subject ''.
    """
    lines = msg.split("\n")  # a CR left at a line end is removed by the strip() calls below
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first is None:
        return Commit("", "", None, "", None, None, [])
    type_tag, subject = _split_subject(lines[first].strip())
    trailers = _trailers(lines[first + 1:])
    links = [item.strip() for item in trailers.get("Links", "").split(",") if item.strip()]
    return Commit(
        sha="",
        date="",
        type_tag=type_tag,
        subject=subject,
        person=trailers.get("Person") or None,
        agent=trailers.get("Agent") or None,
        links=links,
    )


def _git(repo: Path, *args: str) -> str:
    """Run git with args in repo and return its stdout as text; CalledProcessError propagates.

    Output is read as UTF-8 with bad bytes replaced.
    """
    done = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        check=True, capture_output=True, cwd=repo,
    )
    return done.stdout.decode("utf-8", errors="replace")


def _has_commits(repo: Path) -> bool:
    """False in a repository that has no commit yet; any other git failure propagates."""
    try:
        _git(repo, "rev-parse", "--verify", "--quiet", "HEAD")
    except subprocess.CalledProcessError as exc:
        if exc.returncode == 1:  # --quiet: exit status 1, no message, when HEAD names nothing
            return False
        raise
    return True


def commits_since_last(repo: Path, person: str, fallback: int = 20) -> list[Commit]:
    """The commits made since person's own last commit, newest first, as git returns them.

    The boundary is the newest commit whose author matches person, found with
    'git log --author=<person>'. git reads that value as a regular expression against
    'Name <email>': 'Fan' also matches 'Stefan <s@x>', and a character such as '(' has its
    regex meaning (an invalid expression makes git fail). Pass the name as in 'user.name'.
    That commit itself is left out. A person with no commit gets the last `fallback` commits.

    Args:
        repo: Root of the git work tree.
        person: The name to look for; must not be blank (an empty pattern matches every commit).
        fallback: How many of the newest commits to list for a person without commits.

    Returns:
        The commits, with sha, author date and the parsed message; [] when there is nothing
        new or the repository has no commit yet.

    Raises:
        ValueError: If person is blank.
        subprocess.CalledProcessError: If git fails for another reason, for example repo is not
            a git repository.
    """
    if not person.strip():
        raise ValueError("person must not be empty")
    if not _has_commits(repo):
        return []
    last = _git(repo, "log", f"--author={person}", "-n", "1", "--format=%H").strip()
    selection = [f"{last}..HEAD"] if last else ["-n", str(fallback)]
    log = _git(repo, "log", *selection, "--format=%H%x1f%ad%x1f%B%x1e", "--date=short")
    commits = []
    for record in log.split(_RECORD):
        fields = record.split(_FIELD, 2)
        if len(fields) == 3:  # the text after the last record, or a stray separator, has fewer
            sha, day, message = fields
            commits.append(replace(parse_message(message), sha=sha.strip(), date=day.strip()))
    return commits


def _line(commit: Commit) -> str:
    """The digest line of one commit."""
    who = f"{commit.person or '?'}/{commit.agent or '?'}"
    return f"- {commit.date} {commit.sha[:7]} {commit.subject} — {who}"


def render(commits: list[Commit]) -> str:
    """Render commits as a short digest, grouped by type tag.

    The groups come in TYPE_TAGS order, then 'other' for the untagged (and for a tag that is
    not in TYPE_TAGS); empty groups are left out. A group is the heading '## <tag> (<count>)'
    and one line per commit, in the order given:

        - <date> <sha[:7]> <subject> — <person>/<agent>

    with '?' for a missing person or agent. A blank line separates the groups and the text ends
    with one newline. An empty list gives 'No new commits.'.
    """
    if not commits:
        return "No new commits.\n"
    groups: dict[str, list[Commit]] = {tag: [] for tag in (*TYPE_TAGS, _OTHER)}
    for commit in commits:
        groups[commit.type_tag if commit.type_tag in TYPE_TAGS else _OTHER].append(commit)
    blocks = [
        "\n".join([f"## {tag} ({len(members)})", *(_line(c) for c in members)]) + "\n"
        for tag, members in groups.items()
        if members
    ]
    return "\n".join(blocks)
