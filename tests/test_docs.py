"""Tests for the documents every project starts with: PROTOCOL.md, CLAUDE.md and AGENTS.md.

PROTOCOL.md is the runbook every AI session follows (spec §13 and §14). These tests pin its
sixteen sections and the runbook of every verb, the passages it carries word for word from the
spec, that every command it shows exists in the ra command line with the flags it uses, that
the formats it shows are the ones the parsers read, and that its version is the one 'ra init'
stamps. SECTIONS and VERBS are also used by the plugin tests.
"""

import argparse
import re
from pathlib import Path

import pytest
from ra.cli import build_parser
from ra.commit import TYPE_TAGS
from ra.frontmatter import parse
from ra.knowledge import parse_fact_line
from ra.literature import parse_claims
from ra.scaffold import init_project

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "template"
PROTOCOL = TEMPLATE / "PROTOCOL.md"
SPEC = ROOT / "docs" / "superpowers" / "specs" / "2026-10-25-ra-agent-framework-stage0-design.md"
CHECK_SOURCE = TEMPLATE / "protocol" / "ra" / "check.py"

SECTIONS = [
    "Purpose and scope", "Bootstrap", "Repo map", "Information types and write rules",
    "Session procedure", "Verbs", "Literature rules", "Human gates", "Conflict rules",
    "Naming conventions", "Commit conventions", "File templates", "Never-in-repo list",
    "Health checks", "Glossary", "Protocol version and change procedure",
]
VERBS = [
    "session-start", "session-end", "add-literature", "reread-literature", "propose-question",
    "close-question", "propose-knowledge", "propose-decision", "accept-decision",
    "supersede-decision", "update-status",
]
# The five parts of every runbook, in order (Task 9 brief, step 3).
PARTS = ("**Preconditions:**", "**Steps:**", "**Ask the human:**", "**Files changed:**",
         "**Commit:**")
COMMAND = "python protocol/ra.py"
_FENCE = re.compile(r"(\s*)```")


def _read(path: Path) -> str:
    """The text of a UTF-8 file."""
    return path.read_text(encoding="utf-8")


def _blocks(text: str) -> list[str]:
    """The fenced code blocks of text, each without the indentation of its opening fence."""
    blocks: list[str] = []
    current: list[str] | None = None
    indent = ""
    for line in text.splitlines():
        fence = _FENCE.match(line)
        if fence and current is None:
            current, indent = [], fence.group(1)
        elif fence and current is not None:
            blocks.append("\n".join(current))
            current = None
        elif current is not None:
            current.append(line.removeprefix(indent))
    return blocks


def _split(text: str, marker: str) -> list[tuple[str, str]]:
    """Each heading line of text that starts with marker, outside fenced blocks, with the text
    after it up to the next such heading: (heading without the marker, text)."""
    parts: list[tuple[str, list[str]]] = []
    fenced = False
    for line in text.splitlines():
        if _FENCE.match(line):
            fenced = not fenced
        elif not fenced and line.startswith(marker):
            parts.append((line[len(marker):], []))
            continue
        if parts:
            parts[-1][1].append(line)
    return [(heading, "\n".join(lines)) for heading, lines in parts]


def _section(number: int) -> str:
    """The text of section number of PROTOCOL.md, under its heading '## <number>. <title>'."""
    heading, text = _split(_read(PROTOCOL), "## ")[number - 1]
    assert heading == f"{number}. {SECTIONS[number - 1]}"
    return text


def _runbooks() -> dict[str, str]:
    """The '### <verb>' runbooks of section 6 by verb, in document order."""
    return dict(_split(_section(6), "### "))


def _words(text: str) -> str:
    """text with every run of whitespace made one space, for comparing prose."""
    return " ".join(text.split())


def _spec_line(prefix: str) -> str:
    """The one line of the spec that starts with prefix."""
    lines = [line for line in _read(SPEC).splitlines() if line.startswith(prefix)]
    assert len(lines) == 1, prefix
    return lines[0]


def _spec_between(start: str, end: str) -> str:
    """The spec text between the line start and the line end, stripped."""
    text = _read(SPEC)
    return text[text.index(f"\n{start}\n") + len(start) + 2 : text.index(f"\n{end}\n")].strip()


def _spec_prompts() -> list[str]:
    """The three gate prompt blocks of spec §8."""
    prompts = [b for b in _blocks(_read(SPEC)) if b.startswith("Proposed for the shared repo")]
    assert len(prompts) == 3
    return prompts


