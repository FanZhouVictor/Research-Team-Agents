"""Tests for scripts/install_skills.py and for the onboarding documents that send people to it.

The script runs as a person runs it: in a subprocess, with this interpreter, against a scratch
home directory given with --home, so the real ~/.claude and ~/.codex are never touched. The
document tests hold INSTALL.md, README.md, plugin/README.md and docs/pilot-checklist.md to this
repository: every framework path they name exists, every relative link resolves, and every
command they show for protocol/ra.py or scripts/install_skills.py parses with that program's own
parser once its placeholders are filled in (the approach of tests/test_docs.py).
"""

import importlib.util
import re
import shlex
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from ra.cli import build_parser
from test_docs import ROOT, _blocks, _check_command

SCRIPT = ROOT / "scripts" / "install_skills.py"
SOURCE = ROOT / "plugin" / "skills"
NAMES = sorted(path.parent.name for path in SOURCE.glob("*/SKILL.md"))
INSTALL = ROOT / "INSTALL.md"
# The documents that send people to the script and the helper, those that exist.
DOCS = [path for path in (INSTALL, ROOT / "README.md", ROOT / "plugin" / "README.md",
                          ROOT / "docs" / "pilot-checklist.md") if path.is_file()]
_PLACEHOLDER = re.compile(r"<[^<>\n]*>")
_VALUES = {"<platforms>": "claude-code codex", "<agent>": "codex"}  # values a parser checks
_URL = re.compile(r"https?://\S+")
# A framework path in running text or a command: docs/…, scripts/…, template/… and so on.
_FRAMEWORK_PATH = re.compile(
    r"(?<![\w./~-])(?:docs|examples|plugin|scripts|template|tests)/[\w./-]*"
)
_LINK = re.compile(r"\]\(([^)\s]+)\)")


def _run(home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the script with --home home and args; a non-zero exit does not raise."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--home", str(home), *args],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )


def _home(tmp_path: Path, *folders: str) -> Path:
    """A scratch home directory that holds the given tool folders, such as '.codex'."""
    home = tmp_path / "home"
    home.mkdir()
    for folder in folders:
        (home / folder).mkdir()
    return home


def _names(folder: Path) -> list[str]:
    """The names of the entries directly inside folder, sorted."""
    return sorted(entry.name for entry in folder.iterdir())


def _files(root: Path) -> dict[str, bytes]:
    """Every file under root by its POSIX path relative to root, with its bytes."""
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


