"""'ra init': create a project repository from the template."""

import argparse
from pathlib import Path

from ra import scaffold
from ra.cli_common import guarded
from ra.newfile import AGENTS

__all__ = ["add"]


@guarded
def _init(args: argparse.Namespace) -> int:
    dest = Path(args.dest)
    scaffold.init_project(dest, args.name, args.person, args.git_author, args.platforms, args.role)
    print(dest.resolve())
    return 0


def add(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register 'init': create a project repository from the template."""
    command = subparsers.add_parser(
        "init",
        help="create a new project repository from the template",
        description=(
            "Copy the template to DEST (a directory that does not exist yet or is empty; a "
            "relative DEST is read from the current directory), fill PROJECT.md with the "
            "project name and the first member, run git init and make the first commit as that "
            "member. Prints the path of the new project. Run it from the framework repository, "
            "not inside a project. Write DEST before --platforms, which takes several values."
        ),
    )
    command.add_argument("dest", metavar="DEST", help="directory of the new project")
    command.add_argument("--name", required=True, help="project name, the title of PROJECT.md")
    command.add_argument("--person", required=True, help="the first member, e.g. Fan")
    command.add_argument(
        "--git-author", required=True, metavar="GIT_AUTHOR",
        help="the member's git identity as 'Name <email>', e.g. 'Fan <fan@x>'",
    )
    command.add_argument(
        "--platforms", required=True, nargs="+", choices=AGENTS, metavar="PLATFORM",
        help=f"the member's AI tools, one or more of: {', '.join(AGENTS)}",
    )
    command.add_argument("--role", required=True, help="the member's role, e.g. PI")
    command.set_defaults(func=_init)
