"""Tests for ra.digest: reading commit messages back and rendering the what's-new digest.

parse_message and render are tested on their own; commits_since_last runs real git in the
repo fixture ('ra.py digest' is tested in test_cli_digest.py). Hand-written commits without
a [tag] subject are part of the histories here: the digest lists them as untagged ('other')
and never raises.
"""

import subprocess
from datetime import date, datetime
from pathlib import Path

import pytest
from conftest import GitIdentity, _commit_all
from ra.commit import TYPE_TAGS, commit, format_message
from ra.digest import Commit, commits_since_last, parse_message, render
from ra.newfile import new_log, new_question

# The subject of the one commit the repo fixture starts with (the first commit of init_project).
INIT_SUBJECT = "initialise project from RA_Agent template 0.1.0"
SPEC_MESSAGE = (
    "[literature] added Smith 2024 — plume segmentation from GOES imagery\n"
    "\n"
    "Person: Fan\n"
    "Agent: codex\n"
    "Links: literature/smith2024-plume-goes.md, questions/Q-2026-10-25-plume-baselines.md\n"
)


def _git(repo: Path, *args: str) -> str:
    """Run git in repo and return its output, read as UTF-8."""
    done = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return done.stdout


def _c(
    tag: str | None,
    subject: str,
    person: str | None = "Fan",
    agent: str | None = "codex",
    sha: str = "abcdef0123456789",
    day: str = "2026-10-25",
) -> Commit:
    """A Commit as commits_since_last would return it."""
    return Commit(
        sha=sha, date=day, type_tag=tag, subject=subject, person=person, agent=agent, links=[]
    )


# --- the brief's tests -------------------------------------------------------------------


def test_since_last_commit_and_untagged_tolerated(repo, git_identity):
    git_identity(repo, "Fan", "fan@x")
    p1 = new_log(repo, "fan", "codex", datetime(2026, 10, 25, 9, 0))
    commit(repo, [p1], "log", "s1", "Fan", "codex", [])
    git_identity(repo, "Lee", "lee@x")
    p2 = new_question(repo, "a", "t", "Lee", "claude-code", date(2026, 10, 25))
    commit(repo, [p2], "question", "added A", "Lee", "claude-code", ["questions/Q-2026-10-25-a.md"])
    (repo / "PROJECT.md").write_text(
        (repo / "PROJECT.md").read_text(encoding="utf-8") + "\n", encoding="utf-8"
    )
    _commit_all(repo, "fixed typo by hand")
    cs = commits_since_last(repo, "Fan")
    assert [c.type_tag for c in cs] == [None, "question"]  # newest first
    assert "other" in render(cs)


def test_fallback_when_person_has_no_commits(repo):
    for i in range(25):
        _commit_all(repo, f"[log] s{i}")
    assert len(commits_since_last(repo, "Nobody")) == 20


# --- parse_message -----------------------------------------------------------------------


def test_parse_message_reads_the_spec_example():
    assert parse_message(SPEC_MESSAGE) == Commit(
        sha="",
        date="",
        type_tag="literature",
        subject="added Smith 2024 — plume segmentation from GOES imagery",
        person="Fan",
        agent="codex",
        links=["literature/smith2024-plume-goes.md", "questions/Q-2026-10-25-plume-baselines.md"],
    )


@pytest.mark.parametrize("tag", TYPE_TAGS)
def test_parse_message_reads_back_what_format_message_wrote(tag):
    links = ["a.md", "questions/Q-2026-10-25-x.md"]
    c = parse_message(format_message(tag, "s — t", "Fan Zhou", "claude-code", links))
    assert (c.type_tag, c.subject, c.person, c.agent, c.links) == (
        tag, "s — t", "Fan Zhou", "claude-code", links,
    )


def test_parse_message_reads_a_message_without_links():
    c = parse_message(format_message("log", "s", "Fan", "codex", []))
    assert (c.person, c.agent, c.links) == ("Fan", "codex", [])


