"""The command line of the ra package: the parser and the dispatch.

protocol/ra.py is only the entry script; it calls main() here. Each command lives in its own
cli_<command>.py module, with the pieces they share in cli_common.py, and add_commands()
registers them.
"""

import argparse
import sys

from ra import cli_check, cli_commit, cli_dedup, cli_init, cli_new, cli_stats, cli_sync
from ra.cli_common import Handler

__all__ = ["add_commands", "build_parser", "main"]


def add_commands(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register every command on subparsers; later commands are added here.

    A command is a module cli_<name>.py with a function add(subparsers) that adds its
    subparser(s), and one call of it here. The handler of a command is attached with
    set_defaults:

        command = subparsers.add_parser("name", help="...")
        command.set_defaults(func=handler)

    where handler(args: argparse.Namespace) -> int returns the process exit code. Decorate
    the handler with @guarded (from ra.cli_common) to turn ValueError, an OSError
    (FileExistsError, FileNotFoundError, a permission error, ...) and a failed git command
    (subprocess.CalledProcessError) into an 'error: ...' line and exit code 1. A handler that
    works in the project takes its root from project_root() (from ra.cli_common), which
    refuses any other directory; only init does not.
    """
    cli_init.add(subparsers)
    cli_new.add(subparsers)
    cli_check.add(subparsers)
    cli_dedup.add(subparsers)
    cli_commit.add(subparsers)
    cli_sync.add(subparsers)
    cli_stats.add(subparsers)


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
