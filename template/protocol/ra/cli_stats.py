"""'ra stats': print the pilot metrics of the project in the current directory."""

import argparse
from pathlib import Path

from ra import stats
from ra.cli_common import guarded

__all__ = ["add"]


@guarded
def _stats(args: argparse.Namespace) -> int:
    for key, value in stats.stats(Path.cwd()).items():
        print(f"{key}: {value}")
    return 0


def add(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register 'stats': count what the pilot measures."""
    command = subparsers.add_parser(
        "stats",
        help="count papers, claims and open items: the pilot metrics",
        description=(
            "Print the pilot metrics of the project in the current directory, one 'key: value' "
            "line per count: papers, claims, unverified_claims (no verified-by from a person "
            "other than the claim's author), disputed_claims, duplicate_records, "
            "decisions_edited, open_questions and conflict_facts (fact lines in CONFLICT). "
            "Never opens a PDF. Exits 0."
        ),
    )
    command.set_defaults(func=_stats)
