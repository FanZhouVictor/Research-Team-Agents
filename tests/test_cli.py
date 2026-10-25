"""Smoke tests for the 'python protocol/ra.py' command-line entry point."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "template/protocol/ra.py"


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
