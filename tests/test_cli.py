"""Smoke tests for the command line: the entry script as a subprocess, ra.cli.main in process."""

import argparse
import subprocess
import sys
from pathlib import Path

import pytest
from ra.cli import main
from ra.cli_common import guarded

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


COMMIT = [
    "commit", "--type", "log", "--subject", "end of session", "--person", "Fan", "--agent", "codex",
]


def test_main_runs_commit_in_the_current_directory(repo, monkeypatch, capsys):
    monkeypatch.chdir(repo)
    (repo / "log" / "a.md").write_text("a\n", encoding="utf-8")
    assert main([*COMMIT, "--links", "log/a.md", "--", "log/a.md"]) == 0
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout
    captured = capsys.readouterr()
    assert captured.out == head and captured.err == ""


def test_main_reports_a_git_failure_as_one_error_line_with_exit_1(repo, monkeypatch, capsys):
    monkeypatch.chdir(repo)
    monkeypatch.setenv("LC_ALL", "C")  # git's wording is translated otherwise
    assert main([*COMMIT, "--", "missing.md"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "error: git add -- missing.md failed: "
        "fatal: pathspec 'missing.md' did not match any files\n"
    )


def test_main_runs_digest_in_the_current_directory(repo, monkeypatch, capsys):
    monkeypatch.chdir(repo)
    assert main(["digest", "--person", "Fan"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "No new commits.\n" and captured.err == ""


# --- guarded: a failed command line tool becomes one error line ----------------------------


def _failure(
    cmd: list[str], stdout: bytes | str, stderr: bytes | str, code: int = 128
) -> subprocess.CalledProcessError:
    """The error subprocess.run(check=True) raises when cmd exits with code."""
    return subprocess.CalledProcessError(code, cmd, output=stdout, stderr=stderr)


@pytest.mark.parametrize(
    ("error", "line"),
    [
        (  # bytes, as subprocess returns them without text mode
            _failure(["git", "add", "--", "x.md"], b"", b"fatal: pathspec 'x.md' did not match\n"),
            "error: git add -- x.md failed: fatal: pathspec 'x.md' did not match\n",
        ),
        (  # text, as a caller that used text=True gets them
            _failure(["git", "add"], "", "fatal: bad\n"),
            "error: git add failed: fatal: bad\n",
        ),
        (  # several lines become one
            _failure(["git", "commit", "-F", "-"], b"", b"first\n\nsecond\n"),
            "error: git commit -F - failed: first second\n",
        ),
        (  # git commit explains 'nothing to commit' on stdout and leaves stderr empty
            _failure(
                ["git", "commit", "-F", "-"],
                b"On branch main\nnothing to commit, working tree clean\n",
                b"",
                1,
            ),
            "error: git commit -F - failed: On branch main nothing to commit, working tree clean\n",
        ),
        (  # global -c settings are not repeated
            _failure(["git", "-c", "core.quotepath=false", "log", "-n", "1"], b"", b"fatal: x\n"),
            "error: git log -n 1 failed: fatal: x\n",
        ),
        (  # no output at all: the exit status is all there is
            _failure(["git", "commit", "-F", "-"], b"", b"", 1),
            "error: git commit -F - failed: exit status 1\n",
        ),
        (  # bytes that are not UTF-8 are replaced, not raised
            _failure(["git", "log"], b"", b"fatal: \xff\n"),
            "error: git log failed: fatal: " + chr(0xFFFD) + "\n",
        ),
    ],
    ids=[
        "bytes", "text", "several-lines", "stdout-fallback", "global-settings", "no-output",
        "bad-utf8",
    ],
)
def test_guarded_turns_a_failed_git_command_into_one_error_line(error, line, capsys):
    @guarded
    def handler(args: argparse.Namespace) -> int:
        raise error

    assert handler(argparse.Namespace()) == 1
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", line)


def test_guarded_still_raises_unexpected_exceptions():
    @guarded
    def handler(args: argparse.Namespace) -> int:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        handler(argparse.Namespace())
