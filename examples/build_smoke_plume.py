"""Build the example project smoke-plume: a scripted, reproducible history of the protocol.

    python examples/build_smoke_plume.py [dest] [--force]

Run it from a checkout of the framework repository. dest defaults to examples/smoke-plume
beside this script, which the framework repository git-ignores. The project starts with 'ra
init' (ra.scaffold.init_project); then each Step of STEPS runs one verb of
smoke_plume_verbs.py, which writes files through the ra package, and the write becomes one
structured commit (ra.commit). Fan <fan@x> and Lee <lee@x> take turns as the git identity,
every commit has a fixed author and committer date, and git configuration from outside is
shut out, so two builds from the same template give the same commit ids. The text comes
from smoke_plume_content.py and the placeholder PDFs from smoke-plume-src/pdf/.
"""

import argparse
import contextlib
import os
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_PROTOCOL = _HERE.parent / "template" / "protocol"  # the ra package of this checkout
if str(_PROTOCOL) not in sys.path:
    sys.path.insert(0, str(_PROTOCOL))

import smoke_plume_content as content
from ra.commit import commit
from ra.scaffold import init_project
from smoke_plume_verbs import (
    Step,
    Write,
    accept_decision,
    add_fact,
    add_literature,
    author,
    close_question,
    propose_decision,
    propose_question,
    reread_literature,
    rewrite_status,
    set_up_project,
    supersede_decision,
    write_log,
)

__all__ = ["DEFAULT_DEST", "STEPS", "build", "main"]

DEFAULT_DEST = _HERE / "smoke-plume"
_INIT_AT = "2026-10-25 14:20"  # the 'ra init' commit; STEPS follow it
_ZONE = "+0000"  # the time zone of every commit date
_EMAILS = {member["person"]: member["email"] for member in (content.FOUNDER, content.MEMBER)}
# Outside git settings would change the commits (signing, hooks, line endings) or send them
# elsewhere (an inherited GIT_DIR); identity and dates are set per commit.
_GIT_ENV: dict[str, str | None] = {
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
    **dict.fromkeys((
        "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT", "GIT_DIR", "GIT_WORK_TREE",
        "GIT_INDEX_FILE", "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_AUTHOR_DATE",
        "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "GIT_COMMITTER_DATE",
    )),
}

_CLAUDE, _CODEX = "claude-code", "codex"
STEPS: tuple[Step, ...] = (
    # 2026-10-25: Fan fills in PROJECT.md, then a claude-code session from 14:32 to 16:05
    Step("2026-10-25 14:26", "Fan", _CLAUDE, set_up_project),
    Step("2026-10-25 14:40", "Fan", _CLAUDE, propose_question, "Q-2026-10-25-plume-baselines"),
    Step("2026-10-25 14:44", "Fan", _CLAUDE, propose_question, "Q-2026-10-25-abi-band-choice"),
    Step("2026-10-25 15:05", "Fan", _CLAUDE, add_literature, "smith2024-plume-goes"),
    Step("2026-10-25 15:14", "Fan", _CLAUDE, add_fact, "band7-2km"),
    Step("2026-10-25 15:35", "Fan", _CLAUDE, add_literature, "jones2023-plume-unet"),
    Step("2026-10-25 15:48", "Fan", _CLAUDE, propose_decision, "D-2026-10-25-loss-function"),
    Step("2026-10-25 15:55", "Fan", _CLAUDE, accept_decision, "D-2026-10-25-loss-function"),
    Step("2026-10-25 16:02", "Fan", _CLAUDE, write_log, "2026-10-25-fan-claude-code-1432"),
    Step("2026-10-25 16:05", "Fan", _CLAUDE, rewrite_status, "2026-10-25-fan-claude-code-1432"),
    # 2026-10-26: Fan proposes a question and a decision, and accepts the decision
    Step("2026-10-26 10:12", "Fan", _CLAUDE, propose_question, "Q-2026-10-26-dataset-size"),
    Step("2026-10-26 10:30", "Fan", _CLAUDE, propose_decision, "D-2026-10-26-eval-metric"),
    Step("2026-10-26 16:40", "Fan", _CLAUDE, accept_decision, "D-2026-10-26-eval-metric"),
    # 2026-10-27: Lee's codex session from 09:10 to 11:40; Fan closes a question afterwards
    Step("2026-10-27 10:05", "Lee", _CODEX, reread_literature, "smith2024-plume-goes"),
    Step("2026-10-27 10:50", "Lee", _CODEX, add_fact, "band7-1km"),
    Step("2026-10-27 11:36", "Lee", _CODEX, write_log, "2026-10-27-lee-codex-0910"),
    Step("2026-10-27 11:40", "Lee", _CODEX, rewrite_status, "2026-10-27-lee-codex-0910"),
    Step("2026-10-27 15:20", "Fan", _CLAUDE, close_question, "Q-2026-10-26-dataset-size"),
    # 2026-10-28: Fan's codex session from 10:00 to 10:45. Its literature commit comes after
    # Lee's last commit, so Lee's next digest lists it.
    Step("2026-10-28 10:15", "Fan", _CODEX, supersede_decision, "D-2026-10-28-loss-function-v2"),
    Step("2026-10-28 10:32", "Fan", _CODEX, add_literature, "brown2022-cloud-masks"),
    Step("2026-10-28 10:42", "Fan", _CODEX, write_log, "2026-10-28-fan-codex-1000"),
    Step("2026-10-28 10:45", "Fan", _CODEX, rewrite_status, "2026-10-28-fan-codex-1000"),
)


