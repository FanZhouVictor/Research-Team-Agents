"""Shared pytest fixtures: git identity helper, minimal PDF writer and a fresh project repo."""

import os
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

GitIdentity = Callable[[Path, str, str], None]
MakePdf = Callable[[Path, str], None]
FilesOf = Callable[[Path], set[str]]

# Directories of a project repository that the repo fixture creates.
_PROJECT_DIRS = (
    "questions",
    "decisions",
    "literature/pdf",
    "log",
    "knowledge",
    "protocol/templates",
)


def _git(repo: Path, *args: str) -> None:
    """Run git inside repo and raise if it fails."""
    subprocess.run(["git", *args], cwd=repo, check=True, text=True)


def _write(path: Path, text: str) -> None:
    """Write UTF-8 text with LF line endings on every OS."""
    path.write_text(text, encoding="utf-8", newline="")


def _set_git_identity(repo: Path, name: str, email: str) -> None:
    """Set the repo-local git author identity."""
    _git(repo, "config", "user.name", name)
    _git(repo, "config", "user.email", email)


def _write_pdf(path: Path, text: str) -> None:
    """Write a minimal valid one-page PDF whose only content is text (Latin-1 characters)."""
    shown = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = f"BT /F1 12 Tf 72 720 Td ({shown}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
            b"/Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref_at = len(pdf)
    size = len(objects) + 1
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % size
    for offset in offsets:
        pdf += b"%010d 00000 n \n" % offset
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, xref_at)
    path.write_bytes(bytes(pdf))


def _list_files(root: Path) -> set[str]:
    """Every file under root as a POSIX path relative to it, ignoring the .git directory."""
    return {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(root).parts
    }


@pytest.fixture(scope="session", autouse=True)
def _isolated_git_environment(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Make every git subprocess ignore the developer's own git configuration.

    Commit signing, default branch, hooks and identity from the developer's config must
    not leak into the tests, on any git version:
    - HOME, XDG_CONFIG_HOME and USERPROFILE point at an empty scratch directory, so the
      per-user config files are not found (works for every git version);
    - GIT_CONFIG_GLOBAL and GIT_CONFIG_SYSTEM are the null device, which git >= 2.32
      documents as "read nothing";
    - GIT_CONFIG_NOSYSTEM covers older git and Apple's Xcode-supplied config file, which
      GIT_CONFIG_SYSTEM does not switch off.
    The environment is restored when the session ends.
    """
    home = str(tmp_path_factory.mktemp("home"))
    with pytest.MonkeyPatch.context() as patch:
        for name in ("HOME", "XDG_CONFIG_HOME", "USERPROFILE"):
            patch.setenv(name, home)
        patch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
        patch.setenv("GIT_CONFIG_SYSTEM", os.devnull)
        patch.setenv("GIT_CONFIG_NOSYSTEM", "1")
        yield


@pytest.fixture
def git_identity() -> GitIdentity:
    """Return git_identity(repo, name, email), which sets user.name and user.email in repo."""
    return _set_git_identity


@pytest.fixture
def make_pdf() -> MakePdf:
    """Return make_pdf(path, text), which writes a one-page PDF showing text; no PDF library."""
    return _write_pdf


@pytest.fixture
def files_of() -> FilesOf:
    """Return files_of(root): the files under root as POSIX paths relative to it, minus .git/."""
    return _list_files


@pytest.fixture
def paper(tmp_path: Path, make_pdf: MakePdf) -> Path:
    """A one-page PDF at tmp_path/paper.pdf, beside the repo fixture's tmp_path/repo."""
    path = tmp_path / "paper.pdf"
    make_pdf(path, "hello")
    return path


@pytest.fixture
def repo(tmp_path: Path, git_identity: GitIdentity) -> Path:
    """A fresh project directory with the protocol layout, git-initialised on main as Fan <fan@x>.

    Hand-built stand-in for what the scaffold command will create; it has no commits yet.
    """
    root = tmp_path / "repo"
    for rel in _PROJECT_DIRS:
        (root / rel).mkdir(parents=True)
    _write(root / "PROJECT.md", "# Test Project\n\n## Current status\n")
    _write(root / "knowledge" / "README.md", "# Topic registry\n\n")
    _write(root / "knowledge" / "glossary.md", "# Glossary\n")
    _git(root, "init", "-q", "-b", "main")
    git_identity(root, "Fan", "fan@x")
    return root
