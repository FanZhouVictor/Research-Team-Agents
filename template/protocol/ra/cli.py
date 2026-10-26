"""The command line of the ra package: argument parsing, dispatch and the commands.

protocol/ra.py is only the entry script; it calls main() here. Later commands are
registered inside add_commands(), with handlers decorated by @_guarded.
"""

import argparse
import functools
import sys
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from ra import check, dedup, newfile

__all__ = ["add_commands", "build_parser", "main"]

Handler = Callable[[argparse.Namespace], int]


def _guarded(handler: Handler) -> Handler:
    """Decorate a command handler so that expected failures are reported, not raised.

    ValueError (bad input or bad file content), FileExistsError and FileNotFoundError print
    'error: <message>' on stderr and give exit code 1. Any other exception still raises.
    Put it on every handler that calls into the ra package.
    """

    @functools.wraps(handler)
    def run(args: argparse.Namespace) -> int:
        try:
            return handler(args)
        except (ValueError, FileExistsError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    return run


def _day(text: str) -> date:
    """argparse type: a date written YYYY-MM-DD."""
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not a date as YYYY-MM-DD: {text!r}") from exc


def _minute(text: str) -> datetime:
    """argparse type: a time written YYYY-MM-DDTHH:MM."""
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not a time as YYYY-MM-DDTHH:MM: {text!r}") from exc


def _names(text: str) -> list[str]:
    """argparse type: 'Smith J; Lee K' becomes ['Smith J', 'Lee K'] (split on ';', stripped)."""
    return [name.strip() for name in text.split(";") if name.strip()]


def _print_created(root: Path, path: Path) -> int:
    """Print path relative to root with '/' separators, the form skills and commits cite."""
    print(path.relative_to(root).as_posix())
    return 0


@_guarded
def _new_question(args: argparse.Namespace) -> int:
    root = Path.cwd()
    day = args.date or date.today()
    path = newfile.new_question(root, args.slug, args.title, args.person, args.agent, day)
    return _print_created(root, path)


@_guarded
def _new_decision(args: argparse.Namespace) -> int:
    root = Path.cwd()
    day = args.date or date.today()
    links = args.link or []
    path = newfile.new_decision(root, args.slug, args.title, args.person, args.agent, day, links)
    return _print_created(root, path)


@_guarded
def _new_literature(args: argparse.Namespace) -> int:
    root = Path.cwd()
    meta = {
        "person": args.person,
        "agent": args.agent,
        "date": (args.date or date.today()).isoformat(),
        "title": args.title,
        "year": args.year,
        "authors": args.authors,
        "venue": args.venue,
        "doi": args.doi,
        "arxiv": args.arxiv,
        "relevance": args.relevance,
        "bears-on": args.bears_on,
    }
    path = newfile.new_literature(root, args.citekey, meta, Path(args.pdf))
    return _print_created(root, path)


@_guarded
def _new_log(args: argparse.Namespace) -> int:
    root = Path.cwd()
    start = args.start or datetime.now().replace(second=0, microsecond=0)
    path = newfile.new_log(root, args.person, args.agent, start)
    return _print_created(root, path)


@_guarded
def _new_topic(args: argparse.Namespace) -> int:
    root = Path.cwd()
    path = newfile.new_topic(root, args.topic, args.scope)
    return _print_created(root, path)


@_guarded
def _check(args: argparse.Namespace) -> int:
    findings = check.run_checks(Path.cwd())
    for finding in findings:
        print(f"{finding.code} {finding.path.as_posix()}: {finding.message}")
    if findings:
        return 1
    print("check: no findings")
    return 0


@_guarded
def _dedup(args: argparse.Namespace) -> int:
    if args.doi is None and args.arxiv is None and args.title is None:
        args.parser.error("give at least one of --doi, --arxiv or --title")
    root = Path.cwd()
    found = dedup.find_existing(root, args.doi, args.arxiv, args.title)
    print("none" if found is None else found.relative_to(root).as_posix())
    return 0


def _add_who(parser: argparse.ArgumentParser) -> None:
    """Add the --person and --agent flags that every file with an author takes."""
    parser.add_argument("--person", required=True, help="who, as in the git log, e.g. Fan")
    parser.add_argument("--agent", required=True, help="which tool: claude-code or codex")


def _add_date(parser: argparse.ArgumentParser) -> None:
    """Add the optional --date flag."""
    parser.add_argument("--date", type=_day, help="YYYY-MM-DD (default: today)")


def _add_new(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register 'new <kind>': create one file from its template and print its path."""
    new = subparsers.add_parser(
        "new",
        help="create a question, decision, literature record, log entry or topic",
        description="Create a file in the current directory (the project root) and print its path.",
    )
    kinds = new.add_subparsers(dest="kind", metavar="<kind>", required=True)

    question = kinds.add_parser("question", help="questions/Q-<date>-<slug>.md")
    question.add_argument("--slug", required=True, help="short name, [a-z0-9-]+")
    question.add_argument("--title", required=True, help="the question")
    _add_who(question)
    _add_date(question)
    question.set_defaults(func=_new_question)

    decision = kinds.add_parser("decision", help="decisions/D-<date>-<slug>.md")
    decision.add_argument("--slug", required=True, help="short name, [a-z0-9-]+")
    decision.add_argument("--title", required=True, help="the decision in one line")
    _add_who(decision)
    _add_date(decision)
    decision.add_argument(
        "--link", action="extend", nargs="+", metavar="L",
        help="question id or repo path the decision rests on (repeatable)",
    )
    decision.set_defaults(func=_new_decision)

    literature = kinds.add_parser(
        "literature", help="literature/<citekey>.md, and the PDF copied to literature/pdf/"
    )
    literature.add_argument(
        "--citekey", required=True, help="[a-z0-9-]+, e.g. smith2024-plume-goes"
    )
    literature.add_argument("--pdf", required=True, metavar="PATH", help="the paper's PDF to copy")
    _add_who(literature)
    _add_date(literature)
    literature.add_argument("--title")
    literature.add_argument("--year", type=int)
    literature.add_argument(
        "--authors", type=_names, help='separated by ";", e.g. "Smith J; Lee K"'
    )
    literature.add_argument("--venue")
    literature.add_argument("--doi")
    literature.add_argument("--arxiv")
    literature.add_argument("--relevance", choices=newfile.RELEVANCE)
    literature.add_argument(
        "--bears-on", action="extend", nargs="+", metavar="Q",
        help="ids of the questions the paper bears on (repeatable)",
    )
    literature.set_defaults(func=_new_literature)

    log = kinds.add_parser("log", help="log/<date>-<person>-<agent>-<hhmm>.md")
    _add_who(log)
    log.add_argument(
        "--start", type=_minute, metavar="YYYY-MM-DDTHH:MM", help="session start (default: now)"
    )
    log.set_defaults(func=_new_log)

    topic = kinds.add_parser(
        "topic", help="knowledge/<topic>.md, registered in knowledge/README.md"
    )
    topic.add_argument("--topic", required=True, help="[a-z0-9-]+")
    topic.add_argument("--scope", required=True, help="one line: what the topic covers")
    topic.set_defaults(func=_new_topic)


def _add_dedup(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register 'dedup': find the literature record that already exists for a paper."""
    command = subparsers.add_parser(
        "dedup",
        help="find the literature record that already exists for a paper",
        description=(
            "Look in literature/ of the project in the current directory for the paper given "
            "by the options: first by DOI, then by arXiv id, then by title (case, spacing and "
            "punctuation do not matter). Prints the path of the matching record, or 'none'; "
            "the exit code is 0 either way. Give at least one option."
        ),
    )
    command.add_argument("--doi", help="DOI, bare or as doi:<DOI> or https://doi.org/<DOI>")
    command.add_argument("--arxiv", help="arXiv id, e.g. 2401.10250 (arxiv: and vN are optional)")
    command.add_argument("--title", help="the paper's title")
    command.set_defaults(func=_dedup, parser=command)


def add_commands(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register every command on subparsers; later commands are added here.

    Each command is one subparser whose handler is attached with set_defaults:

        command = subparsers.add_parser("name", help="...")
        command.set_defaults(func=handler)

    where handler(args: argparse.Namespace) -> int returns the process exit code. Decorate
    the handler with @_guarded to turn ValueError, FileExistsError and FileNotFoundError
    into an 'error: ...' line and exit code 1.
    """
    _add_new(subparsers)
    command = subparsers.add_parser(
        "check",
        help="validate the repository; run it before every commit",
        description=(
            "Check the project in the current directory: file names, frontmatter, claims, "
            "PDFs, duplicate papers, knowledge facts and accepted decisions. Prints one "
            "'CODE path: message' line per finding and exits 1 if there is any."
        ),
    )
    command.set_defaults(func=_check)
    _add_dedup(subparsers)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with one subparser per command."""
    parser = argparse.ArgumentParser(
        prog="ra.py",
        description="Deterministic helpers for the shared-repo protocol (see PROTOCOL.md).",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    add_commands(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command line and return the process exit code.

    Args:
        argv: Arguments after the program name; defaults to sys.argv[1:].

    Returns:
        The chosen command's exit code, or 2 when no command is given. Invalid
        arguments make argparse exit with status 2 on its own.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    handler: Handler | None = getattr(args, "func", None)
    if handler is None:
        parser.print_usage(sys.stderr)
        return 2
    return handler(args)
