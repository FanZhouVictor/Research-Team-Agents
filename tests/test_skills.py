"""Tests for the Claude Code plugin in plugin/: its manifest and a skill per verb of PROTOCOL.md.

A skill holds no rule of its own (the Task 10 convention). It cites sections of PROTOCOL.md that
exist, numbers its steps as its verb's runbook in section 6 does, and shows each command of the
runbook byte for byte at the step that runs it. A runbook step that runs another verb, such as
"run propose-question" or "continue with supersede-decision from step 3", shows that verb's
commands at the same step of the skill, in a block indented deeper than the step's own fences
(Ruling R54). These tests are the drift guard between the skills and PROTOCOL.md.
"""

import json
import re

import pytest
from ra.cli import build_parser
from ra.frontmatter import parse
from test_docs import (
    _FENCE,
    COMMAND,
    PARTS,
    PROTOCOL,
    ROOT,
    SECTIONS,
    VERBS,
    _blocks,
    _check_command,
    _fenced,
    _read,
    _runbooks,
)

PLUGIN = ROOT / "plugin"
SKILLS = PLUGIN / "skills"
# The skill convention (Task 10): the body of a SKILL.md has exactly these headings, in order.
SKILL_HEADINGS = ["## Implements", "## Steps", "## Stop conditions"]
# Ruling R24 amended: the verbs whose skill does not exist yet. Tasks 11-13 remove theirs.
PENDING_SKILLS: list[str] = []
_PENDING = pytest.mark.xfail(strict=True, reason="skill arrives in Tasks 11-13")
_HEADING = re.compile(r"#{1,6} ")
_RUNS_RA = re.compile(r"python \S*ra\.py ")  # a command line that runs the helper
_STEP = re.compile(r"^(\d+)\. ", re.MULTILINE)  # a step: a numbered item at the start of a line
# A runbook step that runs another verb, in full or from one of its steps (section 6).
_RUNS_VERB = re.compile(r"\b(?:[Rr]un|continue with) ([a-z]+(?:-[a-z]+)+)(?: from step (\d+))?")


def _cases(names: list[str]) -> list[object]:
    """names as test parameters; one whose skill is pending is a strict xfail (Ruling R24)."""
    return [pytest.param(name, marks=_PENDING) if name in PENDING_SKILLS else name
            for name in names]


def _headings(text: str) -> list[str]:
    """The Markdown heading lines of text, outside fenced blocks."""
    headings: list[str] = []
    fenced = False
    for line in text.splitlines():
        if _FENCE.match(line):
            fenced = not fenced
        elif not fenced and _HEADING.match(line):
            headings.append(line)
    return headings


def _ra_lines(block: str) -> list[str]:
    """The 'python protocol/ra.py' lines of a fenced block, stripped, in order."""
    lines = [line.strip() for line in block.splitlines()]
    return [line for line in lines if line.startswith(f"{COMMAND} ")]


def _steps(text: str) -> list[tuple[int, int, str]]:
    """The steps of text: (number, the column its text starts at, the step up to the next one)."""
    marks = list(_STEP.finditer(text))
    ends = [mark.start() for mark in marks[1:]] + [len(text)]
    return [(int(mark.group(1)), mark.end() - mark.start(), text[mark.start() : end])
            for mark, end in zip(marks, ends)]


def _runbook_steps(verb: str) -> list[tuple[int, str, list[str]]]:
    """The steps of the verb's runbook: (number, text, the commands it runs, in order). The
    command of the Commit part runs at the step that says '(below)', such as 'Commit (below).'."""
    runbook = _runbooks()[verb]
    text = runbook[runbook.index(PARTS[1]) : runbook.index(PARTS[2])]
    commit = [line for block in _blocks(runbook.partition(PARTS[-1])[2])
              for line in _ra_lines(block)]
    steps = [(number, step, [line for block in _blocks(step) for line in _ra_lines(block)]
              + (commit if "(below)" in step else []))
             for number, _, step in _steps(text)]
    assert sum("(below)" in step for _, step, _ in steps) == len(commit), verb
    return steps


def _runbook_commands(verb: str, inside: str = "", start: int = 1) -> list[str]:
    """The commands of the verb's runbook in the order a session runs them, from step start on.
    Run by the verb inside, it leaves out each step that begins 'Unless <inside> runs <verb>', as
    update-status leaves out its pull and push inside session-end."""
    return [line for number, step, lines in _runbook_steps(verb)
            if number >= start and not (inside and step.startswith(
                f"{number}. Unless {inside} runs {verb}"))
            for line in lines]


