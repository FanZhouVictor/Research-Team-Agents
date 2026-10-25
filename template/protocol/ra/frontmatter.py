"""Read and write Markdown files that begin with a YAML frontmatter block.

File layout:

    ---
    key: value
    ---
    body text, returned exactly as stored

The block between the two '---' lines must be a YAML mapping. Typing is deliberately
narrow so that generated and hand-written files read back identically: dates, times and
identifiers stay plain strings (2026-10-25, 14:32, 2401.10250), and only decimal
integers, booleans and null get YAML types. parse() lists the exact rules.
"""

import datetime
import re
from pathlib import Path
from typing import Any, ClassVar

import yaml

__all__ = ["FrontmatterError", "dump", "parse", "write"]

_TIMESTAMP_TAG = "tag:yaml.org,2002:timestamp"
_FLOAT_TAG = "tag:yaml.org,2002:float"
_INT_TAG = "tag:yaml.org,2002:int"
_NULL_TAG = "tag:yaml.org,2002:null"

# Plain decimal integers: no sexagesimal (14:32), hex/octal/binary or underscore forms.
_DECIMAL_INT = re.compile(r"^[-+]?(0|[1-9][0-9]*)$")

# PyYAML folds scalars at 80 columns by default; this width is large enough to never fold.
_NO_FOLDING = 10**6

# The opening '---' line must be the first line of the file; the closing one is the first
# later line made of '---' alone. Both may carry trailing spaces/tabs and a CRLF ending.
_OPEN = re.compile(r"---[ \t]*\r?\n")
_CLOSE = re.compile(r"^---[ \t]*(?:\r?\n|\Z)", re.MULTILINE)


class FrontmatterError(ValueError):
    """A file has no usable frontmatter.

    Raised for bytes that are not UTF-8, a missing or unterminated block, invalid YAML,
    and YAML that is not a mapping.
    """


def _without(resolvers: dict[Any, list[Any]], *tags: str) -> dict[Any, list[Any]]:
    """Copy a YAML implicit-resolver table, dropping the entries for the given tags."""
    return {
        first: [(tag, regexp) for tag, regexp in entries if tag not in tags]
        for first, entries in resolvers.items()
    }


class _Loader(yaml.SafeLoader):
    """SafeLoader (no arbitrary Python objects) with narrow implicit typing.

    Timestamps, floats and the stock int forms (sexagesimal, hex, octal, binary,
    underscores) are not recognised implicitly, so dates, times and identifiers stay str.
    """

    yaml_implicit_resolvers = _without(
        yaml.SafeLoader.yaml_implicit_resolvers, _TIMESTAMP_TAG, _FLOAT_TAG, _INT_TAG
    )
    # An explicit '!!timestamp 2026-10-25' stays a string too.
    yaml_constructors: ClassVar[dict[str | None, Any]] = {
        **yaml.SafeLoader.yaml_constructors,
        _TIMESTAMP_TAG: yaml.SafeLoader.construct_yaml_str,
    }


# Replaces the stock int resolver removed above with the decimal-only one.
_Loader.add_implicit_resolver(_INT_TAG, _DECIMAL_INT, list("-+0123456789"))


class _Dumper(yaml.SafeDumper):
    """SafeDumper matched to _Loader: str, int, bool, None, list and dict read back as written.

    Only the timestamp resolver is removed, so date-like strings are written unquoted.
    The int and float resolvers are the stock ones: strings that look like numbers
    (2401.10250, 14:32) are quoted and stay unambiguous for any YAML reader.
    """

    yaml_implicit_resolvers = _without(yaml.SafeDumper.yaml_implicit_resolvers, _TIMESTAMP_TAG)

    def ignore_aliases(self, data: Any) -> bool:
        """Never write anchors or aliases: an object used twice is written twice."""
        return True


def _represent_none(dumper: yaml.SafeDumper, data: None) -> yaml.ScalarNode:
    return dumper.represent_scalar(_NULL_TAG, "")


def _represent_date(dumper: yaml.SafeDumper, data: datetime.date) -> yaml.ScalarNode:
    return dumper.represent_str(data.isoformat())


_Dumper.add_representer(type(None), _represent_none)
_Dumper.add_representer(datetime.date, _represent_date)
_Dumper.add_representer(datetime.datetime, _represent_date)


def parse(path: Path) -> tuple[dict, str]:
    """Read a frontmatter file.

    Typing rules: only decimal integers (2024, -3), booleans (true, false, yes, no, on,
    off) and null (empty, ~, null) get YAML types. Everything else is a str, notably
    dates (2026-10-25), times (14:32), identifiers such as arXiv ids (2401.10250), floats
    (1.5) and hex, octal, binary or underscore forms (0x1f, 017, 1_000). An explicit
    '!!timestamp' tag also gives a str.

    Args:
        path: File to read: UTF-8, with or without a BOM.

    Returns:
        (meta, body): the YAML mapping with keys in file order, and everything after the
        closing '---' line, unchanged. An empty block gives an empty mapping.

    Raises:
        FrontmatterError: the only exception for bad content: the bytes are not UTF-8, the
            file does not start with a '---' line, there is no closing '---' line, the
            YAML cannot be loaded (syntax error, unsafe tag, bad value for an explicit tag,
            or any other failure of the YAML loader), or it is not a mapping. A missing or
            unreadable file raises OSError as usual.
    """
    try:
        # utf-8-sig tolerates a BOM; newline="" keeps the body byte-for-byte.
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            text = handle.read()
    except UnicodeDecodeError as exc:
        raise FrontmatterError(f"{path}: not valid UTF-8: {exc}") from exc
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
    except Exception as exc:
        # Not only yaml.YAMLError: the constructors also raise ValueError, KeyError,
        # IndexError and the like for bad values of explicit tags ('!!int abc', '!!float'),
        # and deep nesting raises RecursionError. Whatever the loader raises is bad content.
        detail = str(exc) if isinstance(exc, yaml.YAMLError) else f"{type(exc).__name__}: {exc}"
        raise FrontmatterError(f"{path}: invalid YAML in frontmatter: {detail}") from exc
    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        raise FrontmatterError(
            f"{path}: frontmatter must be a YAML mapping, not {type(meta).__name__}"
        )
    return meta, text[closing.end() :]


def dump(meta: dict, body: str) -> str:
    """Return the text of a frontmatter file: a YAML block for meta, then body.

    Keys keep their order, non-ASCII text is written as is, long values stay on one line,
    and an object used twice is written twice (no anchors). date and datetime values are
    written as plain ISO strings and None as an empty value (key:); strings that look
    like numbers (2401.10250, 14:32) are quoted. Pass numbers as ints: a float is written
    as a plain number but reads back as a str.

    Args:
        meta: Mapping of plain values (str, int, bool, None, date, datetime, list, dict).
        body: Text placed after the closing '---' line, unchanged.

    Returns:
        '---\\n', the YAML, '---\\n' and body, concatenated.
    """
    block = yaml.dump(
        meta,
        Dumper=_Dumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=_NO_FOLDING,
    )
    return f"---\n{block}---\n{body}"


def write(path: Path, meta: dict, body: str) -> None:
    """Write dump(meta, body) to path as UTF-8 (no BOM) with LF line endings on every OS."""
    path.write_text(dump(meta, body), encoding="utf-8", newline="")
