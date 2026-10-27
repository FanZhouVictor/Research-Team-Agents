"""'ra new <kind>': create a question, decision, literature record, log entry or topic."""

import argparse
from datetime import date, datetime
from pathlib import Path

from ra import newfile
from ra.cli_common import (
    add_date,
    add_who,
    guarded,
    minute,
    names,
    print_created,
    project_root,
)

__all__ = ["add"]


@guarded
def _new_question(args: argparse.Namespace) -> int:
    root = project_root()
    day = args.date or date.today()
    path = newfile.new_question(root, args.slug, args.title, args.person, args.agent, day)
    return print_created(root, path)


@guarded
def _new_decision(args: argparse.Namespace) -> int:
    root = project_root()
    day = args.date or date.today()
    links = args.link or []
    path = newfile.new_decision(root, args.slug, args.title, args.person, args.agent, day, links)
    return print_created(root, path)


@guarded
def _new_literature(args: argparse.Namespace) -> int:
    root = project_root()
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
    return print_created(root, path)


@guarded
def _new_log(args: argparse.Namespace) -> int:
    root = project_root()
    start = args.start or datetime.now().replace(second=0, microsecond=0)
    path = newfile.new_log(root, args.person, args.agent, start)
    return print_created(root, path)


@guarded
def _new_topic(args: argparse.Namespace) -> int:
    root = project_root()
    path = newfile.new_topic(root, args.topic, args.scope)
    return print_created(root, path)


def add(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
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
    add_who(question)
    add_date(question)
    question.set_defaults(func=_new_question)

    decision = kinds.add_parser("decision", help="decisions/D-<date>-<slug>.md")
    decision.add_argument("--slug", required=True, help="short name, [a-z0-9-]+")
    decision.add_argument("--title", required=True, help="the decision in one line")
    add_who(decision)
    add_date(decision)
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
    add_who(literature)
    add_date(literature)
    literature.add_argument("--title")
    literature.add_argument("--year", type=int)
    literature.add_argument(
        "--authors", type=names, help='separated by ";", e.g. "Smith J; Lee K"'
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
    add_who(log)
    log.add_argument(
        "--start", type=minute, metavar="YYYY-MM-DDTHH:MM", help="session start (default: now)"
    )
    log.set_defaults(func=_new_log)

    topic = kinds.add_parser(
        "topic", help="knowledge/<topic>.md, registered in knowledge/README.md"
    )
    topic.add_argument("--topic", required=True, help="[a-z0-9-]+")
    topic.add_argument("--scope", required=True, help="one line: what the topic covers")
    topic.set_defaults(func=_new_topic)
