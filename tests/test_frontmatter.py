"""Tests for ra.frontmatter: YAML frontmatter parse, dump and write."""

from pathlib import Path

import pytest
from ra.frontmatter import FrontmatterError, dump, parse, write


def _put(path: Path, text: str) -> Path:
    """Write text to path without newline translation, so tests see the exact bytes."""
    path.write_bytes(text.encode("utf-8"))
    return path


def test_roundtrip_preserves_unicode_and_order(tmp_path):
    meta = {"title": "烟羽分割 — 3.9 µm", "readers": [{"person": "Fan", "agent": "codex"}]}
    write(tmp_path/"a.md", meta, "## Summary\nbody\n")
    m, body = parse(tmp_path/"a.md")
    assert m == meta and body == "## Summary\nbody\n"
    assert list(m) == ["title", "readers"]


def test_missing_frontmatter_raises(tmp_path):
    (tmp_path/"b.md").write_text("no block here", encoding="utf-8")
    with pytest.raises(FrontmatterError):
        parse(tmp_path/"b.md")


@pytest.mark.parametrize(
    "text",
    ["", "no block here", "\n---\na: 1\n---\nbody\n", "title: x\n---\nbody\n"],
    ids=["empty-file", "plain-text", "blank-line-before-block", "no-opening-delimiter"],
)
def test_block_must_start_on_the_first_line(tmp_path, text):
    with pytest.raises(FrontmatterError, match="no frontmatter"):
        parse(_put(tmp_path / "f.md", text))


def test_unterminated_block_raises(tmp_path):
    with pytest.raises(FrontmatterError, match="unterminated"):
        parse(_put(tmp_path / "f.md", "---\na: 1\nbody but no closing delimiter\n"))


@pytest.mark.parametrize(
    "text",
    ["---\n- a\n- b\n---\nbody\n", "---\njust a string\n---\nbody\n"],
    ids=["list", "scalar"],
)
def test_non_mapping_yaml_raises(tmp_path, text):
    with pytest.raises(FrontmatterError, match="must be a YAML mapping"):
        parse(_put(tmp_path / "f.md", text))


def test_invalid_yaml_raises_frontmatter_error(tmp_path):
    with pytest.raises(FrontmatterError, match="invalid YAML"):
        parse(_put(tmp_path / "f.md", "---\na: [unclosed\n---\nbody\n"))


def test_unsafe_yaml_tag_is_rejected(tmp_path):
    text = "---\nx: !!python/object/apply:os.getcwd []\n---\nbody\n"
    with pytest.raises(FrontmatterError, match="invalid YAML"):
        parse(_put(tmp_path / "f.md", text))


def test_empty_block_is_an_empty_mapping(tmp_path):
    assert parse(_put(tmp_path / "f.md", "---\n---\nbody\n")) == ({}, "body\n")


@pytest.mark.parametrize(
    ("text", "body"),
    [
        ("---\r\ntitle: x\r\n---\r\nbody\r\n", "body\r\n"),
        ("--- \ntitle: x\n---\t\nbody\n", "body\n"),
        ("---\ntitle: x\n---", ""),
    ],
    ids=["crlf", "trailing-whitespace", "closing-delimiter-at-eof"],
)
def test_delimiter_line_variants(tmp_path, text, body):
    assert parse(_put(tmp_path / "f.md", text)) == ({"title": "x"}, body)


def test_body_is_returned_verbatim_after_first_closing_delimiter(tmp_path):
    body = "\n## Heading\n\n---\n\ntrailing spaces  \r\nCRLF line\r\n"
    meta, got = parse(_put(tmp_path / "f.md", "---\na: 1\n---\n" + body))
    assert meta == {"a": 1}
    assert got == body


def test_dump_layout_is_exact():
    assert dump({"a": 1, "b": ["x", "y"]}, "body\n") == "---\na: 1\nb:\n- x\n- y\n---\nbody\n"


def test_write_stores_utf8_with_lf_line_endings(tmp_path):
    p = tmp_path / "w.md"
    write(p, {"title": "µ"}, "line\n")
    expected = "---\ntitle: µ\n---\nline\n"
    assert p.read_bytes() == expected.encode("utf-8")


def test_date_like_strings_roundtrip_as_unquoted_strings(tmp_path):
    meta = {"date": "2026-10-25", "proposed-by": {"person": "Fan", "date": "2026-10-25"}}
    p = tmp_path / "d.md"
    write(p, meta, "")
    raw = p.read_text(encoding="utf-8")
    assert "date: 2026-10-25\n" in raw
    assert "'2026-10-25'" not in raw and '"2026-10-25"' not in raw
    m, _ = parse(p)
    assert m == meta
    assert isinstance(m["date"], str)


def test_hand_written_unquoted_dates_parse_as_strings(tmp_path):
    text = (
        "---\n"
        "date: 2026-10-25\n"
        "readers:\n"
        "  - {person: Fan, agent: codex, date: 2026-10-25, read: full-text}\n"
        "---\n"
    )
    m, _ = parse(_put(tmp_path / "h.md", text))
    assert m["date"] == "2026-10-25"
    assert m["readers"][0]["date"] == "2026-10-25"


def test_none_roundtrips_as_empty_value_distinct_from_empty_string(tmp_path):
    meta = {"doi": None, "note": "", "year": 2024}
    p = tmp_path / "n.md"
    write(p, meta, "")
    assert p.read_text(encoding="utf-8") == "---\ndoi:\nnote: ''\nyear: 2024\n---\n"
    m, _ = parse(p)
    assert m == meta
    assert m["doi"] is None and m["note"] == ""
