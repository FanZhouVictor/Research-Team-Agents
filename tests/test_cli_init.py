"""Tests for 'python protocol/ra.py init', run as a subprocess and through ra.cli.main.

The library behind the command is tested in test_scaffold.py and test_scaffold_refusals.py.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from ra.cli import main

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "template" / "protocol" / "ra.py"


def _ra(*args: str, script: Path = SCRIPT, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    """Run 'python <script> <args>' in cwd; the output is read as UTF-8."""
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=False,
    )


def _init(
    dest: Path, author: str = "Fan <fan@x>", platforms: tuple[str, ...] = ("codex",)
) -> list[str]:
    """The arguments of 'ra init' for dest."""
    return [
        "init", str(dest), "--name", "Smoke Plume", "--person", "Fan", "--git-author", author,
        "--platforms", *platforms, "--role", "PI",
    ]


def test_init_prints_the_path_and_the_new_project_passes_check(tmp_path):
    dest = tmp_path / "p"
    proc = _ra(*_init(dest, platforms=("claude-code", "codex")))
    assert proc.returncode == 0, proc.stderr
    assert (proc.stdout, proc.stderr) == (f"{dest.resolve()}\n", "")
    checked = _ra("check", script=dest / "protocol" / "ra.py", cwd=dest)
    assert (checked.returncode, checked.stdout, checked.stderr) == (0, "check: no findings\n", "")
    project = (dest / "PROJECT.md").read_text(encoding="utf-8")
    assert "| Fan | Fan <fan@x> | claude-code, codex | PI |" in project


def test_init_inside_a_project_is_refused(tmp_path, repo):
    second = tmp_path / "second"
    proc = _ra(*_init(second), script=repo / "protocol" / "ra.py", cwd=repo)
    assert (proc.returncode, proc.stdout) == (1, "")
    assert proc.stderr.startswith("error: run ra init from the framework repository")
    assert not second.exists()


def test_a_refused_value_is_one_error_line_with_exit_1(tmp_path, capsys):
    dest = tmp_path / "p"
    assert main(_init(dest, author="Fan")) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "error: git author must look like 'Name <email>', got 'Fan'\n"
    assert not dest.exists()


def test_a_destination_with_content_is_one_error_line_with_exit_1(tmp_path, capsys):
    dest = tmp_path / "p"
    dest.mkdir()
    (dest / "keep.txt").write_text("keep\n", encoding="utf-8")
    assert main(_init(dest)) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"error: {dest} exists and is not an empty directory\n"


@pytest.mark.skipif(sys.platform == "win32", reason="Windows reports this path as not found")
def test_a_path_through_a_file_is_one_error_line_not_a_traceback(tmp_path):
    # guarded reports any OSError, not only FileExistsError and FileNotFoundError.
    blocker = tmp_path / "notes.txt"
    blocker.write_text("keep\n", encoding="utf-8")
    dest = blocker / "p"
    proc = _ra(*_init(dest))
    assert (proc.returncode, proc.stdout) == (1, "")
    assert proc.stderr == f"error: Not a directory: {dest}\n"
    assert blocker.read_text(encoding="utf-8") == "keep\n"


def test_only_known_platforms_are_accepted(tmp_path, capsys):
    with pytest.raises(SystemExit) as raised:
        main(_init(tmp_path / "p", platforms=("claude-code", "vim")))
    assert raised.value.code == 2
    assert "invalid choice: 'vim'" in capsys.readouterr().err
    assert not (tmp_path / "p").exists()
