"""Install the RA_Agent skills for Claude Code and Codex, for every project of this person.

    python scripts/install_skills.py [--claude] [--codex] [--home DIR] [--dry-run]

Claude Code reads user-level skills from ~/.claude/skills/<name>/SKILL.md and Codex from
~/.codex/skills/<name>/SKILL.md. This copies every skill folder of plugin/skills/ (next to this
script) into the skills folder of each tool whose folder, ~/.claude or ~/.codex, exists, or of
the tools named with --claude and --codex, creating their folders. An earlier copy of a skill is
deleted first, so a run after 'git pull' updates every skill. Nothing else there is touched: a
folder with a skill's name that is not an RA_Agent skill (its SKILL.md cites no 'PROTOCOL.md §')
stays and is reported. Standard library only; it says so on a Python older than 3.10.

Exit status: 0 when every skill was copied (with --dry-run: would be); 1 when a skill was
refused, a file operation failed or Python is too old; 2 when no tool was found or named.
"""

from __future__ import annotations

import argparse
import io
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

__all__ = ["SOURCE", "TOOLS", "build_parser", "main", "skill_folders"]

SOURCE = Path(__file__).resolve().parents[1] / "plugin" / "skills"
TOOLS = {"claude": ".claude", "codex": ".codex"}  # each tool's folder in the home directory
_NEXT = {"claude": "start a new Claude Code session", "codex": "quit and reopen the Codex app"}
_MARK = "PROTOCOL.md §"  # every RA_Agent skill cites the PROTOCOL.md sections it implements


def build_parser() -> argparse.ArgumentParser:
    """The command line: --claude, --codex, --home DIR and --dry-run."""
    parser = argparse.ArgumentParser(prog="install_skills.py", description="Copy the RA_Agent "
                                     "skills into ~/.claude/skills/ and ~/.codex/skills/.")
    parser.add_argument("--claude", action="store_true",
                        help="install for Claude Code, creating ~/.claude/skills if needed")
    parser.add_argument("--codex", action="store_true",
                        help="install for Codex, creating ~/.codex/skills if needed")
    parser.add_argument("--home", type=Path, metavar="DIR",
                        help="use DIR as the home directory (default: your home directory)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print what would be done and change nothing")
    return parser


def skill_folders(source: Path = SOURCE) -> list[Path]:
    """The folders directly inside source that hold a SKILL.md, sorted by name."""
    entries = source.iterdir() if source.is_dir() else ()
    return sorted(entry for entry in entries if (entry / "SKILL.md").is_file())


def _targets(home: Path, named: list[str]) -> list[tuple[str, Path]]:
    """(tool, its skills folder) per tool to install for: with no tool named, each tool whose
    folder exists in home (a line is printed for each other tool); else the named tools."""
    targets = []
    for tool, folder in TOOLS.items():
        root = home / folder
        if named and tool not in named:
            continue
        if not named and not root.is_dir():
            print(f"skipped {tool}: {root} not found")
            continue
        targets.append((tool, root / "skills"))
    return targets


def _is_skill(path: Path) -> bool:
    """True if path is the folder of an RA_Agent skill: its SKILL.md cites PROTOCOL.md."""
    try:
        return _MARK in (path / "SKILL.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False


def _copy(skill: Path, skills_dir: Path, dry_run: bool) -> bool:
    """Copy one skill folder into skills_dir, replacing an earlier copy; False if refused."""
    dest = skills_dir / skill.name
    present = dest.exists() or dest.is_symlink()
    if present and not _is_skill(dest):
        print(f"refused {skill.name}: {dest} is not an RA_Agent skill; move it out of "
              f"{skills_dir}, then run this script again")
        return False
    note = " (replaced)" if present else ""
    if dry_run:
        print(f"would copy {skill.name} -> {dest}{note}")
        return True
    if dest.is_symlink():
        dest.unlink()  # remove the link only, never the folder it points to
    elif present:
        shutil.rmtree(dest)
    shutil.copytree(skill, dest, ignore=shutil.ignore_patterns(".DS_Store", "__pycache__"))
    print(f"copied {skill.name} -> {dest}{note}")
    return True


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return the exit status described in the module docstring."""
    if sys.version_info < (3, 10):  # noqa: UP036 - a 3.9 python3 must get this message
        print(f"error: Python 3.10 or newer is needed, this is {sys.version.split()[0]}; install "
              "it from https://www.python.org/downloads/", file=sys.stderr)
        return 1
    args = build_parser().parse_args(argv)
    home = args.home if args.home is not None else Path.home()
    skills = skill_folders()
    if not skills:
        print(f"error: no skill folders found in {SOURCE}", file=sys.stderr)
        return 1
    targets = _targets(home, [tool for tool in TOOLS if getattr(args, tool)])
    if not targets:
        print(f"error: found neither {home / TOOLS['claude']} nor {home / TOOLS['codex']}; open "
              "Claude Code or Codex once, or name the tool with --claude or --codex",
              file=sys.stderr)
        return 2
    refused = 0
    try:
        for _, skills_dir in targets:
            if not skills_dir.is_dir():
                if not args.dry_run:
                    skills_dir.mkdir(parents=True)
                print(f"{'would create' if args.dry_run else 'created'} {skills_dir}")
            refused += sum(not _copy(skill, skills_dir, args.dry_run) for skill in skills)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    total = len(skills) * len(targets)
    folders = " and ".join(str(skills_dir) for _, skills_dir in targets)
    if args.dry_run:
        print(f"dry run: would copy {total - refused} of {total} skill folders into {folders}; "
              "nothing was changed")
    else:
        print(f"done: copied {total - refused} of {total} skill folders into {folders}")
    if refused:
        print(f"{refused} refused: move each refused folder out of its skills folder, then run "
              "this script again")
        return 1
    if not args.dry_run:
        print("next: " + "; ".join(_NEXT[tool] for tool, _ in targets))
    return 0


if __name__ == "__main__":  # print paths as UTF-8, also where a pipe has a legacy code page
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    sys.exit(main())