def _script() -> ModuleType:
    """scripts/install_skills.py imported as a module, for its build_parser()."""
    spec = importlib.util.spec_from_file_location("install_skills", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- the script --------------------------------------------------------------------------------


def test_the_plugin_has_the_twelve_skills():
    assert len(NAMES) == 12 and "session-start" in NAMES and "project-init" in NAMES


def test_both_tools_get_every_skill_byte_for_byte(tmp_path):
    home = _home(tmp_path, ".claude", ".codex")
    result = _run(home)
    assert result.returncode == 0, result.stderr
    for folder in (".claude", ".codex"):
        skills = home / folder / "skills"
        assert _names(skills) == NAMES
        for name in NAMES:
            assert _files(skills / name) == _files(SOURCE / name), name
        assert f"copied session-start -> {skills / 'session-start'}\n" in result.stdout
    assert "done: copied 24 of 24 skill folders" in result.stdout
    assert "next: start a new Claude Code session; quit and reopen the Codex app" in result.stdout


def test_a_tool_that_is_not_installed_is_skipped(tmp_path):
    home = _home(tmp_path, ".codex")
    result = _run(home)
    assert result.returncode == 0, result.stderr
    assert f"skipped claude: {home / '.claude'} not found" in result.stdout
    assert _names(home) == [".codex"]
    assert _names(home / ".codex" / "skills") == NAMES


def test_no_tool_at_all_exits_2_and_changes_nothing(tmp_path):
    home = _home(tmp_path)
    result = _run(home)
    assert result.returncode == 2
    assert "error: found neither" in result.stderr and "--codex" in result.stderr
    assert _names(home) == []


def test_a_dry_run_changes_nothing(tmp_path):
    home = _home(tmp_path, ".claude", ".codex")
    result = _run(home, "--dry-run")
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert sum(line.startswith("would copy ") for line in lines) == 2 * len(NAMES)
    assert lines[-1].startswith("dry run: would copy 24 of 24 skill folders")
    assert lines[-1].endswith("nothing was changed")
    assert _names(home / ".claude") == [] and _names(home / ".codex") == []


def test_a_second_run_replaces_each_skill_and_drops_stale_files(tmp_path):
    home = _home(tmp_path, ".codex")
    assert _run(home).returncode == 0
    skills = home / ".codex" / "skills"
    stale = skills / "session-start" / "stale.md"
    stale.write_text("a file an earlier version had", encoding="utf-8")
    (skills / "add-literature" / "SKILL.md").write_text("PROTOCOL.md § old", encoding="utf-8")
    own = skills / "my-own-skill" / "SKILL.md"  # the person's other skills stay as they are
    system = skills / ".system" / "bundled" / "SKILL.md"
    for path in (own, system):
        path.parent.mkdir(parents=True)
        path.write_text("not ours", encoding="utf-8")
    assert _run(home, "--dry-run").returncode == 0
    assert stale.exists()
    result = _run(home)
    assert result.returncode == 0, result.stderr
    assert not stale.exists()
    for name in NAMES:
        assert _files(skills / name) == _files(SOURCE / name), name
    assert own.read_text(encoding="utf-8") == system.read_text(encoding="utf-8") == "not ours"
    assert _names(skills) == sorted([*NAMES, ".system", "my-own-skill"])
    assert f"copied session-start -> {skills / 'session-start'} (replaced)" in result.stdout


def test_the_codex_flag_creates_its_folders_and_leaves_claude_alone(tmp_path):
    home = _home(tmp_path, ".claude")
    result = _run(home, "--codex")
    assert result.returncode == 0, result.stderr
    assert f"created {home / '.codex' / 'skills'}" in result.stdout
    assert _names(home / ".codex" / "skills") == NAMES
    assert _names(home / ".claude") == []


def test_a_folder_with_a_skill_name_that_is_not_ours_is_kept(tmp_path):
    home = _home(tmp_path, ".claude")
    theirs = home / ".claude" / "skills" / "session-start" / "SKILL.md"
    theirs.parent.mkdir(parents=True)
    text = "---\nname: session-start\ndescription: another framework's skill\n---\n"
    theirs.write_text(text, encoding="utf-8")
    result = _run(home)
    assert result.returncode == 1
    assert f"refused session-start: {theirs.parent} is not an RA_Agent skill" in result.stdout
    assert theirs.read_text(encoding="utf-8") == text
    assert _names(home / ".claude" / "skills") == NAMES  # the other eleven are copied
    assert "done: copied 11 of 12 skill folders" in result.stdout


def test_a_python_older_than_3_10_gets_a_message_and_nothing_is_written(
    tmp_path, monkeypatch, capsys
):
    # The script loads on 3.9 (its annotations are not evaluated), so the macOS python3 says why.
    home = _home(tmp_path, ".claude")
    script = _script()
    monkeypatch.setattr(script.sys, "version_info", (3, 9, 6, "final", 0))
    assert script.main(["--home", str(home)]) == 1
    assert "error: Python 3.10 or newer is needed" in capsys.readouterr().err
    assert _names(home / ".claude") == []


# --- the documents -----------------------------------------------------------------------------


def _commands(doc: Path) -> list[list[str]]:
    """The 'python …' commands of the fenced blocks of doc, as words, each placeholder <…>
    filled in; a line 'a && b' gives the commands a and b."""
    commands = []
    for block in _blocks(doc.read_text(encoding="utf-8")):
        for line in block.splitlines():
            for part in line.split("&&"):
                if part.strip().startswith(("python ", "python3 ")):
                    filled = _PLACEHOLDER.sub(lambda m: _VALUES.get(m.group(0), "x"), part)
                    commands.append(shlex.split(filled))
    return commands


def _framework_paths(doc: Path) -> set[str]:
    """The framework paths doc names; '<framework>/scripts/…' names scripts/…."""
    text = _PLACEHOLDER.sub(" ", _URL.sub(" ", doc.read_text(encoding="utf-8")))
    text = re.sub(r" /", " ", text)
    return {path.rstrip(".") for path in _FRAMEWORK_PATH.findall(text)}


@pytest.mark.parametrize("doc", DOCS, ids=lambda path: path.name)
def test_every_framework_path_and_relative_link_exists(doc):
    for path in _framework_paths(doc):
        assert (ROOT / path).exists(), f"{doc.name} names {path}, which does not exist"
    for target in _LINK.findall(doc.read_text(encoding="utf-8")):
        if not target.startswith(("http://", "https://", "mailto:", "#")):
            assert (doc.parent / target.split("#")[0]).exists(), f"{doc.name} links {target}"


@pytest.mark.parametrize("doc", DOCS, ids=lambda path: path.name)
def test_every_command_shown_parses(doc):
    script_parser = _script().build_parser()
    for words in _commands(doc):
        program = words[1].replace("\\", "/") if len(words) > 1 else ""
        if program.endswith("protocol/ra.py"):
            _check_command(" ".join(words), build_parser())
            parser = build_parser()
        elif program.endswith("scripts/install_skills.py"):
            parser = script_parser
        else:
            continue
        try:
            parser.parse_args(words[2:])
        except SystemExit as exc:
            pytest.fail(f"{doc.name}: {shlex.join(words)} does not parse (exit {exc.code})")


def test_install_md_names_the_script_and_shows_the_commands_it_runs():
    assert INSTALL in DOCS
    assert {"scripts/install_skills.py", "template/protocol/ra.py"} <= _framework_paths(INSTALL)
    shown = {" ".join(words[1:3]) for words in _commands(INSTALL)}
    assert "x/template/protocol/ra.py init" in shown
    assert "protocol/ra.py check" in shown
    assert any(words[1].endswith("scripts/install_skills.py") for words in _commands(INSTALL))
