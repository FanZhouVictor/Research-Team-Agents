"""Tests for the five template files in template/protocol/templates/ and how newfile uses them."""

import re
from datetime import date
from pathlib import Path

import pytest
from ra import newfile
from ra.frontmatter import parse
from ra.newfile import (
    DECISION_KEYS,
    LITERATURE_KEYS,
    LOG_KEYS,
    QUESTION_KEYS,
    new_literature,
    new_question,
    new_topic,
)

TEMPLATES = Path(__file__).resolve().parents[1] / "template" / "protocol" / "templates"
WHO = {"person": "Fan", "agent": "codex", "date": "2026-10-25"}


@pytest.mark.parametrize(
    ("name", "keys"),
    [
        ("literature", LITERATURE_KEYS),
        ("question", QUESTION_KEYS),
        ("decision", DECISION_KEYS),
        ("log", LOG_KEYS),
    ],
)
def test_template_frontmatter_keys_match_the_key_tuples(name, keys):
    lines = (TEMPLATES/f"{name}.md").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "---"
    block = lines[1 : lines.index("---", 1)]
    found = tuple(m.group(1) for line in block if (m := re.match(r"([A-Za-z][\w-]*):", line)))
    assert found == keys


def test_topic_template_has_no_frontmatter():
    assert not (TEMPLATES/"topic.md").read_text(encoding="utf-8").startswith("---")


def test_templates_are_found_next_to_the_package():
    assert newfile.TEMPLATES_DIR == TEMPLATES
    for name in ("literature", "question", "decision", "log", "topic"):
        assert (TEMPLATES/f"{name}.md").is_file(), name


def _use_templates(monkeypatch, directory: Path, **files: str) -> None:
    """Point newfile at a scratch templates directory holding the given files."""
    directory.mkdir()
    for name, text in files.items():
        (directory/f"{name}.md").write_text(text, encoding="utf-8")
    monkeypatch.setattr(newfile, "TEMPLATES_DIR", directory)


def test_body_comes_from_the_template_file(repo, tmp_path, monkeypatch):
    template = (
        "---\nid: {id}\n---\n\n## Mine\n<!-- a note\nover two lines -->\nkept {unknown} text\n"
    )
    _use_templates(monkeypatch, tmp_path/"t", question=template)
    _, body = parse(new_question(repo, "x", "t", "Fan", "codex", date(2026, 10, 25)))
    assert body == "\n## Mine\nkept {unknown} text\n"


def test_templates_checked_out_with_crlf_still_give_lf_files(repo, tmp_path, monkeypatch):
    template = b"---\r\nid: {id}\r\n---\r\n\r\n## Mine\r\n<!-- note -->\r\ntext\r\n"
    directory = tmp_path/"t"
    directory.mkdir()
    (directory/"question.md").write_bytes(template)
    monkeypatch.setattr(newfile, "TEMPLATES_DIR", directory)
    written = new_question(repo, "x", "t", "Fan", "codex", date(2026, 10, 25)).read_bytes()
    assert b"\r" not in written
    assert written.endswith(b"---\n\n## Mine\ntext\n")


def test_only_word_tokens_are_filled_in(repo, paper, tmp_path, monkeypatch):
    template = "---\ncitekey: {citekey}\n---\n\n@article{{citekey}, title = {{A} study}}\n"
    _use_templates(monkeypatch, tmp_path/"t", literature=template)
    _, body = parse(new_literature(repo, "c1", dict(WHO), paper))
    assert body == "\n@article{c1, title = {{A} study}}\n"


def test_topic_template_is_filled_with_topic_and_scope(repo, tmp_path, monkeypatch):
    _use_templates(monkeypatch, tmp_path/"t", topic="# {topic}\n{scope}\n\n<!-- note -->\n")
    p = new_topic(repo, "goes-abi", "uses {topic} literally")
    assert p.read_text(encoding="utf-8") == "# goes-abi\nuses {topic} literally\n\n"