@contextlib.contextmanager
def _environ(values: Mapping[str, str | None]) -> Iterator[None]:
    """Set (a str) or unset (None) environment variables inside the block, then restore them."""
    saved = {name: os.environ.get(name) for name in values}
    try:
        _apply(values)
        yield
    finally:
        _apply(saved)


def _apply(values: Mapping[str, str | None]) -> None:
    """Set each variable to its str value, or unset it for None."""
    for name, value in values.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


def _dated(when: str) -> contextlib.AbstractContextManager[None]:
    """A block whose commits get when ('YYYY-MM-DD HH:MM' in _ZONE) as author and committer date."""
    moment = datetime.strptime(f"{when} {_ZONE}", "%Y-%m-%d %H:%M %z")
    stamp = f"{int(moment.timestamp())} {_ZONE}"  # git's internal date format
    return _environ({"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp})


def _commit(repo: Path, step: Step, write: Write) -> None:
    """Commit write in repo as step.person with step.agent, dated step.when."""
    for key, value in (("user.name", step.person), ("user.email", _EMAILS[step.person])):
        subprocess.run(["git", "config", key, value], cwd=repo, check=True, text=True,
                       capture_output=True)
    links = list(dict.fromkeys((*write.paths, *write.cited)))
    with _dated(step.when):
        commit(repo, [repo / path for path in write.paths], write.type_tag, write.subject,
               step.person, step.agent, links)


def build(dest: Path, *, template_dir: Path | None = None) -> Path:
    """Build the example project at dest and return dest.

    dest must be absent or an empty directory, as for 'ra init'; template_dir is the RA
    template to copy, by default the template/ of this checkout. The result is the same, down
    to the commit ids, every time it is built from the same template. A failure after 'ra
    init' leaves the partial project in place.

    Raises:
        FileExistsError: dest exists and is not an empty directory; nothing is written.
        ValueError: The template does not fit the content (a section or file is missing).
        subprocess.CalledProcessError: A git command failed.
    """
    dest = Path(dest)
    founder = content.FOUNDER
    with _environ(_GIT_ENV):
        with _dated(_INIT_AT):
            init_project(dest, content.NAME, founder["person"], author(founder),
                         founder["platforms"], founder["role"], template_dir)
        for step in STEPS:
            _commit(dest, step, step.verb(dest, step))
    return dest


def _rmtree(path: Path) -> None:
    """Delete the directory tree at path, read-only files (git objects on Windows) included."""

    def retry(func: Callable[..., Any], name: str, _error: object) -> None:
        os.chmod(name, stat.S_IWRITE)
        func(name)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=retry)
    else:
        shutil.rmtree(path, onerror=retry)


def _remove_earlier_build(dest: Path) -> None:
    """Delete dest if it is an earlier build of this example; an absent or empty dest stays.

    Raises:
        ValueError: dest holds anything else; it is left untouched.
    """
    if not dest.exists() or (dest.is_dir() and not any(dest.iterdir())):
        return
    project = dest / "PROJECT.md"
    if not ((dest / ".git").is_dir() and project.is_file()
            and content.NOTICE in project.read_text(encoding="utf-8", errors="replace")):
        raise ValueError(f"refusing to delete {dest}: it is not an earlier build of this example")
    _rmtree(dest)


def _git_said(exc: subprocess.CalledProcessError) -> str:
    """What a failed git command printed, on one line."""
    said = exc.stderr or exc.stdout or ""
    text = said.decode("utf-8", errors="replace") if isinstance(said, bytes) else said
    return " ".join(text.split()) or f"exit status {exc.returncode}"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line; return the exit code: 0 when built, 1 when refused or failed."""
    parser = argparse.ArgumentParser(
        prog="build_smoke_plume.py",
        description="Build the example project smoke-plume: a git repository whose history "
        "shows the shared-repo protocol at work. Prints the path of the project.",
    )
    parser.add_argument("dest", nargs="?", type=Path, default=DEFAULT_DEST,
                        help="where to build it (default: smoke-plume beside this script)")
    parser.add_argument("--force", action="store_true",
                        help="delete dest first if it holds an earlier build of the example")
    args = parser.parse_args(argv)
    try:
        if args.force:
            _remove_earlier_build(args.dest)
        build(args.dest)
    except FileExistsError as exc:
        print(f"error: {exc}; pass --force to replace an earlier build", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        command = " ".join(str(part) for part in exc.cmd)
        print(f"error: {command} failed: {_git_said(exc)}", file=sys.stderr)
        return 1
    print(args.dest.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