@pytest.mark.parametrize(
    ("message", "tag", "subject"),
    [
        ("[log] s", "log", "s"),
        ("[log]   padded   ", "log", "padded"),
        ("\n  \n[question] after blank lines\n", "question", "after blank lines"),
        ("[experiment] x", None, "[experiment] x"),  # not a type tag
        ("[Log] s", None, "[Log] s"),  # tags are lower case
        ("[log]x", None, "[log]x"),  # the tag is followed by a space
        ("[log]", None, "[log]"),
        ("[log s", None, "[log s"),
        ("fixed typo by hand", None, "fixed typo by hand"),
        ("  hand written  \n", None, "hand written"),
        (
            "Merge branch 'main' of github.com:lab/plume",
            None,
            "Merge branch 'main' of github.com:lab/plume",
        ),
        ("", None, ""),
        (" \n\t\n", None, ""),
    ],
)
def test_parse_message_subject_line(message, tag, subject):
    c = parse_message(message)
    assert (c.type_tag, c.subject) == (tag, subject)
    assert (c.sha, c.date) == ("", "")


def test_parse_message_without_trailers_has_no_person_agent_or_links():
    assert parse_message("[log] s\n") == Commit("", "", "log", "s", None, None, [])


def test_parse_message_keeps_the_trailers_of_an_untagged_subject():
    c = parse_message("[experiment] x\n\nPerson: Fan\nAgent: codex\nLinks: a.md\n")
    assert (c.type_tag, c.subject) == (None, "[experiment] x")
    assert (c.person, c.agent, c.links) == ("Fan", "codex", ["a.md"])


@pytest.mark.parametrize(
    ("line", "links"),
    [
        ("Links: a.md", ["a.md"]),
        ("Links: a.md, b/c.md", ["a.md", "b/c.md"]),
        ("Links:a.md,b/c.md", ["a.md", "b/c.md"]),
        ("Links: a.md,, ,b.md,", ["a.md", "b.md"]),
        ("Links:", []),
        ("Links: ", []),
        ("Links:  , ", []),
    ],
)
def test_parse_message_splits_links_on_commas(line, links):
    assert parse_message(f"[log] s\n\nPerson: Fan\nAgent: codex\n{line}\n").links == links


def test_parse_message_takes_the_first_occurrence_of_each_trailer():
    c = parse_message(
        "[log] s\n\nPerson: Fan\nPerson: Lee\nAgent: codex\nAgent: claude-code\n"
        "Links: a.md\nLinks: b.md\n"
    )
    assert (c.person, c.agent, c.links) == ("Fan", "codex", ["a.md"])


def test_parse_message_finds_trailers_after_a_free_text_body():
    c = parse_message(
        "[log] s\n\nWhat happened in\nthis session.\n\nPerson: Fan\nAgent: codex\nLinks: a.md\n"
    )
    assert (c.subject, c.person, c.agent, c.links) == ("s", "Fan", "codex", ["a.md"])


def test_parse_message_reads_windows_line_endings():
    c = parse_message("[log] s\r\n\r\nPerson: Fan\r\nAgent: codex\r\nLinks: a.md, b.md\r\n")
    assert c == Commit("", "", "log", "s", "Fan", "codex", ["a.md", "b.md"])


def test_parse_message_treats_an_empty_person_or_agent_as_missing():
    c = parse_message("[log] s\n\nPerson:\nAgent:   \nLinks:\n")
    assert (c.person, c.agent, c.links) == (None, None, [])


# --- commits_since_last ------------------------------------------------------------------


def test_commits_carry_sha_date_and_the_parsed_message(repo, monkeypatch):
    monkeypatch.setenv("GIT_AUTHOR_DATE", "2026-10-25T23:30:00+0000")
    path = new_question(repo, "x", "t", "Lee", "claude-code", date(2026, 10, 25))
    link = "questions/Q-2026-10-25-x.md"
    sha = commit(repo, [path], "question", "added X", "Lee", "claude-code", [link])
    commits = commits_since_last(repo, "Nobody")
    assert commits[:-1] == [
        Commit(
            sha=sha, date="2026-10-25", type_tag="question", subject="added X",
            person="Lee", agent="claude-code", links=[link],
        )
    ]
    assert (commits[-1].type_tag, commits[-1].subject) == ("protocol", INIT_SUBJECT)


