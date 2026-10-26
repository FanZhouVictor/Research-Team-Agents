"""Write to the shared repository: the commit message of spec §9 and the commit that carries it.

Every protocol write by an AI is one commit, and its message has this form:

    [<type>] <subject>

    Person: <name>
    Agent: <claude-code|codex>
    Links: <comma-separated paths>

format_message builds that text and commit() stages the files of the write and commits them
with it. The three trailer lines are always there: with no links the last line is 'Links:' with
nothing after the colon. The message carries nothing else (no Co-Authored-By). ra.digest reads
these messages back.
"""

import os
import subprocess
from pathlib import Path

from ra.newfile import AGENTS

__all__ = ["AGENTS", "TYPE_TAGS", "commit", "format_message"]

TYPE_TAGS: tuple[str, ...] = (
    "literature", "question", "knowledge", "decision", "log", "status", "protocol",
)


def _one_line(value: object, label: str) -> str:
    """value without surrounding whitespace; ValueError unless it is a non-blank one-line string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must not be empty")
    if "\n" in value or "\r" in value:
        raise ValueError(f"{label} must be one line, got {value!r}")
    return value.strip()


def _link(value: object) -> str:
    """One entry of Links: a one-line path without a comma (a comma would read back as two)."""
    link = _one_line(value, "link")
    if "," in link:
        raise ValueError(f"link must not contain a comma, got {link!r}")
    return link


def format_message(
    type_tag: str, subject: str, person: str, agent: str, links: list[str]
) -> str:
    """Return the commit message of spec §9 for one write.

    Args:
        type_tag: One of TYPE_TAGS.
        subject: What was written, on one line.
        person: Who made the write, as in the git log.
        agent: One of AGENTS.
        links: Repo paths the commit adds, changes or cites; may be empty.

    Returns:
        '[<type_tag>] <subject>', a blank line, then the Person, Agent and Links lines, each
        ending in a newline. Subject, person and links are stripped of surrounding whitespace,
        which git would remove from the end of a line anyway. With no links the last line is
        'Links:' alone.

    Raises:
        ValueError: If type_tag is not in TYPE_TAGS, agent is not in AGENTS, or subject, person
            or a link is blank or has a line break, or a link has a comma.
    """
    if type_tag not in TYPE_TAGS:
        raise ValueError(f"type must be one of {', '.join(TYPE_TAGS)}, got {type_tag!r}")
    if agent not in AGENTS:
        raise ValueError(f"agent must be one of {', '.join(AGENTS)}, got {agent!r}")
    subject = _one_line(subject, "subject")
    person = _one_line(person, "person")
    paths = [_link(link) for link in links]
    trailer = f"Links: {', '.join(paths)}" if paths else "Links:"
    return f"[{type_tag}] {subject}\n\nPerson: {person}\nAgent: {agent}\n{trailer}\n"


def _relative(repo: Path, path: Path) -> str:
    """path as a POSIX path relative to repo; ValueError if it is not inside repo.

    A relative path is read relative to repo, never to the current directory, and '..' parts
    are resolved by name. An absolute path that spells repo another way (through a symlink such
    as macOS /var) is compared again after symlinks are resolved.
    """
    root = Path(os.path.abspath(repo))
    target = Path(os.path.abspath(root / path))  # root / <an absolute path> is that path
    try:
        return target.relative_to(root).as_posix()
    except ValueError:
        pass
    try:
        return Path(os.path.realpath(target)).relative_to(os.path.realpath(root)).as_posix()
    except ValueError:
        raise ValueError(f"{path} is not inside the repository {repo}") from None


def _git(repo: Path, *args: str, stdin: bytes | None = None) -> str:
    """Run git with args in repo and return its stdout as text; CalledProcessError propagates.

    Output is read as UTF-8 (bad bytes replaced). stdin goes in as bytes: text mode would turn
    '\\n' into '\\r\\n' on Windows.
    """
    done = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        check=True, capture_output=True, cwd=repo, input=stdin,
    )
    return done.stdout.decode("utf-8", errors="replace")


def commit(
    repo: Path,
    paths: list[Path],
    type_tag: str,
    subject: str,
    person: str,
    agent: str,
    links: list[str],
) -> str:
    """Stage paths and commit them with the message of format_message; return the new sha.

    One call is one logical write. Every argument is checked before git runs, so a rejected
    call stages nothing. Whatever else is already staged is committed too, and no empty
    commit is made.

    Args:
        repo: Root of the git work tree.
        paths: Files to stage, absolute or relative to repo; each must be inside repo. An empty
            list stages nothing and commits what is already staged.
        type_tag: As in format_message.
        subject: As in format_message.
        person: As in format_message.
        agent: As in format_message.
        links: As in format_message.

    Returns:
        The sha of the new commit, from 'git rev-parse HEAD'.

    Raises:
        ValueError: A bad argument of format_message, or a path outside repo.
        subprocess.CalledProcessError: A git command failed, for example 'git commit' with
            nothing staged.
    """
    message = format_message(type_tag, subject, person, agent, links).encode("utf-8")
    relative = [_relative(repo, path) for path in paths]
    if relative:
        _git(repo, "add", "--", *relative)
    _git(repo, "commit", "-F", "-", stdin=message)
    return _git(repo, "rev-parse", "HEAD").strip()
