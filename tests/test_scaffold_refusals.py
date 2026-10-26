"""Tests for what init_project refuses: a bad template, a bad destination, a bad value.

Each refusal raises before anything is created or changed. The project that init_project makes
is tested in test_scaffold.py.
"""

import re

import pytest
from conftest import _init_project


@pytest.mark.parametrize("missing", ["PROJECT.md", "PROTOCOL.md", "protocol/ra/scaffold.py"])
def test_a_directory_without_a_template_file_is_refused(tmp_path, template, missing):
    (template / missing).unlink()
    dest = tmp_path / "p"
    with pytest.raises(ValueError, match=re.escape(missing)):
        _init_project(dest, template)
    assert not dest.exists()


@pytest.mark.parametrize("name", ["empty", "nowhere"])
def test_an_empty_or_missing_directory_is_not_a_template(tmp_path, name):
    (tmp_path / "empty").mkdir()
    dest = tmp_path / "p"
    with pytest.raises(ValueError, match="not the RA template"):
        _init_project(dest, tmp_path / name)
    assert not dest.exists()


def test_a_template_with_a_git_entry_is_refused(tmp_path, template):
    (template / ".git").mkdir()
    dest = tmp_path / "p"
    with pytest.raises(ValueError, match="run ra init from the framework repository"):
        _init_project(dest, template)
    assert not dest.exists()


def test_a_project_is_not_a_template_for_another_project(tmp_path, repo):
    dest = tmp_path / "second"
    with pytest.raises(ValueError, match="not inside a project"):
        _init_project(dest, repo)
    assert not dest.exists()


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("---\nother: 1\n---\nbody\n", "needs 'version: <x.y.z>' in its frontmatter, got None"),
        ("---\nversion:\n---\nbody\n", "needs 'version: <x.y.z>' in its frontmatter, got None"),
        ("---\nversion: 1\n---\nbody\n", "needs 'version: <x.y.z>' in its frontmatter, got 1"),
        ("---\nversion: ' '\n---\nbody\n", "needs 'version: <x.y.z>' in its frontmatter, got ' '"),
        ("no frontmatter\n", "no frontmatter block"),
    ],
    ids=["no-key", "empty", "not-text", "blank", "no-frontmatter"],
)
def test_a_template_without_a_usable_version_is_refused(tmp_path, template, text, message):
    (template / "PROTOCOL.md").write_text(text, encoding="utf-8")
    dest = tmp_path / "p"
    with pytest.raises(ValueError, match=message):
        _init_project(dest, template)
    assert not dest.exists()


def test_a_destination_that_is_a_file_is_refused_and_left_alone(tmp_path):
    dest = tmp_path / "p"
    dest.write_text("mine\n", encoding="utf-8")
    with pytest.raises(FileExistsError, match="not an empty directory"):
        _init_project(dest)
    assert dest.read_text(encoding="utf-8") == "mine\n"


def test_a_destination_with_content_is_refused_and_left_alone(tmp_path, files_of):
    dest = tmp_path / "p"
    (dest / "sub").mkdir(parents=True)
    (dest / "sub" / "keep.txt").write_text("keep\n", encoding="utf-8")
    with pytest.raises(FileExistsError, match="not an empty directory"):
        _init_project(dest)
    assert files_of(dest) == {"sub/keep.txt"} and not (dest / ".git").exists()


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"name": ""}, "name must not be empty"),
        ({"name": " \t"}, "name must not be empty"),
        ({"name": "two\nlines"}, "name must be one line"),
        ({"person": ""}, "person must not be empty"),
        ({"person": "Fan\r\nLee"}, "person must be one line"),
        ({"role": "  "}, "role must not be empty"),
        ({"role": "PI\nLead"}, "role must be one line"),
        ({"git_author": ""}, "git author must not be empty"),
        ({"git_author": "Fan"}, "Name <email>"),
        ({"git_author": "Fan <>"}, "Name <email>"),
        ({"git_author": "<fan@x>"}, "Name <email>"),
        ({"git_author": "Fan <fan>"}, "Name <email>"),
        ({"git_author": "Fan fan@x"}, "Name <email>"),
        ({"git_author": "Fan <fan@x> (PI)"}, "Name <email>"),
        ({"git_author": "Fan <fan@x>\nLee <lee@x>"}, "git author must be one line"),
        ({"platforms": []}, "platforms must not be empty"),
        ({"platforms": ["vim"]}, "platform must be one of claude-code, codex"),
        ({"platforms": ["claude-code", "vim"]}, "platform must be one of claude-code, codex"),
        ({"platforms": ["codex", "codex"]}, "platforms must not repeat 'codex'"),
    ],
)
def test_a_bad_value_is_refused_before_anything_is_written(tmp_path, fields, message):
    dest = tmp_path / "p"
    with pytest.raises(ValueError, match=message):
        _init_project(dest, **fields)
    assert not dest.exists()
