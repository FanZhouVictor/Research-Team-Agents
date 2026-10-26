"""Tests for the example project that examples/build_smoke_plume.py builds (ruling R13).

The project is built once per session into a temporary directory, never into the git-ignored
examples/smoke-plume, and read back through the ra package, as later tasks and the pilot do.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest
from build_smoke_plume import build
from ra.check import run_checks
from ra.digest import commits_since_last, parse_message, render
from ra.frontmatter import parse
from ra.knowledge import parse_facts
from ra.literature import parse_claims

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "examples" / "build_smoke_plume.py"
AUTHORS = {"Fan": "Fan <fan@x>", "Lee": "Lee <lee@x>"}
LEE = "Lee · codex · 2026-10-27"
# Guidance lines of the templates and of PROJECT.md that a filled-in file must not keep.
GUIDANCE = (
    "≤150 words", "One or two lines tying", "Why this matters to the project.",
    "<two to five lines>", "<e.g. literature review",
)
_HEADING = re.compile(r"^## (.+)$", re.MULTILINE)


def _git(repo: Path, *args: str) -> str:
    """The output of 'git <args>' run in repo, read as UTF-8."""
    return subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8",
    ).stdout


def _python(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    """Run this test interpreter with args in cwd; the output is read as UTF-8."""
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=False,
    )


def _sections(body: str) -> dict[str, str]:
    """The '## ' sections of a Markdown body: heading -> its text, stripped."""
    marks = list(_HEADING.finditer(body))
    ends = [mark.start() for mark in marks[1:]] + [len(body)]
    return {mark.group(1): body[mark.end() : end].strip() for mark, end in zip(marks, ends)}


@pytest.fixture(scope="session")
def example_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The example project, built once for the session into a temporary directory."""
    return build(tmp_path_factory.mktemp("example") / "smoke-plume")


def test_example_project_is_clean_and_digestible(example_repo):
    repo = example_repo
    assert run_checks(repo) == []
    assert "literature" in render(commits_since_last(repo, "Lee"))


@pytest.mark.xfail(strict=True, reason="stats arrives in Task 15")
def test_example_stats(example_repo):
    from ra.stats import stats

    assert stats(example_repo)["unverified_claims"] >= 1


def test_builder_is_deterministic(example_repo, tmp_path):
    again = build(tmp_path / "smoke-plume")
    assert _git(again, "rev-parse", "HEAD") == _git(example_repo, "rev-parse", "HEAD")


