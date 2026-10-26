"""Tests for DECISION_EDITED, the one rule of ra.check that reads git history.

The other rules of ra.check are tested in test_check.py.
"""

import logging
import subprocess
from pathlib import Path

from conftest import _commit_all, _decision
from ra.check import Finding, decision_edited_in_place, run_checks
from ra.frontmatter import parse, write


def _accepted(repo: Path) -> Path:
    """The brief's setup: a decision committed as proposed, then accepted in a second commit."""
    p = _decision(repo, "eval-metric", status="proposed")
    _commit_all(repo, "[decision] proposed")
    m, b = parse(p)
    m["status"] = "accepted"
    m["accepted-by"] = "Fan · 2026-10-26"
    write(p, m, b)
    _commit_all(repo, "[decision] accepted")
    return p


# --- the brief's tests -------------------------------------------------------------------


def test_accepted_decision_body_edit_flagged(repo):
    p = _decision(repo, "eval-metric", status="proposed")
    _commit_all(repo, "[decision] proposed")
    m, b = parse(p)
    m["status"] = "accepted"
    m["accepted-by"] = "Fan · 2026-10-26"
    write(p, m, b)
    _commit_all(repo, "[decision] accepted")
    m, b = parse(p)
    write(p, m, b + "\nchanged rationale\n")
    _commit_all(repo, "oops")
    assert "DECISION_EDITED" in {f.code for f in run_checks(repo)}


def test_superseded_by_edit_allowed(repo):
    p = _accepted(repo)
    m, b = parse(p)
    m["superseded-by"] = "D-2026-11-01-new-metric"
    m["status"] = "superseded"
    write(p, m, b)
    _commit_all(repo, "[decision] superseded")
    assert "DECISION_EDITED" not in {f.code for f in run_checks(repo)}
    assert decision_edited_in_place(repo, p) is False


# --- more cases --------------------------------------------------------------------------


def test_uncommitted_edit_of_an_accepted_decision_is_flagged(repo, monkeypatch):
    p = _accepted(repo)
    assert decision_edited_in_place(repo, p) is False
    m, b = parse(p)
    heading = "## Rationale and evidence\n"
    write(p, m, b.replace(heading, heading + "New reason.\n"))
    assert decision_edited_in_place(repo, p) is True
    # A relative path is relative to repo, wherever the process runs.
    monkeypatch.chdir(repo / "decisions")
    assert decision_edited_in_place(repo, p.relative_to(repo)) is True
    assert run_checks(repo) == [
        Finding("DECISION_EDITED", Path("decisions/D-2026-10-25-eval-metric.md"),
                "edited after acceptance: only status: and superseded-by: may change")
    ]


def test_proposed_decision_may_be_edited_freely(repo):
    p = _decision(repo, "eval-metric", status="proposed")
    _commit_all(repo, "[decision] proposed")
    m, b = parse(p)
    m["title"] = "Use mIoU"
    write(p, m, b + "More rationale.\n")
    _commit_all(repo, "[decision] revised")
    write(p, m, b + "Even more.\n")
    assert run_checks(repo) == []


def test_removing_a_rule_line_from_an_accepted_decision_is_an_edit(repo):
    # The diff line for a removed '---' line is '----': it must not pass for a file header.
    p = _decision(repo, "eval-metric", status="accepted")
    m, b = parse(p)
    write(p, m, b + "\n---\n")
    _commit_all(repo, "[decision] accepted")
    write(p, m, b + "\n")
    assert decision_edited_in_place(repo, p) is True


def test_outside_git_the_decision_check_is_skipped_with_one_warning(tmp_path, caplog):
    plain = tmp_path / "plain"
    (plain / "decisions").mkdir(parents=True)
    _decision(plain, "a", status="accepted")
    _decision(plain, "b", status="superseded")
    with caplog.at_level(logging.WARNING, logger="ra.check"):
        assert run_checks(plain) == []
    assert [record.levelname for record in caplog.records] == ["WARNING"]
    assert "not a git repository" in caplog.records[0].getMessage()


def test_accepted_decision_before_the_first_commit_does_not_crash(tmp_path, caplog):
    unborn = tmp_path / "unborn"  # the repo fixture already has its first commit
    (unborn / "decisions").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=unborn, check=True)
    _decision(unborn, "eval-metric", status="accepted")
    with caplog.at_level(logging.WARNING, logger="ra.check"):
        assert run_checks(unborn) == []
    assert caplog.records and {record.levelname for record in caplog.records} == {"WARNING"}
