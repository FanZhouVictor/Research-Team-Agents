"""Command-line entry point: python protocol/ra.py <command>.

This file only parses arguments and dispatches to the ra package that sits next to
it. Inside this script, 'import ra' finds that package: a package directory wins over
a same-named .py file in the same directory, and the script itself runs as __main__.
"""

import argparse
import sys
from collections.abc import Callable


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser; each command is one subparser."""
    parser = argparse.ArgumentParser(
        prog="ra.py",
        description="Deterministic helpers for the shared-repo protocol (see PROTOCOL.md).",
    )
    # Commands are added to this subparsers object, each with
    #   subparser.set_defaults(func=handler)
    # where handler(args: argparse.Namespace) -> int returns the process exit code.
    parser.add_subparsers(dest="command", metavar="<command>")
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
    handler: Callable[[argparse.Namespace], int] | None = getattr(args, "func", None)
    if handler is None:
        parser.print_usage(sys.stderr)
        return 2
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
