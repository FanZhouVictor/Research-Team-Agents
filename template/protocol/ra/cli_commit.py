"""'ra commit' and 'ra digest': write the protocol's structured commit, read it back."""

import argparse
from pathlib import Path

from ra import commit, digest
from ra.cli_common import add_who, guarded, project_root

__all__ = ["add"]


@guarded
def _commit(args: argparse.Namespace) -> int:
    root = project_root()
    paths = [Path(path) for path in args.paths]
    links = args.links or []
    sha = commit.commit(root, paths, args.type, args.subject, args.person, args.agent, links)
    print(sha)
    return 0


@guarded
def _digest(args: argparse.Namespace) -> int:
    commits = digest.commits_since_last(project_root(), args.person, args.fallback)
    print(digest.render(commits), end="")
    return 0


def _add_commit(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register 'commit': one structured commit for one logical write."""
    command = subparsers.add_parser(
        "commit",
        help="commit one logical write with the protocol's structured message",
        description=(
            "Stage the given paths (relative to the current directory, the project root) and "
            "commit them with the message '[<type>] <subject>' followed by the Person, Agent "
            "and Links lines; print the new commit's sha. Without paths it commits what is "
            "already staged. Write -- before the paths when --links comes before them."
        ),
    )
    command.add_argument(
        "--type", required=True, choices=commit.TYPE_TAGS, metavar="TAG",
        help=f"commit type, one of: {', '.join(commit.TYPE_TAGS)}",
    )
    command.add_argument("--subject", required=True, help="what was written, on one line")
    add_who(command)
    command.add_argument(
        "--links", action="extend", nargs="*", metavar="L",
        help="repo paths the commit adds, changes or cites (repeatable)",
    )
    command.add_argument("paths", nargs="*", metavar="PATH", help="files to stage and commit")
    command.set_defaults(func=_commit)


def _add_digest(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register 'digest': what is new in the git log for one person."""
    command = subparsers.add_parser(
        "digest",
        help="list the commits made since this person's last commit",
        description=(
            "Print the commits made since the last commit of --person, grouped by type tag "
            "(commits without a tag under 'other'). Merge commits are never listed and never "
            "count as a person's last commit. The person is matched by git's --author as a "
            "fixed string, not a regular expression, anywhere in 'Name <email>': give the "
            "whole 'Name <email>'. A person without commits gets the last --fallback commits."
        ),
    )
    command.add_argument(
        "--person", required=True, help="the git author name, e.g. 'Fan <fan@x>'"
    )
    command.add_argument(
        "--fallback", type=int, default=20, metavar="N",
        help="how many commits to list for a person without commits (default: 20)",
    )
    command.set_defaults(func=_digest)


def add(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register 'commit' and 'digest'."""
    _add_commit(subparsers)
    _add_digest(subparsers)