def _subcommands(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    """The subcommands of parser by name, as argparse registered them; {} if it has none."""
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    return {}


def _check_command(line: str, parser: argparse.ArgumentParser) -> None:
    """Assert that the command line names an existing command and uses only its own flags.

    The words after 'python protocol/ra.py' name a command and, for 'new' and 'sync', a
    subcommand of it. Every '--flag' must be one of that (sub)command's flags, and every
    required flag must be there unless the line asks for --help. Values are placeholders and
    are not checked.
    """
    words = line.split()[2:]
    asks_help = "--help" in words
    while words and not words[0].startswith("-") and _subcommands(parser):
        commands = _subcommands(parser)
        assert words[0] in commands, f"unknown command {words[0]!r} in: {line}"
        parser, words = commands[words[0]], words[1:]
    known = {flag for action in parser._actions for flag in action.option_strings}
    flags = {word for word in words if word.startswith("--") and word != "--"}
    assert flags <= known, f"unknown flag(s) {sorted(flags - known)} in: {line}"
    if asks_help:
        return
    assert not _subcommands(parser), f"a subcommand is missing in: {line}"
    for action in parser._actions:
        if action.required and action.option_strings:
            assert flags & set(action.option_strings), f"{action.option_strings} missing: {line}"


# --- the brief's tests (Task 9, step 1) -------------------------------------------------------


def test_protocol_has_all_sections_in_order():
    headings = [heading for heading, _ in _split(_read(PROTOCOL), "## ")]
    assert headings == [f"{number}. {title}" for number, title in enumerate(SECTIONS, start=1)]


def test_every_verb_has_a_runbook_and_gate_prompts_are_verbatim():
    text = _read(PROTOCOL)
    assert list(_runbooks()) == VERBS
    for verb in VERBS:
        assert f"### {verb}" in text
    assert "Commit / Edit / Skip?" in text and "Proposed for the shared repo — KNOWLEDGE" in text


def test_entry_files_are_single_instruction():
    for name in ("CLAUDE.md", "AGENTS.md"):
        lines = [line for line in _read(TEMPLATE / name).splitlines() if line.strip()]
        assert len(lines) <= 3 and "PROTOCOL.md" in " ".join(lines)


# --- structure ---------------------------------------------------------------------------------


def test_the_verbs_are_the_spec_verbs_except_dual_run():
    line = _spec_line("- **The plugin's skills implement the verbs**")
    spec_verbs = re.findall(r"`([a-z-]+)`", line.split(". Skills cite")[0])
    assert spec_verbs == [*VERBS, "dual-run"]
    assert "dual-run" in _section(6) and "### dual-run" not in _section(6)


@pytest.mark.parametrize("verb", VERBS)
def test_every_runbook_has_the_five_parts_in_order(verb):
    runbook = _runbooks()[verb]
    places = [runbook.find(part) for part in PARTS]
    assert -1 not in places, f"{verb} lacks {[p for p, at in zip(PARTS, places) if at < 0]}"
    assert places == sorted(places)


# --- commands, codes and tags match the tooling ------------------------------------------------


def test_every_command_shown_exists_with_the_flags_it_uses():
    lines = [line.strip() for block in _blocks(_read(PROTOCOL)) for line in block.splitlines()]
    commands = [line for line in lines if line.startswith(f"{COMMAND} ")]
    assert len(commands) > 20  # every runbook shows its commands
    for line in commands:
        _check_command(line, build_parser())


def test_section_14_names_every_check_code_and_no_other():
    codes = set(re.findall(r'_finding\(\s*"([A-Z_]+)"', _read(CHECK_SOURCE)))
    assert "DECISION_EDITED" in codes
    assert set(re.findall(r"\b[A-Z]+(?:_[A-Z]+)+\b", _section(14))) == codes


def test_section_11_lists_the_commit_types_of_ra_commit():
    [line] = [line for line in _section(11).splitlines() if line.startswith("- **Type tags**")]
    assert tuple(re.findall(r"`([a-z]+)`", line.split(". ")[0])) == TYPE_TAGS


def test_formats_shown_are_the_formats_the_parsers_read():
    blocks = _blocks(_read(PROTOCOL))
    facts = [line.strip() for block in blocks for line in block.splitlines() if "(src:" in line]
    assert facts and all(parse_fact_line(line) is not None for line in facts)
    examples = [b for b in _blocks(_section(7)) if b.startswith("## Claims for this project\n")]
    assert len(examples) == 1
    [claim] = parse_claims(examples[0])
    assert claim.where and claim.bears_on and claim.by
    assert (claim.kind, claim.basis) == ("result", "stated by paper")
    assert claim.verified_by == [] and claim.disputed_by == []


# --- verbatim passages from the spec ----------------------------------------------------------


def test_the_gate_prompts_of_spec_8_are_in_section_8_verbatim():
    blocks = _blocks(_section(8))
    for prompt in _spec_prompts():
        assert prompt in blocks


@pytest.mark.parametrize(
    ("number", "passage"),
    [
        (8, lambda: _spec_line("`Edit` returns the proposal")),
        (7, lambda: _spec_between("### 10.1 The PDF-first rule", "### 10.2 Dedup")),
        (5, lambda: _spec_line("**Conflicts.**")),
    ],
    ids=["edit-skip-sentences", "pdf-first-rule", "conflict-stop-rule"],
)
def test_spec_passages_are_copied_word_for_word(number, passage):
    assert _words(passage()) in _words(_section(number))


# --- version and the files a project starts with ----------------------------------------------


def test_the_version_is_the_one_init_stamps_and_heads_the_changelog(tmp_path):
    meta, _ = parse(PROTOCOL)
    assert meta == {"version": "0.1.0"}
    dest = tmp_path / "p"
    init_project(dest, "P", "Fan", "Fan <fan@x>", ["codex"], "PI")
    assert parse(dest / "PROJECT.md")[0] == {"protocol-version": meta["version"]}
    assert f"`{meta['version']} — " in _section(16)
    for name in ("PROTOCOL.md", "CLAUDE.md", "AGENTS.md"):
        assert (dest / name).read_bytes() == (TEMPLATE / name).read_bytes(), name
