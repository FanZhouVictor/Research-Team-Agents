"""Shared pytest fixtures (git identity, minimal PDF writer, a fresh project repo, two clones of
a shared one, the built example project) and the plain helpers that tests import with
'from conftest import _lit, _decision, _commit_all, _append_fact'."""

import os
import re
import shutil
import stat
import subprocess
import tempfile
from collections.abc import Callable, Iterator, Sequence
from datetime import date
from pathlib import Path

import pytest
from ra.frontmatter import parse, write
from ra.newfile import new_decision, new_literature, new_topic
from ra.scaffold import init_project

GitIdentity = Callable[[Path, str, str], None]
MakePdf = Callable[[Path, str], None]
FilesOf = Callable[[Path], set[str]]

# What init_project must never copy into a project; '*.pyc' is a file pattern.
_CACHES = ("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".DS_Store", "*.pyc")


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


# --- helpers imported by tests ----------------------------------------------------------

# The body of the claims section: from its heading to the next '## ' heading or the end.
_CLAIMS_SECTION = re.compile(
    r"(^## Claims for this project\n).*?(?=^## |\Z)", re.MULTILINE | re.DOTALL
)


def _lit(
    repo: Path,
    make_pdf: MakePdf,
    citekey: str,
    *,
    doi: str | None = None,
    arxiv: str | None = None,
    title: str = "T",
    claims: Sequence[tuple[str, str | None]] = (("c", "p.1"),),
) -> Path:
    """Create a valid literature record with new_literature and give it these claims.

    The record has title, year 2024, doi and arxiv when given, and first reader Fan / codex /
    2026-10-25; its PDF is written by make_pdf in a temporary directory outside repo. Each
    claim is (text, where), written in the spec §10.3 form; the where line is left out when
    where is None. Returns the record's path.
    """
    meta: dict[str, object] = {
        "title": title, "year": 2024, "person": "Fan", "agent": "codex", "date": "2026-10-25",
    }
    if doi is not None:
        meta["doi"] = doi
    if arxiv is not None:
        meta["arxiv"] = arxiv
    with tempfile.TemporaryDirectory() as scratch:
        pdf = Path(scratch) / f"{citekey}.pdf"
        make_pdf(pdf, citekey)
        path = new_literature(repo, citekey, meta, pdf)
    lines: list[str] = []
    for text, where in claims:
        lines.append(f"- {text}\n")
        if where is not None:
            lines.append(f"  - where: {where}\n")
        lines.append("  - kind: result · basis: stated by paper\n")
        lines.append("  - by: Fan · codex · 2026-10-25\n")
    front, body = parse(path)
    body = _CLAIMS_SECTION.sub(lambda m: m.group(1) + "".join(lines) + "\n", body, count=1)
    write(path, front, body)
    return path


def _decision(repo: Path, slug: str, *, status: str) -> Path:
    """Create decisions/D-2026-10-25-<slug>.md (title "t", Fan / codex, no links) with status.

    An accepted decision also gets 'accepted-by: Fan · 2026-10-26'. Returns the path.
    """
    path = new_decision(repo, slug, "t", "Fan", "codex", date(2026, 10, 25), [])
    meta, body = parse(path)
    meta["status"] = status
    if status == "accepted":
        meta["accepted-by"] = "Fan · 2026-10-26"
    write(path, meta, body)
    return path


def _commit_all(repo: Path, msg: str) -> None:
    """Stage everything in repo and commit it with msg; the commit may be empty."""
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--allow-empty", "-m", msg)


def _drop_head_object(repo: Path) -> None:
    """Delete the loose object of the commit HEAD names: HEAD still resolves, 'git log' fails."""
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True,
                         capture_output=True).stdout.strip()
    path = repo / ".git" / "objects" / sha[:2] / sha[2:]
    os.chmod(path, stat.S_IWRITE)  # git writes objects read-only; Windows refuses to delete them
    path.unlink()


def _append_fact(repo: Path, topic: str, text: str) -> None:
    """Append one fact line (spec §11) to knowledge/<topic>.md, creating the topic if it is new.

    The topic is made by new_topic with the scope '<topic> facts'. That scope is fixed, so two
    clones that create the same topic write the same file head and the same registry line, and
    only their fact lines differ. The metadata of the fact is the same for every call.
    """
    path = repo / "knowledge" / f"{topic}.md"
    if not path.exists():
        new_topic(repo, topic, f"{topic} facts")
    line = f"- {text} (src: seed2024-x §1 · Fan/codex 2026-10-25 · approved Fan · ok)\n"
    with path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(line)


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
def repo(tmp_path: Path) -> Path:
    """A fresh project made by init_project: the real scaffold, git-initialised on main.

    Fan <fan@x> is the git identity and the only member. The repository has one commit, the
    first commit of init_project, and a clean working tree.
    """
    root = tmp_path / "repo"
    init_project(root, "Test Project", "Fan", "Fan <fan@x>", ["claude-code", "codex"], "PI")
    return root


@pytest.fixture
def two_clones(tmp_path: Path, git_identity: GitIdentity) -> tuple[Path, Path]:
    """Two clones of one shared project, as two team members have it: (a, b).

    A project made by init_project (name 'Seed', Fan <fan@x>) becomes the bare repository
    tmp_path/origin.git; a and b are clones of it, with the local git identities Fan <fan@x>
    and Lee <lee@x>. Each is on main with origin/main as its upstream, so 'git pull' and
    'git push' work without arguments, and each has a clean working tree at the first commit.
    """
    seed = tmp_path / "seed"
    init_project(seed, "Seed", "Fan", "Fan <fan@x>", ["claude-code", "codex"], "PI")
    origin = tmp_path / "origin.git"
    _git(tmp_path, "clone", "-q", "--bare", str(seed), str(origin))
    a, b = tmp_path / "a", tmp_path / "b"
    for clone, person, email in ((a, "Fan", "fan@x"), (b, "Lee", "lee@x")):
        _git(tmp_path, "clone", "-q", str(origin), str(clone))
        git_identity(clone, person, email)
    return a, b


@pytest.fixture(scope="session")
def example_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The example project of examples/build_smoke_plume.py, built once for the session.

    It is built into a temporary directory, never into the git-ignored examples/smoke-plume.
    Tests only read it.
    """
    # examples/ is on the pytest path (pyproject.toml); imported here, so that only the tests that
    # use the example need it.
    from build_smoke_plume import build

    return build(tmp_path_factory.mktemp("example") / "smoke-plume")


def _init_project(dest: Path, template_dir: Path | None = None, **fields: object) -> None:
    """init_project for the project 'Smoke Plume' and its member Fan, with some fields replaced.

    fields are name, person, git_author, platforms and role; template_dir is the template to copy.
    """
    given = {
        "name": "Smoke Plume", "person": "Fan", "git_author": "Fan <fan@x>",
        "platforms": ["claude-code", "codex"], "role": "PI", **fields,
    }
    init_project(
        dest, given["name"], given["person"], given["git_author"], given["platforms"],
        given["role"], template_dir,
    )


@pytest.fixture
def template(tmp_path: Path) -> Path:
    """A scratch copy of the real template, without caches, that a test may break on purpose."""
    path = tmp_path / "template"
    source = Path(__file__).resolve().parents[1] / "template"
    shutil.copytree(source, path, ignore=shutil.ignore_patterns(*_CACHES))
    return path
