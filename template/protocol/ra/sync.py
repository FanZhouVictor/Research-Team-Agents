"""Pull, push and find merge conflicts in the shared repository (spec §12).

pull and push run 'git pull' and 'git push' in the project root. A pull is a merge: it never
rebases and never opens an editor. When it stops on a conflict, git leaves the merge in place and
so does pull, because resolving a conflict in knowledge/ or decisions/ is for a human, never for
the AI (spec §12; conflicts elsewhere are treated the same way). unmerged_paths lists what the
merge left conflicted, protected_conflicts the part of it under knowledge/ or decisions/.

The functions let subprocess.CalledProcessError through; the command line (ra.cli_sync) reports
it. Nothing here prints.
"""

import subprocess
from pathlib import Path

__all__ = ["protected_conflicts", "pull", "push", "unmerged_paths"]

_PROTECTED = ("knowledge", "decisions")  # the folders whose conflicts only a human resolves


def _git(repo: Path, *args: str, joined: bool = False) -> str:
    """Run git with args in repo and return its stdout as text; CalledProcessError propagates.

    Output is read as UTF-8 with bad bytes replaced. With joined, git's stderr goes into the
    same pipe as its stdout, so that a failure carries everything git said, in order: 'git pull'
    reports the fetch on stderr and the merge conflict on stdout, and the stderr alone would
    not say why it failed.
    """
    done = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        check=True, cwd=repo, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if joined else subprocess.PIPE,
    )
    return done.stdout.decode("utf-8", errors="replace")


def pull(repo: Path) -> None:
    """Merge what the remote has new into the current branch: 'git pull --rebase=false --no-edit'.

    The merge never rebases, whatever pull.rebase says, and takes git's own merge message, so no
    editor opens. If it stops on a conflict, git leaves the merge in place in the work tree;
    unmerged_paths names the files, and nobody but a human resolves them (spec §12).

    Args:
        repo: Root of the git work tree.

    Raises:
        subprocess.CalledProcessError: git failed: a merge conflict, no remote or upstream, a
            local change the merge would overwrite, an earlier merge still unfinished, no
            network. Everything git said is in its stdout.
    """
    _git(repo, "pull", "--rebase=false", "--no-edit", joined=True)


def push(repo: Path) -> None:
    """Send the local commits of the current branch to its upstream: 'git push'.

    Args:
        repo: Root of the git work tree.

    Raises:
        subprocess.CalledProcessError: git refused or failed, for example because the remote has
            commits that are not here yet (pull first) or the branch has no upstream. Everything
            git said is in its stdout.
    """
    _git(repo, "push", joined=True)


def unmerged_paths(repo: Path) -> list[Path]:
    """The paths a merge left conflicted, relative to repo and sorted; [] when there is none.

    These are the paths that 'git diff --diff-filter=U' lists: content conflicts, files added
    or deleted on one side only, binary files. Names come back as they are. Git writes some
    names in quotes with escapes (a tab or a double quote in them) even with core.quotepath
    off, so the list is read NUL-terminated.

    Args:
        repo: Root of the git work tree.

    Raises:
        subprocess.CalledProcessError: git failed, for example repo is not a git repository.
    """
    listing = _git(repo, "diff", "--name-only", "--diff-filter=U", "-z")
    return sorted((Path(name) for name in listing.split("\0") if name), key=Path.as_posix)


def protected_conflicts(repo: Path) -> list[Path]:
    """The unmerged paths under knowledge/ or decisions/, sorted; only a human resolves them.

    Args:
        repo: Root of the git work tree.

    Raises:
        subprocess.CalledProcessError: git failed, as for unmerged_paths.
    """
    return [path for path in unmerged_paths(repo) if path.parts[0] in _PROTECTED]