def _runs(verb: str) -> dict[int, tuple[str, int]]:
    """The steps of the verb's runbook that run another verb: {step: (that verb, its first step)}."""
    runs: dict[int, tuple[str, int]] = {}
    for number, step, _ in _runbook_steps(verb):
        found = {(other, int(first or 1)) for other, first in _RUNS_VERB.findall(step)
                 if other in VERBS and other != verb}
        assert len(found) <= 1, f"{verb} step {number} runs {sorted(found)}"
        if found:
            [runs[number]] = found
    return runs


def _skill_steps(body: str) -> list[tuple[int, list[str], list[str]]]:
    """The steps of a skill's '## Steps': (number, the commands of the step's own fences, those
    of the fences indented deeper than the step's text, which show a verb the step runs)."""
    text = body[body.index(SKILL_HEADINGS[1]) : body.index(SKILL_HEADINGS[2])]
    steps: list[tuple[int, list[str], list[str]]] = []
    for number, column, step in _steps(text):
        own: list[str] = []
        nested: list[str] = []
        for indent, block in _fenced(step):
            (nested if len(indent) > column else own).extend(_ra_lines(block))
        steps.append((number, own, nested))
    return steps


@pytest.mark.parametrize("verb", _cases([*VERBS, "project-init"]))
def test_every_verb_has_a_skill_that_cites_protocol(verb):
    path = SKILLS / verb / "SKILL.md"
    assert path.exists(), verb
    meta, body = parse(path)
    assert meta["name"] == verb and len(meta["description"]) > 40
    assert "PROTOCOL.md §" in body
    assert _headings(body) == SKILL_HEADINGS
    # No drift: a skill copies its commands from the runbooks, so every 'python protocol/ra.py'
    # line it shows is a line PROTOCOL.md shows; project-init runs the framework's own ra.py.
    shown = {line.strip() for block in _blocks(_read(PROTOCOL)) for line in block.splitlines()}
    lines = [line.strip() for block in _blocks(body) for line in block.splitlines()]
    commands = [line for line in lines if _RUNS_RA.match(line)]
    assert commands, f"{verb} shows no ra command in a fenced block"
    for line in commands:
        if line.startswith(f"{COMMAND} "):
            assert line in shown, f"{verb} shows a command that PROTOCOL.md does not: {line}"
        _check_command(line, build_parser())


@pytest.mark.parametrize("verb", _cases(VERBS))
def test_every_skill_shows_its_runbook_step_by_step(verb):
    # The other way (Rulings R53 and R54): the skill numbers its steps as the runbook does, and
    # each step's own fences show exactly the commands of that runbook step.
    path = SKILLS / verb / "SKILL.md"
    assert path.exists(), verb
    steps = _skill_steps(parse(path)[1])
    runbook = _runbook_steps(verb)
    assert [number for number, _, _ in steps] == [number for number, _, _ in runbook], (
        f"{verb} does not number its steps as its runbook does")
    for (number, own, _), (_, _, wanted) in zip(steps, runbook):
        assert own == wanted, f"{verb} step {number} shows {own}, its runbook step {wanted}"
    # A step that runs another verb shows that verb's commands in a nested block, from the step
    # it starts at, without the steps it leaves out there; no other step has a nested block.
    runs = _runs(verb)
    nested = {number: lines for number, _, lines in steps if lines}
    assert sorted(nested) == sorted(runs), (
        f"{verb} nests commands at steps {sorted(nested)}, its runbook runs a verb at {runs}")
    for number, (other, first) in runs.items():
        wanted = _runbook_commands(other, inside=verb, start=first)
        assert nested[number] == wanted, f"{verb} step {number} must show {other}'s {wanted}"


def test_every_section_a_skill_cites_exists():
    # A skill points into PROTOCOL.md by section number, as in '§9' or '§1–5'.
    paths = sorted(SKILLS.glob("*/SKILL.md"))
    assert paths
    for path in paths:
        cited = re.findall(r"§(\d+)(?:–(\d+))?", _read(path))
        numbers = [int(number) for pair in cited for number in pair if number]
        assert numbers and all(1 <= n <= len(SECTIONS) for n in numbers), (path, numbers)


def test_the_pending_skills_are_the_missing_ones():
    # A skill that lands must leave PENDING_SKILLS even when it breaks the convention, which
    # its strict xfail alone would hide.
    assert [verb for verb in VERBS if not (SKILLS / verb / "SKILL.md").exists()] == PENDING_SKILLS


def test_the_manifest_names_the_plugin_and_each_skill_its_folder():
    manifest = json.loads(_read(PLUGIN / ".claude-plugin" / "plugin.json"))
    assert manifest["name"] == "ra-agent"
    skills = sorted(SKILLS.glob("*/SKILL.md"))
    assert skills
    for path in skills:
        meta, _ = parse(path)
        assert list(meta) == ["name", "description"], path  # the convention's only fields
        assert meta["name"] == path.parent.name, path