def test_nothing_new_when_the_persons_own_commit_is_the_latest(repo):
    _commit_all(repo, "[log] s")
    assert commits_since_last(repo, "Fan") == []


def test_the_boundary_is_the_persons_latest_commit(repo, git_identity):
    _commit_all(repo, "[log] fan-1")
    git_identity(repo, "Lee", "lee@x")
    _commit_all(repo, "[log] lee-1")
    git_identity(repo, "Fan", "fan@x")
    _commit_all(repo, "[log] fan-2")
    git_identity(repo, "Lee", "lee@x")
    _commit_all(repo, "[question] lee-2")
    _commit_all(repo, "[status] lee-3")
    assert [c.subject for c in commits_since_last(repo, "Fan")] == ["lee-3", "lee-2"]
    assert commits_since_last(repo, "Lee") == []


def test_the_fallback_caps_only_a_person_without_commits(repo, git_identity):
    _commit_all(repo, "[log] fan")
    git_identity(repo, "Lee", "lee@x")
    for i in range(5):
        _commit_all(repo, f"[log] lee-{i}")
    assert len(commits_since_last(repo, "Fan", fallback=2)) == 5
    assert [c.subject for c in commits_since_last(repo, "Nobody", fallback=2)] == [
        "lee-4", "lee-3",
    ]


def test_a_repository_without_commits_has_an_empty_digest(tmp_path):
    unborn = tmp_path / "unborn"  # the repo fixture already has its first commit
    unborn.mkdir()
    _git(unborn, "init", "-q", "-b", "main")
    assert commits_since_last(unborn, "Fan") == []


def test_a_directory_that_is_not_a_repository_raises(tmp_path, monkeypatch):
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    with pytest.raises(subprocess.CalledProcessError):
        commits_since_last(plain, "Fan")


def test_a_git_error_other_than_no_commits_propagates(repo):
    _commit_all(repo, "[log] s")
    with pytest.raises(subprocess.CalledProcessError):
        commits_since_last(repo, "\\(")  # git reads --author as a regular expression


@pytest.mark.parametrize("person", ["", "  ", "\t"])
def test_a_blank_person_is_rejected(repo, person):
    _commit_all(repo, "[log] s")  # an empty --author would match the newest commit
    with pytest.raises(ValueError):
        commits_since_last(repo, person)


def test_hand_written_commits_never_break_the_digest(repo):
    _commit_all(repo, "[log] base")
    _commit_all(repo, "Merge branch 'main' of github.com:lab/plume")
    _commit_all(repo, "[experiment] unknown tag\n\nfree text body")
    _commit_all(repo, "[log] s\r\n\r\nPerson: Fan\r\nAgent: codex\r\nLinks:\r\n")
    subprocess.run(
        ["git", "commit", "-q", "--allow-empty", "--allow-empty-message", "-m", ""],
        cwd=repo, check=True,
    )
    cs = commits_since_last(repo, "Nobody")
    assert [(c.type_tag, c.subject) for c in cs] == [
        (None, ""),
        ("log", "s"),
        (None, "[experiment] unknown tag"),
        (None, "Merge branch 'main' of github.com:lab/plume"),
        ("log", "base"),
        ("protocol", INIT_SUBJECT),
    ]
    text = render(cs)
    assert "## log (2)" in text and "## other (3)" in text


def test_separator_characters_in_a_message_do_not_break_the_other_commits(repo):
    _commit_all(repo, "[log] before")
    _commit_all(repo, "stray \x1e record and \x1f field \x1e\x1f separators")
    _commit_all(repo, "[log] after")
    cs = commits_since_last(repo, "Nobody")
    assert len(cs) == 4  # the three above and the scaffold's first commit
    assert (cs[0].type_tag, cs[0].subject) == ("log", "after")
    assert (cs[-2].type_tag, cs[-2].subject) == ("log", "before")


