"""Create a project repository from the template: the library behind 'ra init'.

The protocol version is the 'version' in the frontmatter of the template's PROTOCOL.md, and
is written nowhere else; init_project stamps it into PROJECT.md and the first commit.
"""

import contextlib
import re
import shutil
import subprocess
from pathlib import Path

from ra import frontmatter
from ra.commit import commit
from ra.newfile import AGENTS

__all__ = ["init_project"]

# template/, two levels above this file; in a project that is its root, which has a .git entry
_TEMPLATE = Path(__file__).resolve().parents[2]
_REQUIRED = ("PROJECT.md", "PROTOCOL.md", "protocol/ra/scaffold.py")  # what makes the template
_IGNORED = shutil.ignore_patterns(  # caches and leftovers that must never land in a project
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".DS_Store", "*.pyc"
)
_TOKEN = re.compile(r"\{(\w+)\}")
_AUTHOR = re.compile(r"(?P<name>[^<>\s](?:[^<>\r\n]*[^<>\s])?) <(?P<email>[^<>\s@]+@[^<>\s@]+)>")


def _line(value: object, label: str) -> str:
    """value without surrounding whitespace; ValueError unless it is one non-blank line."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must not be empty")
    text = value.strip()
    if "\n" in text or "\r" in text:
        raise ValueError(f"{label} must be one line, got {value!r}")
    return text


def _template_version(template: Path) -> str:
    """The protocol version of template; ValueError unless it is the RA template.

    It needs the _REQUIRED files, a version in PROTOCOL.md and no .git entry (a project).
    """
    missing = [rel for rel in _REQUIRED if not (template / rel).is_file()]
    if missing:
        raise ValueError(f"{template} is not the RA template: {', '.join(missing)} not found")
    if (template / ".git").exists():
        raise ValueError(
            "run ra init from the framework repository, not inside a project "
            f"({template} has a .git entry)"
        )
    protocol = template / "PROTOCOL.md"
    version = frontmatter.parse(protocol)[0].get("version")
    if not (version.strip() if isinstance(version, str) else ""):
        raise ValueError(f"{protocol} needs 'version: <x.y.z>' in its frontmatter, got {version!r}")
    return _line(version, f"the version in {protocol}")


def _check_dest(dest: Path) -> None:
    """Raise FileExistsError unless dest does not exist or is an empty directory."""
    if not dest.exists() or (dest.is_dir() and not any(dest.iterdir())):
        return
    raise FileExistsError(f"{dest} exists and is not an empty directory")


def _split_author(git_author: str) -> tuple[str, str, str]:
    """(author, name, email) of 'Name <email>', author stripped; ValueError for anything else."""
    author = _line(git_author, "git author")
    found = _AUTHOR.fullmatch(author)
    if found is None:
        raise ValueError(f"git author must look like 'Name <email>', got {author!r}")
    return author, found["name"], found["email"]


def _check_platforms(platforms: list[str]) -> list[str]:
    """A copy of platforms; ValueError if it is empty, names an unknown tool or repeats one."""
    if not platforms:
        raise ValueError("platforms must not be empty")
    for index, platform in enumerate(platforms):
        if platform not in AGENTS:
            raise ValueError(f"platform must be one of {', '.join(AGENTS)}, got {platform!r}")
        if platform in platforms[:index]:
            raise ValueError(f"platforms must not repeat {platform!r}")
    return list(platforms)


def _fill(path: Path, values: dict[str, str]) -> None:
    """Replace the {word} tokens of the file at path by values, in one pass."""
    text = path.read_text(encoding="utf-8")
    filled = _TOKEN.sub(lambda token: values.get(token.group(1), token.group(0)), text)
    path.write_text(filled, encoding="utf-8", newline="")


def _git(repo: Path, *args: str) -> None:
    """Run git with args in repo; a failure raises CalledProcessError."""
    subprocess.run(["git", *args], check=True, text=True, capture_output=True, cwd=repo)


def _discard(dest: Path, existed: bool) -> None:
    """Undo a failed init: remove dest, or empty it again if it was there before.

    Best effort and never raises, so the caller sees the error that made init fail.
    """
    if not existed:
        shutil.rmtree(dest, ignore_errors=True)
        return
    with contextlib.suppress(OSError):
        for entry in dest.iterdir():
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry, ignore_errors=True)
            else:
                entry.unlink(missing_ok=True)


def init_project(
    dest: Path,
    name: str,
    person: str,
    git_author: str,
    platforms: list[str],
    role: str,
    template_dir: Path | None = None,
) -> None:
    """Create the project repository at dest from the template and make its first commit.

    dest must be absent or an empty directory; a relative path is read from the current
    directory and missing parents are created. git_author is 'Name <email>' and becomes the
    repository's user.name and user.email. platforms are the member's AI tools, one or more of
    AGENTS without repeats, listed in this order; the first signs the first commit. template_dir
    defaults to the template/ that holds this package.

    Everything is checked before anything is written. If a later step fails, a dest that init
    created is removed again and an empty dest that was there before is emptied again.

    Raises:
        ValueError: A bad argument (a blank or multi-line name, person or role; git_author not
            'Name <email>'; platforms empty, unknown or repeated), or template_dir is not the
            template or is a project (it has a .git entry).
        FileExistsError: dest exists and is not an empty directory.
        subprocess.CalledProcessError: A git command failed.
        FileNotFoundError: git is not installed.
    """
    source = _TEMPLATE if template_dir is None else template_dir
    version = _template_version(source)
    _check_dest(dest)
    author, author_name, author_email = _split_author(git_author)
    tools = _check_platforms(platforms)
    values = {
        "protocol_version": version,
        "name": _line(name, "name"),
        "person": _line(person, "person"),
        "git_author": author,
        "platforms": ", ".join(tools),
        "role": _line(role, "role"),
    }
    existed = dest.exists()
    try:
        shutil.copytree(source, dest, ignore=_IGNORED, dirs_exist_ok=True)
        _fill(dest / "PROJECT.md", values)
        _git(dest, "init", "-q", "-b", "main")
        _git(dest, "config", "user.name", author_name)
        _git(dest, "config", "user.email", author_email)
        _git(dest, "add", "-A")
        subject = f"initialise project from RA_Agent template {version}"
        links = ["PROJECT.md", "PROTOCOL.md"]
        commit(dest, [], "protocol", subject, values["person"], tools[0], links)
    except BaseException:
        _discard(dest, existed)
        raise
