"""'ra dedup': find the literature record that already exists for a paper."""

import argparse

from ra import dedup
from ra.cli_common import guarded, project_root

__all__ = ["add"]


@guarded
def _dedup(args: argparse.Namespace) -> int:
    if args.doi is None and args.arxiv is None and args.title is None:
        args.parser.error("give at least one of --doi, --arxiv or --title")
    root = project_root()
    found = dedup.find_existing(root, args.doi, args.arxiv, args.title)
    print("none" if found is None else found.relative_to(root).as_posix())
    return 0


def add(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
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
