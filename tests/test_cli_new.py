"""Tests for 'python protocol/ra.py new <kind>', run as a subprocess inside a project repo."""

import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import pytest
from ra.frontmatter import parse

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "template" / "protocol" / "ra.py"

QUESTION = [
    "new", "question", "--slug", "plume-baselines", "--title", "What are the strongest baselines?",
    "--person", "Fan", "--agent", "claude-code", "--date", "2026-10-25",
]
QUESTION_PATH = "questions/Q-2026-10-25-plume-baselines.md"


def _ra(
    cwd: Path, *args: str, script: Path = SCRIPT, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run 'python <script> <args>' with cwd as the working directory; its output is read as UTF-8."""
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _literature(paper: Path, *extra: str) -> list[str]:
    """Arguments of 'new literature' with the required flags, then extra flags."""
    return [
        "new", "literature", "--citekey", "smith2024-plume-goes", "--pdf", str(paper),
        "--person", "Fan", "--agent", "codex", *extra,
    ]


def test_new_question_prints_the_path_and_creates_the_file(repo):
    proc = _ra(repo, *QUESTION)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == QUESTION_PATH
    assert proc.stderr == ""
    meta, _ = parse(repo/QUESTION_PATH)
    assert meta["id"] == "Q-2026-10-25-plume-baselines"
    assert meta["title"] == "What are the strongest baselines?"
    assert meta["status"] == "open"
    assert meta["proposed-by"] == {"person": "Fan", "agent": "claude-code", "date": "2026-10-25"}


def test_new_question_date_defaults_to_today(repo):
    before = date.today()
    proc = _ra(repo, "new", "question", "--slug", "x", "--title", "t",
               "--person", "Fan", "--agent", "codex")
    after = date.today()
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() in {f"questions/Q-{d.isoformat()}-x.md" for d in (before, after)}


def test_new_decision_collects_repeated_and_multi_value_links(repo):
    proc = _ra(
        repo, "new", "decision", "--slug", "eval-metric", "--title", "Use mIoU",
        "--person", "Fan", "--agent", "codex", "--date", "2026-10-25",
        "--link", "Q-2026-10-25-plume-baselines", "--link", "literature/a.md", "decisions/D-x.md",
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "decisions/D-2026-10-25-eval-metric.md"
    meta, _ = parse(repo/proc.stdout.strip())
    assert meta["status"] == "proposed"
    assert meta["links"] == ["Q-2026-10-25-plume-baselines", "literature/a.md", "decisions/D-x.md"]


def test_new_decision_without_links_writes_an_empty_list(repo):
    proc = _ra(repo, "new", "decision", "--slug", "x", "--title", "t",
               "--person", "Fan", "--agent", "codex")
    assert proc.returncode == 0, proc.stderr
    meta, _ = parse(repo/proc.stdout.strip())
    assert meta["links"] == []


def test_new_literature_with_every_flag(repo, paper):
    proc = _ra(
        repo,
        *_literature(
            paper, "--date", "2026-10-25", "--title", "Mapping smoke at 3.9 µm",
            "--year", "2024", "--authors", "Smith J; 张三 ;Lee K",
            "--venue", "Remote Sensing of Environment", "--doi", "10.1016/j.rse.2024.113",
            "--arxiv", "2401.10250", "--relevance", "core",
            "--bears-on", "Q-2026-10-25-a", "Q-2026-10-25-b",
        ),
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "literature/smith2024-plume-goes.md"
    meta, _ = parse(repo/"literature"/"smith2024-plume-goes.md")
    assert meta["title"] == "Mapping smoke at 3.9 µm" and meta["year"] == 2024
    assert meta["authors"] == ["Smith J", "张三", "Lee K"]
    assert meta["venue"] == "Remote Sensing of Environment"
    assert meta["doi"] == "10.1016/j.rse.2024.113" and meta["arxiv"] == "2401.10250"
    assert meta["relevance"] == "core"
    assert meta["bears-on"] == ["Q-2026-10-25-a", "Q-2026-10-25-b"]
    assert meta["pdf"] == "literature/pdf/smith2024-plume-goes.pdf"
    assert meta["readers"] == [
        {"person": "Fan", "agent": "codex", "date": "2026-10-25", "read": "full-text"}
    ]
    copied = repo/"literature"/"pdf"/"smith2024-plume-goes.pdf"
    assert copied.read_bytes() == paper.read_bytes()


def test_new_literature_with_required_flags_only(repo, paper):
    before = date.today()
    proc = _ra(repo, *_literature(Path("..") / paper.name))  # relative to the project root
    after = date.today()
    assert proc.returncode == 0, proc.stderr
    meta, _ = parse(repo/"literature"/"smith2024-plume-goes.md")
    assert meta["readers"][0]["date"] in {d.isoformat() for d in (before, after)}
    assert meta["title"] is None and meta["year"] is None and meta["relevance"] is None
    assert (meta["authors"], meta["bears-on"], meta["related"]) == ([], [], [])


def test_new_log_with_start(repo):
    proc = _ra(repo, "new", "log", "--person", "Fan", "--agent", "codex",
               "--start", "2026-10-25T14:32")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "log/2026-10-25-fan-codex-1432.md"
    meta, _ = parse(repo/proc.stdout.strip())
    assert meta["session"] == "14:32–" and meta["person"] == "Fan" and meta["date"] == "2026-10-25"


def test_new_log_uses_the_slug_of_a_person_with_a_space(repo):
    proc = _ra(repo, "new", "log", "--person", "Fan Zhou", "--agent", "codex",
               "--start", "2026-10-25T14:32")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "log/2026-10-25-fan-zhou-codex-1432.md"
    assert parse(repo/proc.stdout.strip())[0]["person"] == "Fan Zhou"


@pytest.mark.parametrize(
    ("person", "name"),
    [("José", "2026-10-25-josé-codex-1432.md"), ("张三", "2026-10-25-张三-codex-1432.md")],
)
def test_new_log_keeps_the_unicode_letters_of_the_person(repo, person, name):
    proc = _ra(repo, "new", "log", "--person", person, "--agent", "codex",
               "--start", "2026-10-25T14:32")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == f"log/{name}"
    meta, _ = parse(repo/"log"/name)
    assert meta["person"] == person


def test_output_is_utf8_even_when_the_default_output_encoding_cannot_show_the_path(repo):
    # Pipes use a legacy code page on many Windows setups; the file must not be created and
    # then reported as an error because the path could not be printed.
    env = {**os.environ, "PYTHONIOENCODING": "ascii"}
    proc = _ra(repo, "new", "log", "--person", "张三", "--agent", "codex",
               "--start", "2026-10-25T14:32", env=env)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "log/2026-10-25-张三-codex-1432.md"
    assert (repo/"log"/"2026-10-25-张三-codex-1432.md").is_file()


def test_error_messages_are_utf8_even_when_the_default_output_encoding_is_not(repo):
    env = {**os.environ, "PYTHONIOENCODING": "ascii"}
    proc = _ra(repo, "new", "log", "--person", "。。。", "--agent", "codex", env=env)
    assert proc.returncode == 1
    assert "'。。。'" in proc.stderr


def test_new_log_start_defaults_to_now_at_minute_precision(repo):
    before = datetime.now().replace(second=0, microsecond=0)
    proc = _ra(repo, "new", "log", "--person", "Fan", "--agent", "codex")
    after = datetime.now()
    assert proc.returncode == 0, proc.stderr
    match = re.fullmatch(r"log/(\d{4}-\d{2}-\d{2})-fan-codex-(\d{4})\.md", proc.stdout.strip())
    assert match, proc.stdout
    assert before <= datetime.strptime(match[1] + match[2], "%Y-%m-%d%H%M") <= after


def test_new_topic_creates_the_file_and_registers_it(repo):
    proc = _ra(repo, "new", "topic", "--topic", "goes-abi",
               "--scope", "GOES-16 ABI instrument facts")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "knowledge/goes-abi.md"
    topic = (repo/"knowledge"/"goes-abi.md").read_text(encoding="utf-8")
    assert topic == "# goes-abi\nGOES-16 ABI instrument facts\n\n"
    registry = (repo/"knowledge"/"README.md").read_text(encoding="utf-8")
    assert registry.endswith("\n- goes-abi — GOES-16 ABI instrument facts\n")


def test_existing_file_is_an_error_message_not_a_traceback(repo):
    assert _ra(repo, *QUESTION).returncode == 0
    proc = _ra(repo, *QUESTION)
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.strip() == f"error: {QUESTION_PATH} already exists"


@pytest.mark.parametrize(
    "args",
    [
        ["new", "question", "--slug", "Bad Slug", "--title", "t", "--person", "Fan",
         "--agent", "codex"],
        ["new", "question", "--slug", "x", "--title", "t", "--person", "Fan", "--agent", "claude"],
        ["new", "question", "--slug", "x", "--title", "t", "--person", "", "--agent", "codex"],
        ["new", "decision", "--slug", "UPPER", "--title", "t", "--person", "Fan",
         "--agent", "codex"],
        ["new", "question", "--slug", "x", "--title", "  ", "--person", "Fan", "--agent", "codex"],
        ["new", "log", "--person", "###", "--agent", "codex"],
        ["new", "topic", "--topic", "x", "--scope", "two\nlines"],
        ["new", "topic", "--topic", "Bad_Topic", "--scope", "s"],
    ],
    ids=["bad-slug", "bad-agent", "empty-person", "bad-decision-slug", "blank-title",
         "bad-log-person", "multi-line-scope", "bad-topic"],
)
def test_invalid_input_is_an_error_message_with_exit_1(repo, files_of, args):
    before = files_of(repo)
    proc = _ra(repo, *args)
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("error: ") and "Traceback" not in proc.stderr
    assert files_of(repo) == before


def test_missing_pdf_is_an_error_message_with_exit_1(repo, tmp_path):
    proc = _ra(repo, *_literature(tmp_path/"nope.pdf"))
    assert proc.returncode == 1
    assert proc.stderr.startswith("error: ") and "nope.pdf" in proc.stderr
    assert "Traceback" not in proc.stderr
    assert not (repo/"literature"/"smith2024-plume-goes.md").exists()


@pytest.mark.parametrize(
    ("args", "complaint"),
    [
        (["new"], "<kind>"),
        (["new", "paper"], "'paper'"),
        (["new", "question", "--slug", "x"], "--title"),
        ([*QUESTION[:-1], "2026-13-01"], "2026-13-01"),
        ([*QUESTION[:-1], "25/10/2026"], "25/10/2026"),
        (["new", "log", "--person", "Fan", "--agent", "codex", "--start", "14:32"], "14:32"),
        (["new", "log", "--person", "Fan", "--agent", "codex", "--start", "2026-10-25 14:32"],
         "2026-10-25 14:32"),
    ],
    ids=["no-kind", "unknown-kind", "missing-flags", "impossible-date", "bad-date-format",
         "start-without-date", "start-with-space"],
)
def test_usage_errors_exit_2_and_write_nothing(repo, files_of, args, complaint):
    before = files_of(repo)
    proc = _ra(repo, *args)
    assert proc.returncode == 2
    assert "usage" in proc.stderr.lower() and complaint in proc.stderr
    assert files_of(repo) == before


@pytest.mark.parametrize(
    ("extra", "complaint"),
    [(["--relevance", "important"], "'important'"), (["--year", "abc"], "'abc'")],
)
def test_literature_flag_values_are_checked_by_the_parser(repo, paper, extra, complaint):
    proc = _ra(repo, *_literature(paper, *extra))
    assert proc.returncode == 2 and complaint in proc.stderr
    assert not (repo/"literature"/"smith2024-plume-goes.md").exists()


def test_new_help_lists_the_five_kinds(repo):
    proc = _ra(repo, "new", "--help")
    assert proc.returncode == 0
    for kind in ("question", "decision", "literature", "log", "topic"):
        assert kind in proc.stdout


def test_works_as_protocol_ra_py_inside_a_project(repo):
    # The layout of a generated project: protocol/ra.py, protocol/ra/ and protocol/templates/.
    shutil.copytree(SCRIPT.parent, repo/"protocol", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    proc = _ra(repo, *QUESTION, script=Path("protocol/ra.py"))
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == QUESTION_PATH
    _, body = parse(repo/QUESTION_PATH)
    assert "## Context" in body
