"""Shared pytest fixtures: git identity helper, minimal PDF writer and a fresh project repo."""

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

# Keep git subprocesses independent of the developer's own git configuration (commit
# signing, default branch, hooks, identity, ...). Git documents the null device for
# GIT_CONFIG_GLOBAL / GIT_CONFIG_SYSTEM (git >= 2.32): it then reads no global or system
# config. GIT_CONFIG_NOSYSTEM covers older git and Apple's extra Xcode-supplied config
# file, which GIT_CONFIG_SYSTEM does not switch off. Set at import time so that every
# subprocess started by any test inherits it.
os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
os.environ["GIT_CONFIG_SYSTEM"] = os.devnull
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"

GitIdentity = Callable[[Path, str, str], None]
MakePdf = Callable[[Path, str], None]

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


@pytest.fixture
def git_identity() -> GitIdentity:
    """Return git_identity(repo, name, email), which sets user.name and user.email in repo."""
    return _set_git_identity


@pytest.fixture
def make_pdf() -> MakePdf:
    """Return make_pdf(path, text), which writes a one-page PDF showing text; no PDF library."""
    return _write_pdf


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
