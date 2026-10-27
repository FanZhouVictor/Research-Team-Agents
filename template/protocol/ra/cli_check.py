"""'ra check': validate the project in the current directory."""

import argparse

from ra import check
from ra.cli_common import guarded, project_root

__all__ = ["add"]


@guarded
def _check(args: argparse.Namespace) -> int:
    findings = check.run_checks(project_root())
    for finding in findings:
        print(f"{finding.code} {finding.path.as_posix()}: {finding.message}")
    if findings:
        return 1
    print("check: no findings")
    return 0


def add(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register 'check': validate the repository."""
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
