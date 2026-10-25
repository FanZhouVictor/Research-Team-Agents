"""Smoke tests for the command line: the entry script as a subprocess, ra.cli.main in process."""

import subprocess
import sys
from pathlib import Path

import pytest
from ra.cli import main

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "template/protocol/ra.py"

NEW_QUESTION = [
    "new", "question", "--slug", "x", "--title", "t",
    "--person", "Fan", "--agent", "codex", "--date", "2026-10-25",
]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_help_prints_usage_and_exits_0():
    proc = _run("--help")
    assert proc.returncode == 0
    assert "usage" in proc.stdout.lower()


def test_no_command_prints_usage_and_exits_2():
    proc = _run()
    assert proc.returncode == 2
    assert "usage" in proc.stderr.lower()


# --- ra.cli.main, called in this process --------------------------------------------------


def test_main_help_prints_usage_and_exits_0(capsys):
    with pytest.raises(SystemExit) as raised:
        main(["--help"])
    assert raised.value.code == 0
    assert "usage" in capsys.readouterr().out.lower()


def test_main_without_a_command_prints_usage_and_returns_2(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err.lower()


def test_main_runs_new_in_the_current_directory(repo, monkeypatch, capsys):
    monkeypatch.chdir(repo)
    assert main(NEW_QUESTION) == 0
    captured = capsys.readouterr()
    assert captured.out == "questions/Q-2026-10-25-x.md\n" and captured.err == ""
    assert (repo/"questions"/"Q-2026-10-25-x.md").is_file()


def test_main_reports_expected_failures_as_error_lines_with_exit_1(repo, monkeypatch, capsys):
    monkeypatch.chdir(repo)
    assert main(NEW_QUESTION) == 0
    capsys.readouterr()
    assert main(NEW_QUESTION) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "error: questions/Q-2026-10-25-x.md already exists\n"
