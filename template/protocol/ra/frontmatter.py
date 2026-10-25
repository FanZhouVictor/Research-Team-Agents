"""Read and write Markdown files that begin with a YAML frontmatter block.

File layout:

    ---
    key: value
    ---
    body text, returned exactly as stored

The block between the two '---' lines must be a YAML mapping. Dates are plain
strings: 2026-10-25 is read back as the str '2026-10-25' (never a datetime.date)
and is written without quotes, so generated and hand-written files parse alike.
"""

import re
from pathlib import Path
from typing import Any

import yaml

__all__ = ["FrontmatterError", "dump", "parse", "write"]

_TIMESTAMP_TAG = "tag:yaml.org,2002:timestamp"
_NULL_TAG = "tag:yaml.org,2002:null"

# The opening '---' line must be the first line of the file; the closing one is the first
# later line made of '---' alone. Both may carry trailing spaces/tabs and a CRLF ending.
_OPEN = re.compile(r"---[ \t]*\r?\n")
_CLOSE = re.compile(r"^---[ \t]*(?:\r?\n|\Z)", re.MULTILINE)


class FrontmatterError(ValueError):
    """A file has no usable frontmatter: missing, unterminated, bad YAML, or not a mapping."""


def _without_timestamp(resolvers: dict[Any, list[Any]]) -> dict[Any, list[Any]]:
    """Copy a YAML implicit-resolver table, dropping the entries for timestamps."""
    return {
        first: [(tag, regexp) for tag, regexp in entries if tag != _TIMESTAMP_TAG]
        for first, entries in resolvers.items()
    }


class _Loader(yaml.SafeLoader):
    """SafeLoader (no arbitrary Python objects) that leaves date-like scalars as str."""

    yaml_implicit_resolvers = _without_timestamp(yaml.SafeLoader.yaml_implicit_resolvers)


class _Dumper(yaml.SafeDumper):
    """SafeDumper that writes date-like strings unquoted and None as an empty value."""

    yaml_implicit_resolvers = _without_timestamp(yaml.SafeDumper.yaml_implicit_resolvers)


def _represent_none(dumper: yaml.SafeDumper, data: None) -> yaml.ScalarNode:
    return dumper.represent_scalar(_NULL_TAG, "")


_Dumper.add_representer(type(None), _represent_none)


def parse(path: Path) -> tuple[dict, str]:
    """Read a frontmatter file.

    Args:
        path: File to read, UTF-8.

    Returns:
        (meta, body): the YAML mapping with keys in file order, and everything after
        the closing '---' line, unchanged. An empty block gives an empty mapping.

    Raises:
        FrontmatterError: the file does not start with a '---' line, has no closing
            '---' line, holds invalid or unsafe YAML, or the YAML is not a mapping.
    """
    # newline="" keeps the body byte-for-byte (no CRLF to LF translation).
    with path.open("r", encoding="utf-8", newline="") as handle:
        text = handle.read()
    opening = _OPEN.match(text)
    if opening is None:
        raise FrontmatterError(
            f"{path}: no frontmatter block (the file must start with a '---' line)"
        )
    closing = _CLOSE.search(text, opening.end())
    if closing is None:
        raise FrontmatterError(
            f"{path}: unterminated frontmatter block (no closing '---' line)"
        )
    try:
        # Parsed from the opening '---' (a valid YAML document start) so that line
        # numbers in YAML error messages match the line numbers of the file.
        meta = yaml.load(text[: closing.start()], Loader=_Loader)
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"{path}: invalid YAML in frontmatter: {exc}") from exc
    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        raise FrontmatterError(
            f"{path}: frontmatter must be a YAML mapping, not {type(meta).__name__}"
        )
    return meta, text[closing.end() :]


def dump(meta: dict, body: str) -> str:
    """Return the text of a frontmatter file: a YAML block for meta, then body.

    Keys keep their order and non-ASCII text is written as is. Pass dates as ISO
    strings; they are written unquoted. None is written as an empty value (key:).

    Args:
        meta: Mapping of plain YAML values (str, int, float, bool, None, list, dict).
        body: Text placed after the closing '---' line, unchanged.

    Returns:
        '---\\n', the YAML, '---\\n' and body, concatenated.
    """
    block = yaml.dump(
        meta, Dumper=_Dumper, sort_keys=False, allow_unicode=True, default_flow_style=False
    )
    return f"---\n{block}---\n{body}"


def write(path: Path, meta: dict, body: str) -> None:
    """Write dump(meta, body) to path as UTF-8 with LF line endings on every OS."""
    path.write_text(dump(meta, body), encoding="utf-8", newline="")
