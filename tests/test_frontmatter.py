"""Tests for ra.frontmatter: YAML frontmatter parse, dump and write."""

from datetime import date, datetime
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


# --- implicit typing: only decimal ints, bools and null are typed -------------------------


@pytest.mark.parametrize(
    ("scalar", "expected"),
    [
        ("2024", 2024),
        ("-3", -3),
        ("+5", 5),
        ("0", 0),
        ("true", True),
        ("no", False),
        ("null", None),
        ("~", None),
        ("2401.10250", "2401.10250"),
        ("1.5", "1.5"),
        (".inf", ".inf"),
        ("1e3", "1e3"),
        ("14:32", "14:32"),
        ("14:32:05", "14:32:05"),
        ("2026-10-25", "2026-10-25"),
        ("0x1f", "0x1f"),
        ("0b101", "0b101"),
        ("017", "017"),
        ("1_000", "1_000"),
    ],
)
def test_implicit_typing_rules(tmp_path, scalar, expected):
    m, _ = parse(_put(tmp_path / "t.md", f"---\nk: {scalar}\n---\n"))
    assert m["k"] == expected
    assert type(m["k"]) is type(expected)


def test_hand_written_arxiv_id_time_and_year(tmp_path):
    text = "---\narxiv: 2401.10250\nsession: 14:32\nyear: 2024\n---\n"
    m, _ = parse(_put(tmp_path / "t.md", text))
    assert m == {"arxiv": "2401.10250", "session": "14:32", "year": 2024}
    assert type(m["arxiv"]) is str and type(m["session"]) is str and type(m["year"]) is int


def test_numeric_looking_strings_are_quoted_and_roundtrip(tmp_path):
    meta = {"arxiv": "2401.10250", "session": "14:32", "year": 2024}
    p = tmp_path / "r.md"
    write(p, meta, "")
    raw = p.read_text(encoding="utf-8")
    assert raw == "---\narxiv: '2401.10250'\nsession: '14:32'\nyear: 2024\n---\n"
    m, _ = parse(p)
    assert m == meta
    assert type(m["arxiv"]) is str and type(m["year"]) is int


# --- dates: objects dump as plain ISO strings, explicit timestamp tags load as str --------


def test_date_object_dumps_as_plain_iso_string_and_reads_back_as_str(tmp_path):
    text = dump({"d": date(2026, 10, 25)}, "")
    assert text == "---\nd: 2026-10-25\n---\n"
    m, _ = parse(_put(tmp_path / "d.md", text))
    assert m == {"d": "2026-10-25"} and type(m["d"]) is str


def test_datetime_object_dumps_as_plain_iso_string_and_reads_back_as_str(tmp_path):
    text = dump({"t": datetime(2026, 10, 25, 14, 32)}, "")
    assert text == "---\nt: 2026-10-25T14:32:00\n---\n"
    m, _ = parse(_put(tmp_path / "t.md", text))
    assert m == {"t": "2026-10-25T14:32:00"} and type(m["t"]) is str


@pytest.mark.parametrize(
    "scalar",
    ["!!timestamp '2026-10-25'", "!!timestamp 2026-10-25"],
    ids=["quoted", "plain"],
)
def test_explicit_timestamp_tag_loads_as_str(tmp_path, scalar):
    m, _ = parse(_put(tmp_path / "e.md", f"---\nd: {scalar}\n---\n"))
    assert m == {"d": "2026-10-25"} and type(m["d"]) is str


# --- error contract: parse raises only FrontmatterError on bad input ----------------------


def test_non_utf8_file_raises_frontmatter_error(tmp_path):
    p = tmp_path / "latin1.md"
    p.write_bytes("---\ntitle: µ\n---\nbody\n".encode("latin-1"))
    with pytest.raises(FrontmatterError, match="not valid UTF-8") as info:
        parse(p)
    assert str(p) in str(info.value)


def test_utf8_bom_is_tolerated(tmp_path):
    p = tmp_path / "bom.md"
    text = "---\ntitle: µ\n---\nbody\n"
    p.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    assert parse(p) == ({"title": "µ"}, "body\n")


@pytest.mark.parametrize(
    "line",
    ["a: !!int abc", "a: !!float abc", "a: !!bool maybe"],
    ids=["int", "float", "bool"],
)
def test_bad_value_for_explicit_tag_raises_frontmatter_error(tmp_path, line):
    p = _put(tmp_path / "t.md", f"---\n{line}\n---\n")
    with pytest.raises(FrontmatterError, match="invalid YAML") as info:
        parse(p)
    assert str(p) in str(info.value)


def test_absurdly_deep_nesting_raises_frontmatter_error(tmp_path):
    text = "---\na: " + "[" * 3000 + "]" * 3000 + "\n---\n"
    with pytest.raises(FrontmatterError, match="invalid YAML"):
        parse(_put(tmp_path / "deep.md", text))


# --- dump output shape: no folding, no anchors --------------------------------------------


def test_long_values_stay_on_one_line(tmp_path):
    title = " ".join(["segmentation"] * 16)
    assert len(title) >= 200
    assert dump({"title": title}, "") == f"---\ntitle: {title}\n---\n"
    p = tmp_path / "long.md"
    write(p, {"title": title}, "")
    assert parse(p)[0] == {"title": title}


def test_shared_objects_are_written_in_full_without_anchors(tmp_path):
    shared_list = ["q1", "q2"]
    shared_map = {"person": "Fan", "agent": "codex"}
    meta = {"links": shared_list, "bears-on": shared_list, "a": shared_map, "b": shared_map}
    text = dump(meta, "")
    assert "&" not in text and "*" not in text
    m, _ = parse(_put(tmp_path / "s.md", text))
    assert m == meta
