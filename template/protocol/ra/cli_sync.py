"""'ra sync': pull, push and look for merge conflicts in the project repository (spec §12)."""

import argparse
import contextlib
import subprocess
from pathlib import Path

from ra import sync
from ra.cli_common import guarded, project_root

__all__ = ["add"]

_STOP = 2  # exit code of 'sync conflicts' when a merge left conflicts: the caller stops there


def _print_unmerged(root: Path) -> bool:
    """Print one line per unmerged path, 'protected <path>' lines first, then 'other <path>'.

    Returns True if there was any path.
    """
    unmerged = sync.unmerged_paths(root)
    protected = set(sync.protected_conflicts(root))
    for path in unmerged:
        if path in protected:
            print(f"protected {path.as_posix()}")
    for path in unmerged:
        if path not in protected:
            print(f"other {path.as_posix()}")
    return bool(unmerged)


@guarded
def _conflicts(args: argparse.Namespace) -> int:
    if _print_unmerged(project_root()):
        return _STOP
    print("sync: no conflicts")
    return 0


@guarded
def _pull_and_merge(args: argparse.Namespace) -> int:
    sync.pull(project_root())
    return 0


def _pull(args: argparse.Namespace) -> int:
    code = _pull_and_merge(args)  # a failure is reported by guarded as one 'error: ...' line
    if code != 0:
        # What git left unmerged comes after the error line, so a conflict is seen at once. The
        # failure is already reported: if even this listing fails, there is nothing to add, and
        # outside a project root (a ValueError) there is no merge to list.
        with contextlib.suppress(subprocess.CalledProcessError, OSError, ValueError):
            _print_unmerged(project_root())
    return code


@guarded
def _push(args: argparse.Namespace) -> int:
    sync.push(project_root())
    return 0


def add(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register 'sync pull', 'sync push' and 'sync conflicts'."""
    command = subparsers.add_parser(
        "sync",
        help="pull, push and look for merge conflicts in the project repository",
        description=(
            "Keep the project in the current directory (the project root) in step with its "
            "remote: pull before a write, push after a batch of writes, and look for "
            "conflicts after a pull."
        ),
    )
    actions = command.add_subparsers(dest="action", metavar="<action>", required=True)

    pull = actions.add_parser(
        "pull",
        help="git pull as a merge (no rebase, no editor)",
        description=(
            "Run 'git pull --rebase=false --ff --no-edit'. It prints nothing and exits 0 when it "
            "succeeds. When git fails it prints one 'error: ...' line on stderr and exits 1; "
            "paths that git left unmerged follow on stdout, as 'sync conflicts' prints them. A "
            "merge conflict is left in place: do not resolve it, tell the user."
        ),
    )
    pull.set_defaults(func=_pull)

    push = actions.add_parser(
        "push",
        help="git push of the current branch",
        description=(
            "Run 'git push'. It prints nothing and exits 0 when it succeeds. When git refuses, "
            "for example because the remote has commits that are not pulled yet, it prints one "
            "'error: ...' line on stderr and exits 1."
        ),
    )
    push.set_defaults(func=_push)

    conflicts = actions.add_parser(
        "conflicts",
        help="list the paths a merge left conflicted; exit code 2 means stop",
        description=(
            "List the paths a merge left unmerged, one per line: 'protected <path>' for those "
            "under knowledge/ or decisions/ first, then 'other <path>' for the rest. The exit "
            "code is 2 if there is any: stop, leave the conflict in place and tell the user. "
            "Without a conflict it prints 'sync: no conflicts' and exits 0."
        ),
    )
    conflicts.set_defaults(func=_conflicts)