def _lee_branch_merged_by_fan(repo: Path, git_identity: GitIdentity) -> None:
    """Fan commits; Lee commits a [question] on a branch; Fan commits again and merges it.

    The merge is a real two-parent commit authored by Fan, as 'git pull' makes it when the
    remote has diverged.
    """
    _commit_all(repo, "[log] base")
    _git(repo, "checkout", "-q", "-b", "lee")
    git_identity(repo, "Lee", "lee@x")
    _commit_all(
        repo, "[question] added A\n\nPerson: Lee\nAgent: claude-code\nLinks: questions/Q-x.md"
    )
    _git(repo, "checkout", "-q", "main")
    git_identity(repo, "Fan", "fan@x")
    _commit_all(repo, "[log] fan-2")
    _git(repo, "merge", "-q", "--no-ff", "-m", "Merge branch 'lee'", "lee")
    assert len(_git(repo, "rev-list", "--parents", "-n", "1", "HEAD").split()) == 3  # 2 parents


def test_a_merge_commit_is_not_the_boundary_and_is_not_listed(repo, git_identity):
    # Fan's newest commit is the merge; the digest must start at fan-2 and show Lee's commit.
    _lee_branch_merged_by_fan(repo, git_identity)
    cs = commits_since_last(repo, "Fan")
    assert [(c.type_tag, c.subject, c.person) for c in cs] == [("question", "added A", "Lee")]


def test_the_digest_of_the_other_person_skips_the_merge_too(repo, git_identity):
    _lee_branch_merged_by_fan(repo, git_identity)
    assert [c.subject for c in commits_since_last(repo, "Lee")] == ["fan-2"]


def test_merge_commits_are_left_out_of_the_fallback_and_do_not_count_against_its_limit(
    repo, git_identity
):
    _lee_branch_merged_by_fan(repo, git_identity)
    listed = {c.subject for c in commits_since_last(repo, "Nobody")}
    assert listed == {INIT_SUBJECT, "base", "added A", "fan-2"}
    two = commits_since_last(repo, "Nobody", fallback=2)
    assert len(two) == 2 and not any(c.subject.startswith("Merge") for c in two)


def test_a_user_setting_for_the_log_output_encoding_does_not_garble_the_digest(repo):
    _git(repo, "config", "i18n.logOutputEncoding", "ISO-8859-1")
    _commit_all(repo, "[log] café ñ")
    assert [c.subject for c in commits_since_last(repo, "Nobody")] == ["café ñ", INIT_SUBJECT]


# --- render ------------------------------------------------------------------------------


def test_render_of_nothing_says_so():
    assert render([]) == "No new commits.\n"


def test_render_groups_by_type_with_counts_and_untagged_last():
    commits = [
        _c(None, "fixed typo by hand", None, None, sha="1111111aaaa", day="2026-10-27"),
        _c("log", "s2", "Lee", "claude-code", sha="2222222bbbb", day="2026-10-26"),
        _c("literature", "added Smith 2024", sha="3333333cccc"),
        _c("log", "s1", sha="4444444dddd", day="2026-10-24"),
    ]
    assert render(commits) == (
        "## literature (1)\n"
        "- 2026-10-25 3333333 added Smith 2024 — Fan/codex\n"
        "\n"
        "## log (2)\n"
        "- 2026-10-26 2222222 s2 — Lee/claude-code\n"
        "- 2026-10-24 4444444 s1 — Fan/codex\n"
        "\n"
        "## other (1)\n"
        "- 2026-10-27 1111111 fixed typo by hand — ?/?\n"
    )


def test_render_orders_the_groups_by_type_tag_then_other():
    commits = [_c(None, "x")] + [_c(tag, "x") for tag in reversed(TYPE_TAGS)]
    headings = [line for line in render(commits).splitlines() if line.startswith("## ")]
    assert headings == [f"## {tag} (1)" for tag in TYPE_TAGS] + ["## other (1)"]


def test_render_uses_a_question_mark_for_a_missing_person_or_agent():
    text = render([_c("log", "s", None, "codex"), _c("log", "t", "Fan", None)])
    assert "- 2026-10-25 abcdef0 s — ?/codex\n" in text
    assert "- 2026-10-25 abcdef0 t — Fan/?\n" in text


def test_render_lists_a_commit_with_an_unknown_tag_under_other():
    assert render([_c("experiment", "x")]).startswith("## other (1)\n")