def test_builder_refuses_non_empty_dest_without_force(tmp_path):
    dest = tmp_path / "smoke-plume"
    dest.mkdir()
    (dest / "keep.txt").write_text("keep\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        build(dest)
    refused = _python(str(BUILDER), str(dest))
    assert (refused.returncode, refused.stdout) == (1, "")
    assert refused.stderr.startswith("error: ") and "--force" in refused.stderr
    # --force deletes only an earlier build of the example, never other content
    forced = _python(str(BUILDER), str(dest), "--force")
    assert (forced.returncode, forced.stdout) == (1, "")
    assert forced.stderr.startswith("error: refusing to delete ")
    assert [entry.name for entry in dest.iterdir()] == ["keep.txt"]


def test_the_script_builds_a_project_that_passes_ra_check(tmp_path):
    dest = tmp_path / "smoke-plume"
    built = _python(str(BUILDER), str(dest))
    assert (built.returncode, built.stderr) == (0, "")
    assert Path(built.stdout.strip()) == dest.resolve()
    checked = _python("protocol/ra.py", "check", cwd=dest)
    assert (checked.returncode, checked.stdout, checked.stderr) == (0, "check: no findings\n", "")
    head = _git(dest, "rev-parse", "HEAD")
    rebuilt = _python(str(BUILDER), str(dest), "--force")
    assert (rebuilt.returncode, rebuilt.stderr) == (0, "")
    assert _git(dest, "rev-parse", "HEAD") == head


def test_core_record_has_two_readers_two_verified_claims_and_one_disputed(example_repo):
    meta, body = parse(example_repo / "literature" / "smith2024-plume-goes.md")
    assert meta["relevance"] == "core"
    readers = [(r["person"], r["agent"], r["date"], r["read"]) for r in meta["readers"]]
    assert readers == [
        ("Fan", "claude-code", "2026-10-25", "full-text"),
        ("Lee", "codex", "2026-10-27", "full-text"),
    ]
    claims = parse_claims(body)
    assert len(claims) == 3
    assert all(c.where and c.kind and c.basis for c in claims)
    assert {c.by for c in claims} == {"Fan · claude-code · 2026-10-25"}
    assert [c.verified_by for c in claims] == [[LEE], [LEE], []]
    assert [len(c.disputed_by) for c in claims] == [0, 0, 1]
    assert claims[2].disputed_by[0].startswith(f"{LEE} — ")
    assert "\nrevised: 2026-10-27 Lee/codex — " in _sections(body)["Summary"]
    assert len(_sections(body)["Notes"].splitlines()) == 2  # one line per reader


def test_supporting_claims_are_unverified_and_the_rejected_paper_has_none(example_repo):
    literature = example_repo / "literature"
    assert sorted(path.name for path in literature.glob("*.md")) == [
        "brown2022-cloud-masks.md", "jones2023-plume-unet.md", "smith2024-plume-goes.md",
    ]
    assert len(list((literature / "pdf").glob("*.pdf"))) == 3
    jones, jones_body = parse(literature / "jones2023-plume-unet.md")
    brown, brown_body = parse(literature / "brown2022-cloud-masks.md")
    assert (jones["relevance"], brown["relevance"]) == ("supporting", "not-useful")
    assert len(jones["readers"]) == 1
    claims = parse_claims(jones_body)
    assert len(claims) == 2
    assert all(c.where and not c.verified_by and not c.disputed_by for c in claims)
    assert parse_claims(brown_body) == []
    assert _sections(brown_body)["Why it matters here"]  # the reason it was rejected


def test_claims_bear_only_on_questions_that_existed_when_the_record_was_added(example_repo):
    for path in (example_repo / "literature").glob("*.md"):
        rel = f"literature/{path.name}"
        added = _git(example_repo, "log", "--diff-filter=A", "--format=%H", "--", rel).split()[-1]
        tree = set(_git(example_repo, "ls-tree", "--name-only", added, "questions/").split())
        for claim in parse_claims(parse(path)[1]):
            assert claim.bears_on, (rel, claim.text)
            assert all(f"questions/{qid}.md" in tree for qid in claim.bears_on), (rel, claim.text)


def test_goes_abi_holds_two_facts_in_conflict(example_repo):
    knowledge = example_repo / "knowledge"
    facts = parse_facts((knowledge / "goes-abi.md").read_text(encoding="utf-8"))
    assert [(f.citekey, f.where, f.by, f.approved, f.status) for f in facts] == [
        ("smith2024-plume-goes", "§2.1 p.3", "Fan/claude-code 2026-10-25", "Fan",
         "CONFLICT with line below"),
        ("jones2023-plume-unet", "Table 1", "Lee/codex 2026-10-27", "Lee",
         "CONFLICT with line above"),
    ]
    registry = (knowledge / "README.md").read_text(encoding="utf-8").splitlines()
    assert "- goes-abi — GOES-16 ABI instrument facts" in registry
    added = _git(example_repo, "log", "--diff-filter=A", "--format=%H", "--",
                 "knowledge/goes-abi.md").split()
    assert len(added) == 1  # the registry line lands in the commit of the first fact
    assert _git(example_repo, "show", "--name-only", "--format=", added[0]).split() == [
        "knowledge/README.md", "knowledge/goes-abi.md",
    ]


def test_two_questions_are_open_and_one_is_answered_by_knowledge(example_repo):
    questions = {path.stem: parse(path)[0] for path in (example_repo / "questions").glob("*.md")}
    assert {qid: meta["status"] for qid, meta in questions.items()} == {
        "Q-2026-10-25-plume-baselines": "open",
        "Q-2026-10-25-abi-band-choice": "open",
        "Q-2026-10-26-dataset-size": "answered",
    }
    answered = questions["Q-2026-10-26-dataset-size"]
    assert (answered["answered-by"], answered["closed-by"]) == (
        "knowledge/goes-abi.md", "Fan · 2026-10-27",
    )
    assert all(meta["approved-by"] for meta in questions.values())
    subjects = _git(example_repo, "log", "--format=%s").splitlines()
    assert "[question] closed Q-2026-10-26-dataset-size" in subjects


def test_one_decision_is_accepted_and_one_pair_is_superseded(example_repo):
    decisions = example_repo / "decisions"
    metric = parse(decisions / "D-2026-10-26-eval-metric.md")[0]
    old = parse(decisions / "D-2026-10-25-loss-function.md")[0]
    new = parse(decisions / "D-2026-10-28-loss-function-v2.md")[0]
    assert (metric["status"], metric["accepted-by"]) == ("accepted", "Fan · 2026-10-26")
    assert (old["status"], old["superseded-by"]) == ("superseded", "D-2026-10-28-loss-function-v2")
    assert (new["status"], new["supersedes"]) == ("accepted", "D-2026-10-25-loss-function")
    # the old file's one edit is made in the commit that adds the new file
    last = _git(example_repo, "log", "-n", "1", "--format=%H", "--",
                "decisions/D-2026-10-25-loss-function.md").strip()
    assert _git(example_repo, "show", "--name-only", "--format=", last).split() == [
        "decisions/D-2026-10-25-loss-function.md", "decisions/D-2026-10-28-loss-function-v2.md",
    ]


def test_three_logs_by_two_people_on_both_platforms(example_repo):
    logs = {path.name: parse(path)[0] for path in (example_repo / "log").glob("*.md")}
    assert {name: (m["person"], m["agent"], m["session"]) for name, m in logs.items()} == {
        "2026-10-25-fan-claude-code-1432.md": ("Fan", "claude-code", "14:32–16:05"),
        "2026-10-27-lee-codex-0910.md": ("Lee", "codex", "09:10–11:40"),
        "2026-10-28-fan-codex-1000.md": ("Fan", "codex", "10:00–10:45"),
    }


def test_every_commit_is_structured_and_made_by_the_person_it_names(example_repo):
    log = _git(example_repo, "log", "--format=%an <%ae>%x1f%B%x1e")
    records = [record.split("\x1f") for record in log.split("\x1e") if record.strip()]
    commits = [(author.strip(), parse_message(message)) for author, message in records]
    assert all(c.type_tag and c.agent in ("claude-code", "codex") and c.links for _, c in commits)
    assert all(author == AUTHORS[c.person] for author, c in commits)
    assert commits[0][0] == AUTHORS["Fan"]  # the newest commit
    assert _git(example_repo, "status", "--porcelain") == ""


def test_template_guidance_is_replaced_and_every_section_is_filled(example_repo):
    for folder in ("questions", "decisions", "literature", "log"):
        for path in (example_repo / folder).glob("*.md"):
            body = parse(path)[1]
            assert [text for text in GUIDANCE if text in body] == [], path.name
            if folder in ("decisions", "log"):
                assert all(_sections(body).values()), path.name
    project = (example_repo / "PROJECT.md").read_text(encoding="utf-8")
    assert [text for text in GUIDANCE if text in project] == []
    assert "| Lee | Lee <lee@x> | codex | PhD student |" in project.splitlines()
    assert 3 <= len(_sections(project)["Current status"].splitlines()) <= 8
