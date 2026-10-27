"""Pieces the command modules share: the error guard for handlers, the project-root check and
the argparse helpers.

Each cli_<command>.py module registers its command through add(subparsers) and imports what
it needs from here; this module imports none of them, and nothing from ra.cli.
"""

import argparse
import functools
import subprocess
import sys
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

__all__ = [
    "Handler",
    "add_date",
    "add_who",
    "day",
    "flat",
    "git_failure",
    "guarded",
    "minute",
    "names",
    "print_created",
    "project_root",
]

Handler = Callable[[argparse.Namespace], int]

# What every project root holds: PROJECT.md first, as the error message names the first missing.
_ROOT_FILES = ("PROJECT.md", "protocol/ra.py")


def flat(data: str | bytes | None) -> str:
    """Command output as one line.

    Bytes are read as UTF-8 (bad bytes replaced); each run of whitespace, line breaks
    included, becomes one space.
    """
    text =data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data or ""
    return " ".join(text.split())


def git_failure(exc: subprocess.CalledProcessError) -> str:
    """'git <args> failed: <what git said>', in one line, for a failed git command.

    git's own words are on stderr. 'git commit' with nothing to commit explains itself on
    stdout and leaves stderr empty, so stdout is used then; a command that said nothing gives
    its exit status. 'git' and global '-c name=value' settings are left out of <args>.
    """
    args = [str(part) for part in exc.cmd[1:]]
    while len(args) >= 2 and args[0] == "-c":
        del args[:2]
    said = flat(exc.stderr) or flat(exc.stdout) or f"exit status {exc.returncode}"
    return f"git {' '.join(args)} failed: {said}"


def guarded(handler: Handler) -> Handler:
    """Decorate a command handler so that expected failures are reported, not raised.

    ValueError (bad input or bad file content), FileExistsError and FileNotFoundError print
    'error: <message>' on stderr and give exit code 1. So does subprocess.CalledProcessError,
    which the library functions that run git let through: it prints
    'error: git <args> failed: <what git said>'. Any other exception still raises.
    Put it on every handler that calls into the ra package.
    """

    @functools.wraps(handler)
    def run(args: argparse.Namespace) -> int:
        try:
            return handler(args)
        except (ValueError, FileExistsError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        except subprocess.CalledProcessError as exc:
            print(f"error: {git_failure(exc)}", file=sys.stderr)
            return 1

    return run


def project_root() -> Path:
    """The current directory, once it is known to be a project root.

    A project root holds PROJECT.md and protocol/ra.py (PROTOCOL.md §2 "The helper"). Every
    command but init calls this first: run from anywhere else, check would find no files and
    print 'check: no findings', dedup 'none' and stats zeros, all false.

    Raises:
        ValueError: 'not a project root (no PROJECT.md in <cwd>)', naming protocol/ra.py
            instead when only that is missing; guarded turns it into an 'error:' line.
    """
    root = Path.cwd()
    for name in _ROOT_FILES:
        if not (root / name).is_file():
            raise ValueError(f"not a project root (no {name} in {root})")
    return root


def day(text: str) -> date:
    """argparse type: a date written YYYY-MM-DD."""
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not a date as YYYY-MM-DD: {text!r}") from exc


def minute(text: str) -> datetime:
    """argparse type: a time written YYYY-MM-DDTHH:MM."""
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not a time as YYYY-MM-DDTHH:MM: {text!r}") from exc


def names(text: str) -> list[str]:
    """argparse type: 'Smith J; Lee K' becomes ['Smith J', 'Lee K'] (split on ';', stripped)."""
    return [name.strip() for name in text.split(";") if name.strip()]


def print_created(root: Path, path: Path) -> int:
    """Print path relative to root with '/' separators, the form skills and commits cite."""
    print(path.relative_to(root).as_posix())
    return 0


def add_who(parser: argparse.ArgumentParser) -> None:
    """Add the --person and --agent flags that every file with an author takes."""
    parser.add_argument("--person", required=True, help="who, as in the git log, e.g. Fan")
    parser.add_argument("--agent", required=True, help="which tool: claude-code or codex")


def add_date(parser: argparse.ArgumentParser) -> None:
    """Add the optional --date flag."""
    parser.add_argument("--date", type=day, help="YYYY-MM-DD (default: today)")
