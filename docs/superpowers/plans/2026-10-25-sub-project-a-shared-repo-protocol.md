# Sub-project A: Shared-Repo Protocol — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A project-repo template (PROTOCOL.md, templates, a `ra` CLI) plus a Claude Code plugin of skills, such that any Claude Code or Codex session follows the same rules for literature, questions, knowledge, decisions and work log in a shared git repository.

**Architecture:** The framework repo holds `template/` (copied into every new project by `ra init`) and `plugin/` (skills installed per person). All deterministic work — scaffolding, frontmatter, dedup, structured commits, the digest, the `check` validator — lives in `template/protocol/ra/`, a dependency-light Python package invoked as `python protocol/ra.py <cmd>` inside any project repo. Skills contain no logic of their own: each cites the PROTOCOL.md section it implements and calls the CLI. Phase 1 builds the template and CLI with pytest coverage; Phase 2 writes PROTOCOL.md and the skills; Phase 3 adds sync, the two-clone handoff test, the Codex runnable-alone check and the pilot kit.

**Tech Stack:** Python ≥ 3.10, PyYAML, pytest; git ≥ 2.30 via `subprocess`; Markdown + YAML frontmatter; Claude Code plugin (`.claude-plugin/plugin.json` + `skills/`), Codex `AGENTS.md`.

**Spec:** `docs/superpowers/specs/2026-10-25-ra-agent-framework-stage0-design.md`

## Global Constraints

- Python ≥ 3.10; runtime dependencies: PyYAML only; test dependency: pytest only. No GitPython; git is called with `subprocess.run([...], check=True, text=True)`.
- All paths via `pathlib`; must run on macOS, Linux and Windows.
- Everything under `template/protocol/` must work with no plugin installed (spec §13, runnable-alone test).
- Shared files are written in English; UTF-8 everywhere (Chinese author names, `µ`, `–` must round-trip).
- Commit type tags are exactly: `literature` `question` `knowledge` `decision` `log` `status` `protocol` (spec §9).
- Commit message format verbatim from spec §9: subject `[<tag>] <text>`, blank line, trailers `Person: <name>`, `Agent: <claude-code|codex>`, `Links: <comma-separated paths>`.
- Filenames verbatim from spec §6: `questions/Q-<YYYY-MM-DD>-<slug>.md`, `decisions/D-<YYYY-MM-DD>-<slug>.md`, `literature/<citekey>.md`, `literature/pdf/<citekey>.pdf`, `log/<YYYY-MM-DD>-<person>-<platform>-<HHMM>.md`, `knowledge/<topic>.md`. Slugs, citekeys, topics: `[a-z0-9-]+`.
- Human gate prompts verbatim from spec §8 (three choices: `Commit / Edit / Skip?`).
- Protocol version string lives in PROTOCOL.md frontmatter `version: 0.1.0` and is stamped into PROJECT.md on init.

## Review Focus

1. A human commits by hand with an unstructured message — the digest must list it as untagged, never crash (Task 6).
2. Two people propose the same question slug on the same day — `ra new question` must refuse to overwrite (Task 2).
3. A literature record whose `pdf:` path doesn't exist or doesn't match its citekey — `check` must report `PDF_MISSING` (Task 4).
4. A topic file created without its registry line in `knowledge/README.md` — `check` must report `TOPIC_UNREGISTERED` (Task 4).
5. An accepted decision edited anywhere other than `status:` / `superseded-by:` — `check` must report `DECISION_EDITED` using git history, not file content alone (Task 4).

---

## File Structure

```
ra-agent-framework/
  README.md                                   onboarding: install plugin, init or clone a project, go
  docs/superpowers/specs/…stage0-design.md
  docs/superpowers/plans/…sub-project-a….md
  template/                                   copied verbatim into each new project repo
    PROJECT.md  PROTOCOL.md  CLAUDE.md  AGENTS.md  .gitattributes  .gitignore
    knowledge/README.md  knowledge/glossary.md
    questions/.gitkeep  decisions/.gitkeep  literature/pdf/.gitkeep  log/.gitkeep
    protocol/
      ra.py                                   entry: python protocol/ra.py <cmd> — argparse only, dispatches to ra/
      requirements.txt                        pyyaml
      templates/{literature,question,decision,log,topic}.md
      ra/
        __init__.py
        frontmatter.py   parse / dump / write
        literature.py    claim parser
        newfile.py       new_* file creators
        check.py         validators → Findings
        dedup.py         DOI / arXiv / title lookup
        commit.py        structured commit
        digest.py        what's-new from git log
        scaffold.py      init_project
        sync.py          pull / push / protected conflicts
        stats.py         pilot metrics
  plugin/
    .claude-plugin/plugin.json
    skills/<verb>/SKILL.md   for: project-init session-start session-end add-literature reread-literature
                             propose-question close-question propose-knowledge propose-decision
                             accept-decision supersede-decision update-status
  examples/smoke-plume/                       hand-populated example project (Task 8)
  tests/
    conftest.py          fixtures: repo (fresh init in tmp), make_pdf, git_identity
    test_frontmatter.py test_newfile.py test_literature.py test_check.py test_dedup.py
    test_commit.py test_digest.py test_scaffold.py test_sync.py test_stats.py
    test_docs.py         lints PROTOCOL.md / CLAUDE.md / AGENTS.md / skills
    test_handoff.py      two-clone scenario
```

---

# Phase 1 — Template and CLI

### Task 1: Repo skeleton and frontmatter module

**Files:**
- Create: `template/protocol/ra/__init__.py`, `template/protocol/ra/frontmatter.py`, `template/protocol/ra.py`, `template/protocol/requirements.txt`, `tests/conftest.py`, `pyproject.toml` (pytest config, `pythonpath = ["template/protocol"]`)
- Test: `tests/test_frontmatter.py`

**Interfaces:**
- Produces: `class FrontmatterError(ValueError)`; `parse(path: Path) -> tuple[dict, str]`; `dump(meta: dict, body: str) -> str`; `write(path: Path, meta: dict, body: str) -> None`. YAML block delimited by `---` lines; `dump` uses `yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)`.
- `tests/conftest.py` produces fixtures: `git_identity(repo: Path, name: str, email: str)`; `make_pdf(path: Path, text: str) -> None` (hand-written minimal single-page PDF — header, catalog, pages, page, content stream with the text, xref, trailer; no library).

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/test_frontmatter.py -v` → FAIL, `ImportError`
- [ ] **Step 3: Implement `frontmatter.py` with the signatures above; `ra.py` with an argparse skeleton that prints usage; `requirements.txt` = `pyyaml`**
- [ ] **Step 4: Run to verify pass** — `pytest tests/test_frontmatter.py -v` → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(ra): frontmatter parse/dump and CLI skeleton"`

### Task 2: File templates and `ra new`

**Files:**
- Create: `template/protocol/templates/literature.md`, `question.md`, `decision.md`, `log.md`, `topic.md` (bodies copied from spec §10.3 and §11, frontmatter values as `{placeholders}`); `template/protocol/ra/newfile.py`
- Modify: `template/protocol/ra.py` — subcommand `new {question,decision,literature,log,topic}`
- Test: `tests/test_newfile.py`

**Interfaces:**
- Consumes: `frontmatter.write`
- Produces: `new_question(repo: Path, slug: str, title: str, person: str, agent: str, day: date) -> Path`; `new_decision(repo, slug, title, person, agent, day, links: list[str]) -> Path`; `new_literature(repo, citekey: str, meta: dict, pdf_src: Path) -> Path` (copies PDF to `literature/pdf/<citekey>.pdf`, sets `pdf:` and `readers[0]`); `new_log(repo, person, agent, start: datetime) -> Path`; `new_topic(repo, topic: str, scope: str) -> Path` (creates `knowledge/<topic>.md` and appends `- <topic> — <scope>` to `knowledge/README.md`). All raise `FileExistsError` if the target exists; all validate slug/citekey/topic against `^[a-z0-9-]+$` and raise `ValueError`.

- [ ] **Step 1: Write the failing tests**

```python
def test_question_path_and_frontmatter(repo):
    p = new_question(repo, "plume-baselines", "What are the strongest baselines?", "Fan", "claude-code", date(2026,10,25))
    assert p == repo/"questions"/"Q-2026-10-25-plume-baselines.md"
    m, _ = parse(p)
    assert m["id"] == "Q-2026-10-25-plume-baselines" and m["status"] == "open"
    assert m["proposed-by"] == {"person": "Fan", "agent": "claude-code", "date": "2026-10-25"}

def test_same_slug_same_day_refused(repo):
    new_question(repo, "x", "t", "Fan", "codex", date(2026,10,25))
    with pytest.raises(FileExistsError):
        new_question(repo, "x", "t2", "Lee", "claude-code", date(2026,10,25))

def test_literature_copies_pdf_and_sets_reader(repo, make_pdf):
    src = repo.parent/"s.pdf"; make_pdf(src, "hello")
    p = new_literature(repo, "smith2024-plume-goes", {"title": "T", "year": 2024, "person": "Fan", "agent": "codex", "date": "2026-10-25"}, src)
    m, _ = parse(p)
    assert (repo/"literature"/"pdf"/"smith2024-plume-goes.pdf").exists()
    assert m["pdf"] == "literature/pdf/smith2024-plume-goes.pdf"
    assert m["readers"][0]["read"] == "full-text"

def test_log_filename_uses_start_time(repo):
    p = new_log(repo, "fan", "codex", datetime(2026,10,25,14,32))
    assert p.name == "2026-10-25-fan-codex-1432.md"

def test_topic_registers_in_readme(repo):
    new_topic(repo, "goes-abi", "GOES-16 ABI instrument facts")
    assert "- goes-abi — GOES-16 ABI instrument facts" in (repo/"knowledge"/"README.md").read_text(encoding="utf-8")

def test_bad_slug_rejected(repo):
    with pytest.raises(ValueError):
        new_decision(repo, "Eval Metric", "t", "Fan", "codex", date(2026,10,25), [])
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/test_newfile.py -v` → FAIL
- [ ] **Step 3: Write the five templates; implement `newfile.py`; wire `ra new`**
- [ ] **Step 4: Run to verify pass** — `pytest tests/test_newfile.py -v` → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(ra): file templates and ra new"`

### Task 3: Claim parser

**Files:**
- Create: `template/protocol/ra/literature.py`
- Test: `tests/test_literature.py`

**Interfaces:**
- Produces: `@dataclass Claim(text: str, where: str|None, bears_on: list[str], kind: str|None, basis: str|None, by: str|None, verified_by: list[str], disputed_by: list[str], line: int)`; `parse_claims(body: str) -> list[Claim]` reads the bullet list under the heading `## Claims for this project` (sub-bullets `- where:`, `- bears on:`, `- kind: … · basis: …`, `- by:`, `- verified-by:`, `- disputed-by:`; `—` means empty list; multiple names separated by `;`).

- [ ] **Step 1: Write the failing tests**

```python
BODY = """## Claims for this project
- Transformer beats U-Net by 4.2 mIoU
  - where: Table 3, p.7
  - bears on: Q-2026-10-25-plume-baselines — supports
  - kind: result · basis: stated by paper
  - by: Fan · codex · 2026-10-25
  - verified-by: Lee · claude-code · 2026-10-28
  - disputed-by: —
- Dataset has 1,204 scenes
  - bears on: Q-2026-10-25-plume-baselines — supports
  - by: Fan · codex · 2026-10-25
## Notes
"""
def test_parses_fields_and_missing_where():
    c = parse_claims(BODY)
    assert len(c) == 2
    assert c[0].where == "Table 3, p.7" and c[0].verified_by == ["Lee · claude-code · 2026-10-28"] and c[0].disputed_by == []
    assert c[1].where is None and c[1].bears_on == ["Q-2026-10-25-plume-baselines"]
```

- [ ] **Step 2: Run to verify failure** → FAIL
- [ ] **Step 3: Implement `literature.py`** — line-oriented scan; do not use a Markdown library.
- [ ] **Step 4: Run to verify pass** → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(ra): claim parser"`

### Task 4: `ra check`

**Files:**
- Create: `template/protocol/ra/check.py`
- Modify: `template/protocol/ra.py` — subcommand `check` (exit 1 if any finding; prints `CODE path: message` per line)
- Test: `tests/test_check.py`

**Interfaces:**
- Consumes: `frontmatter.parse`, `literature.parse_claims`
- Produces: `@dataclass Finding(code: str, path: Path, message: str)`; `run_checks(repo: Path) -> list[Finding]`. Codes and rules: `FM_INVALID` (unparseable frontmatter or required key missing — required keys per type from spec §10.3/§11); `BAD_FILENAME` (pattern mismatch per Global Constraints); `CLAIM_NO_WHERE`; `PDF_MISSING` (`pdf:` absent, file absent, or not `literature/pdf/<citekey>.pdf`); `DUP_LITERATURE` (two records share a `doi` or `arxiv`); `DISPUTED_IN_KNOWLEDGE` (a knowledge fact line's `src:` names a citekey + `where` whose claim has non-empty `disputed_by`); `TOPIC_UNREGISTERED` (a `knowledge/*.md` other than README/glossary without a `- <topic> — ` line in README); `DECISION_EDITED` — for each decision with status `accepted` or `superseded`: find the oldest commit whose diff added `status: accepted` (`git log --reverse -S"status: accepted" --format=%H -- <path>`), then `git diff <sha> HEAD -- <path>`; any changed line not starting with `status:` or `superseded-by:` is a finding. `decision_edited_in_place(repo: Path, path: Path) -> bool` is a public helper.

- [ ] **Step 1: Write the failing tests** — one passing fixture (fresh `repo` → `run_checks(repo) == []`) and one test per code. Representative:

```python
def test_claim_without_where_flagged(repo, make_pdf):
    p = _lit(repo, make_pdf, "a2024-x", claims=[("Some claim", None)])
    assert {f.code for f in run_checks(repo)} == {"CLAIM_NO_WHERE"}

def test_pdf_path_must_match_citekey(repo, make_pdf):
    p = _lit(repo, make_pdf, "a2024-x"); m, b = parse(p); m["pdf"] = "literature/pdf/other.pdf"; write(p, m, b)
    assert "PDF_MISSING" in {f.code for f in run_checks(repo)}

def test_accepted_decision_body_edit_flagged(repo):
    p = _decision(repo, "eval-metric", status="proposed"); _commit_all(repo, "[decision] proposed")
    m, b = parse(p); m["status"] = "accepted"; m["accepted-by"] = "Fan · 2026-10-26"; write(p, m, b); _commit_all(repo, "[decision] accepted")
    m, b = parse(p); write(p, m, b + "\nchanged rationale\n"); _commit_all(repo, "oops")
    assert "DECISION_EDITED" in {f.code for f in run_checks(repo)}

def test_superseded_by_edit_allowed(repo):
    # same setup as above, then set superseded-by and status: superseded only
    assert "DECISION_EDITED" not in {f.code for f in run_checks(repo)}
```

Helpers added to `tests/conftest.py` in this task (and used by Tasks 5, 6, 15): `_lit(repo: Path, make_pdf, citekey: str, *, doi: str|None=None, arxiv: str|None=None, title: str="T", claims: list[tuple[str, str|None]] = [("c", "p.1")]) -> Path` (a valid record via `new_literature`, then claims written in the §10.3 format); `_decision(repo: Path, slug: str, *, status: str) -> Path`; `_commit_all(repo: Path, msg: str) -> None` (`git add -A && git commit -m msg`).

- [ ] **Step 2: Run to verify failure** → FAIL
- [ ] **Step 3: Implement `check.py`; wire `ra check`**
- [ ] **Step 4: Run to verify pass** — `pytest tests/test_check.py -v` → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(ra): check validator"`

### Task 5: `ra dedup`

**Files:**
- Create: `template/protocol/ra/dedup.py`
- Modify: `template/protocol/ra.py` — `dedup [--doi] [--arxiv] [--title]` prints the matching path or `none`
- Test: `tests/test_dedup.py`

**Interfaces:**
- Produces: `normalize_title(t: str) -> str` (casefold, strip everything but `[a-z0-9]`); `find_existing(repo: Path, doi: str|None=None, arxiv: str|None=None, title: str|None=None) -> Path|None` — priority DOI, then arXiv, then normalised title (spec §10.2); DOI compared case-insensitively with any `https://doi.org/` prefix stripped.

- [ ] **Step 1: Write the failing tests**

```python
def test_doi_match_beats_title(repo, make_pdf):
    _lit(repo, make_pdf, "a2024-x", doi="10.1016/J.RSE.2024.1", title="Alpha")
    _lit(repo, make_pdf, "b2024-y", doi="10.1/other", title="Beta")
    assert find_existing(repo, doi="https://doi.org/10.1016/j.rse.2024.1", title="Beta").name == "a2024-x.md"

def test_title_normalisation(repo, make_pdf):
    _lit(repo, make_pdf, "c2023-z", title="Smoke-Plume Segmentation: A Study")
    assert find_existing(repo, title="smoke plume segmentation a study").name == "c2023-z.md"
    assert find_existing(repo, title="Unrelated") is None
```

- [ ] **Step 2: Run to verify failure** → FAIL
- [ ] **Step 3: Implement `dedup.py`; wire `ra dedup`**
- [ ] **Step 4: Run to verify pass** → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(ra): literature dedup lookup"`

### Task 6: `ra commit` and `ra digest`

**Files:**
- Create: `template/protocol/ra/commit.py`, `template/protocol/ra/digest.py`
- Modify: `template/protocol/ra.py` — `commit --type --subject --person --agent --links … -- <paths>`; `digest --person [--fallback 20]`
- Test: `tests/test_commit.py`, `tests/test_digest.py`

**Interfaces:**
- Produces (commit): `TYPE_TAGS: tuple[str, ...]`; `format_message(type_tag: str, subject: str, person: str, agent: str, links: list[str]) -> str`; `commit(repo: Path, paths: list[Path], type_tag, subject, person, agent, links) -> str` (returns sha; `ValueError` on unknown tag or agent not in `{"claude-code","codex"}`).
- Produces (digest): `@dataclass Commit(sha: str, date: str, type_tag: str|None, subject: str, person: str|None, agent: str|None, links: list[str])`; `parse_message(msg: str) -> Commit` (sha/date filled by caller; untagged subject → `type_tag=None`); `commits_since_last(repo: Path, person: str, fallback: int = 20) -> list[Commit]` — last commit by `--author=<person>` → `git log <sha>..HEAD`; none → `git log -n <fallback>`; newest first, as git returns them; `render(commits: list[Commit]) -> str` grouped by tag, untagged last under `other`.

- [ ] **Step 1: Write the failing tests**

```python
def test_message_format_verbatim():
    assert format_message("literature", "added Smith 2024", "Fan", "codex", ["literature/smith2024.md"]) == \
        "[literature] added Smith 2024\n\nPerson: Fan\nAgent: codex\nLinks: literature/smith2024.md\n"

def test_bad_tag_rejected(repo):
    with pytest.raises(ValueError):
        commit(repo, [], "experiment", "x", "Fan", "codex", [])

def test_since_last_commit_and_untagged_tolerated(repo):
    git_identity(repo, "Fan", "fan@x")
    p1 = new_log(repo, "fan", "codex", datetime(2026,10,25,9,0)); commit(repo, [p1], "log", "s1", "Fan", "codex", [])
    git_identity(repo, "Lee", "lee@x")
    p2 = new_question(repo, "a", "t", "Lee", "claude-code", date(2026,10,25)); commit(repo, [p2], "question", "added A", "Lee", "claude-code", ["questions/Q-2026-10-25-a.md"])
    (repo/"PROJECT.md").write_text((repo/"PROJECT.md").read_text(encoding="utf-8") + "\n", encoding="utf-8"); _commit_all(repo, "fixed typo by hand")
    cs = commits_since_last(repo, "Fan")
    assert [c.type_tag for c in cs] == [None, "question"]      # newest first
    assert "other" in render(cs)

def test_fallback_when_person_has_no_commits(repo):
    for i in range(25): _commit_all(repo, f"[log] s{i}")
    assert len(commits_since_last(repo, "Nobody")) == 20
```

- [ ] **Step 2: Run to verify failure** → FAIL
- [ ] **Step 3: Implement both modules; wire both subcommands**
- [ ] **Step 4: Run to verify pass** → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(ra): structured commit and digest"`

### Task 7: `ra init`

**Files:**
- Create: `template/protocol/ra/scaffold.py`, `template/PROJECT.md`, `template/.gitattributes` (`*.pdf binary`), `template/.gitignore` (`.ra/`, `NEWS.md`, `__pycache__/`), `template/knowledge/README.md`, `template/knowledge/glossary.md`, `.gitkeep` files
- Modify: `template/protocol/ra.py` — `init <dest> --name --person --git-author --platforms --role`
- Test: `tests/test_scaffold.py`; update `tests/conftest.py` so the `repo` fixture uses `init_project`

**Interfaces:**
- Produces: `init_project(dest: Path, name: str, person: str, git_author: str, platforms: list[str], role: str, template_dir: Path | None = None) -> None` — copies `template/`, fills PROJECT.md title and members row (spec §6 template), stamps `protocol-version`, runs `git init`, first commit message `[protocol] initialise project from RA_Agent template 0.1.0` with trailers.

- [ ] **Step 1: Write the failing tests**

```python
def test_init_layout_and_first_commit(tmp_path):
    init_project(tmp_path/"p", "Smoke Plume", "Fan", "Fan <fan@x>", ["claude-code","codex"], "PI")
    for d in ["questions","knowledge","decisions","literature/pdf","log","protocol/templates"]:
        assert (tmp_path/"p"/d).is_dir()
    assert ".ra/" in (tmp_path/"p"/".gitignore").read_text()
    assert "| Fan | Fan <fan@x> | claude-code, codex | PI |" in (tmp_path/"p"/"PROJECT.md").read_text(encoding="utf-8")
    log = subprocess.run(["git","log","--format=%s"], cwd=tmp_path/"p", capture_output=True, text=True).stdout
    assert log.strip() == "[protocol] initialise project from RA_Agent template 0.1.0"
    assert run_checks(tmp_path/"p") == []
```

- [ ] **Step 2: Run to verify failure** → FAIL
- [ ] **Step 3: Implement `scaffold.py`, the template files, wire `ra init`; switch the `repo` fixture to `init_project`**
- [ ] **Step 4: Run the whole suite** — `pytest -v` → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(ra): project scaffolding"`

### Task 8: Example project

**Files:**
- Create: `examples/smoke-plume/` via `ra init`, then hand-populate: 3 literature records (one `core` with two verified claims and one disputed, one `supporting`, one `not-useful`) with PDFs generated by `make_pdf` (replace with real open-access PDFs before the pilot), 2 open questions, 1 answered question, `knowledge/goes-abi.md` with two facts including a `CONFLICT` pair, 1 accepted decision, 1 superseded decision pair, 3 log entries from two people and both platforms; every change as a structured commit
- Test: `tests/test_example.py`

- [ ] **Step 1: Write the failing test**

```python
def test_example_project_is_clean_and_digestible():
    repo = Path("examples/smoke-plume")
    assert run_checks(repo) == []
    assert "literature" in render(commits_since_last(repo, "Lee"))
    assert stats(repo)["unverified_claims"] >= 1     # stats from Task 15; mark xfail until then
```

- [ ] **Step 2: Populate the example by hand following spec §10.3 and §11 exactly; commit each item with `ra commit`**
- [ ] **Step 3: Run** — `pytest tests/test_example.py -v` → PASS (stats line xfail)
- [ ] **Step 4: Commit** — `git commit -m "docs: example project smoke-plume"`

# Phase 2 — Protocol text and skills

### Task 9: PROTOCOL.md, CLAUDE.md, AGENTS.md

**Files:**
- Create: `template/PROTOCOL.md` (frontmatter `version: 0.1.0`, 16 sections in the order of spec §14, each verb in §6 as a numbered runbook with exact `ra` commands and exact gate prompts from spec §8), `template/CLAUDE.md` and `template/AGENTS.md` (each: one instruction to read PROTOCOL.md first and follow it)
- Test: `tests/test_docs.py`

**Interfaces:**
- Produces: `VERBS = ["session-start","session-end","add-literature","reread-literature","propose-question","close-question","propose-knowledge","propose-decision","accept-decision","supersede-decision","update-status"]` exported from `tests/test_docs.py` for Task 10.

- [ ] **Step 1: Write the failing tests**

```python
SECTIONS = ["Purpose and scope","Bootstrap","Repo map","Information types and write rules","Session procedure","Verbs","Literature rules","Human gates","Conflict rules","Naming conventions","Commit conventions","File templates","Never-in-repo list","Health checks","Glossary","Protocol version and change procedure"]
def test_protocol_has_all_sections_in_order():
    text = Path("template/PROTOCOL.md").read_text(encoding="utf-8")
    idx = [text.index(f"## {i+1}. {s}") for i, s in enumerate(SECTIONS)]
    assert idx == sorted(idx)

def test_every_verb_has_a_runbook_and_gate_prompts_are_verbatim():
    text = Path("template/PROTOCOL.md").read_text(encoding="utf-8")
    for v in VERBS: assert f"### {v}" in text
    assert "Commit / Edit / Skip?" in text and "Proposed for the shared repo — KNOWLEDGE" in text

def test_entry_files_are_single_instruction():
    for f in ["template/CLAUDE.md","template/AGENTS.md"]:
        lines = [l for l in Path(f).read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) <= 3 and "PROTOCOL.md" in " ".join(lines)
```

- [ ] **Step 2: Run to verify failure** → FAIL
- [ ] **Step 3: Write PROTOCOL.md as a runbook** — each verb: Preconditions · Steps (imperative, with the exact `python protocol/ra.py …` call) · Ask the human (verbatim prompt) · Files changed · Commit (tag + subject pattern). Include the use-versus-navigate definition (spec §10.1) and the conflict-stop rule (spec §12) word for word.
- [ ] **Step 4: Run** — `pytest tests/test_docs.py -v` → PASS
- [ ] **Step 5: Manual runnable-alone check in Claude Code** — in `examples/smoke-plume`, with the plugin *not* installed, prompt: "Add this paper to the project: <path to any open-access PDF>". Expected: the session reads PROTOCOL.md, runs `ra dedup`, reads the PDF, writes a record with `where` on every claim, commits with a `[literature]` message, and `ra check` passes. Fix PROTOCOL.md wherever the session hesitated or deviated.
- [ ] **Step 6: Commit** — `git commit -m "docs: PROTOCOL.md v0.1.0 and platform entry files"`

### Task 10: Plugin manifest, `project-init`, `session-start`, `session-end`

**Files:**
- Create: `plugin/.claude-plugin/plugin.json`; `plugin/skills/project-init/SKILL.md`, `plugin/skills/session-start/SKILL.md`, `plugin/skills/session-end/SKILL.md`
- Modify: `tests/test_docs.py`

**Interfaces:**
- Consumes: PROTOCOL.md section numbers; `ra init`, `ra digest`, `ra check`, `ra new log`, `ra commit`, and Task 14's `ra sync pull|push|conflicts`
- Produces: the skill file convention every later skill follows — frontmatter `name`, `description` (pushy, per skill-creator guidance), body that (1) names the PROTOCOL.md section it implements, (2) lists the `ra` calls in order, (3) states the stop conditions. No rule text duplicated from PROTOCOL.md.

- [ ] **Step 1: Verify the current plugin manifest format** — check Claude Code's plugin documentation for the `plugin.json` fields and `skills/` layout before writing; record the doc URL in `plugin/README.md`.
- [ ] **Step 2: Write the failing test**

```python
def test_every_verb_has_a_skill_that_cites_protocol():
    for v in VERBS + ["project-init"]:
        p = Path(f"plugin/skills/{v}/SKILL.md"); assert p.exists(), v
        m, body = parse(p)
        assert m["name"] == v and len(m["description"]) > 40
        assert "PROTOCOL.md §" in body
```

(Fails for all verbs until Tasks 10–13 are complete; keep the test, let it fail on the missing ones.)

- [ ] **Step 3: Write the three skills** — `session-start`: pull → PROJECT.md → `ra digest --person` → open questions → relevant knowledge → `ra check` summary; `session-end`: `ra new log` → fill → `[log]` commit → rewrite "Current status" → `[status]` commit → push; `project-init`: `ra init` with the member row from the user, then open PROTOCOL.md.
- [ ] **Step 4: Manual test in Claude Code with the plugin installed** — in `examples/smoke-plume`: "start my session" then "end my session". Expected: digest shown, a new `log/` file with the five headings filled, two commits `[log]` and `[status]`, `ra check` clean.
- [ ] **Step 5: Commit** — `git commit -m "feat(plugin): manifest, project-init, session-start, session-end"`

### Task 11: `add-literature` and `reread-literature`

**Files:**
- Create: `plugin/skills/add-literature/SKILL.md`, `plugin/skills/reread-literature/SKILL.md`

**Interfaces:**
- Consumes: `ra dedup`, `ra new literature`, `ra check`, `ra commit`; PROTOCOL.md §7 (literature rules)

- [ ] **Step 1: Write both skills** — `add-literature`: ask for PDF path → extract DOI/arXiv/title → `ra dedup`; match → hand off to `reread-literature`; none → read the full PDF → `ra new literature` → fill summary, relevance, claims (each with `where`, `kind`, `basis`, `by`) → for any claim bearing on no existing question, invoke `propose-question` first → `ra check` → `[literature] added <citekey> — <title fragment>` commit. `reread-literature`: read the full PDF → for each existing claim open its `where` and append exactly one of `verified-by` / `disputed-by` with reason → append new claims → refine summary with a `revised:` line → add self to `readers` → `ra check` → `[literature] re-read <citekey> — verified N, disputed N, added N claims`.
- [ ] **Step 2: Manual test** — ingest one real open-access paper as Fan/claude-code; then, as a second git identity, run `add-literature` on the same PDF. Expected: no second record; the first record gains a second reader, every original claim has a verified-by or disputed-by entry, `ra check` clean, two commits with the exact subject patterns.
- [ ] **Step 3: Commit** — `git commit -m "feat(plugin): add-literature and reread-literature"`

### Task 12: `propose-question`, `close-question`, `propose-knowledge`

**Files:**
- Create: the three `SKILL.md` files

**Interfaces:**
- Consumes: `ra new question`, `ra new topic`, `ra commit`; PROTOCOL.md §8 gate prompts verbatim

- [ ] **Step 1: Write the three skills** — gates fire immediately, each time; `Edit` loops back; `Skip` writes nothing shared. `propose-knowledge`: if the topic is new, the same prompt also shows the proposed registry line; on a contradiction with an existing fact, append alongside and set both status fields to `CONFLICT with …`. `close-question` is human-initiated only: ask for the answering `knowledge/…` or `D-…` link, set status and `closed-by`, commit `[question] closed <id>`.
- [ ] **Step 2: Manual test** — "I learned from the PDF that ABI band 7 is 3.9 µm, 2 km" must produce the verbatim KNOWLEDGE prompt and, on `Commit`, a fact line matching spec §11 format and a `[knowledge]` commit; on `Skip`, no change to the repo.
- [ ] **Step 3: Commit** — `git commit -m "feat(plugin): question and knowledge gates"`

### Task 13: `propose-decision`, `accept-decision`, `supersede-decision`, `update-status`

**Files:**
- Create: the four `SKILL.md` files

**Interfaces:**
- Consumes: `ra new decision`, `ra check` (DECISION_EDITED), `ra commit`

- [ ] **Step 1: Write the four skills** — `accept-decision` edits only `status:` and `accepted-by:`; `supersede-decision` creates the new file with `supersedes:`, then makes the single permitted edit to the old file; `update-status` rewrites only the "Current status" section of PROJECT.md, 3–8 lines.
- [ ] **Step 2: Manual test** — propose → accept → supersede in sequence; `ra check` clean after each; then edit the accepted decision's rationale by hand and confirm `ra check` reports `DECISION_EDITED`.
- [ ] **Step 3: Run** — `pytest tests/test_docs.py -v` → PASS (all verbs now present)
- [ ] **Step 4: Commit** — `git commit -m "feat(plugin): decision verbs and update-status"`

# Phase 3 — Sync, handoff test, Codex, pilot kit

### Task 14: `ra sync`

**Files:**
- Create: `template/protocol/ra/sync.py`
- Modify: `template/protocol/ra.py` — `sync pull|push|conflicts`; `plugin/skills/session-start/SKILL.md` and `session-end/SKILL.md` to call them
- Test: `tests/test_sync.py`

**Interfaces:**
- Produces in `tests/conftest.py`: fixture `two_clones(tmp_path) -> tuple[Path, Path]` (bare origin from `init_project`, clone `a` with identity `Fan <fan@x>`, clone `b` with `Lee <lee@x>`); helper `_append_fact(repo: Path, topic: str, text: str) -> None` (creates the topic via `new_topic` if absent, appends one §11-format fact line).
- Produces: `pull(repo: Path) -> None` (`git pull --rebase=false --no-edit`), `push(repo: Path) -> None`, `unmerged_paths(repo: Path) -> list[Path]`, `protected_conflicts(repo: Path) -> list[Path]` (unmerged paths under `knowledge/` or `decisions/`). `ra sync conflicts` exits 2 when `protected_conflicts` is non-empty and prints them — the signal the skills treat as "stop".

- [ ] **Step 1: Write the failing tests**

```python
def test_protected_conflict_detected(two_clones):
    a, b = two_clones                                     # fixture: bare origin + two clones with different identities
    _append_fact(a, "goes-abi", "fact from A"); _commit_all(a, "[knowledge] a"); push(a)
    _append_fact(b, "goes-abi", "fact from B"); _commit_all(b, "[knowledge] b")
    with pytest.raises(subprocess.CalledProcessError): pull(b)
    assert protected_conflicts(b) == [Path("knowledge/goes-abi.md")]

def test_new_file_writes_never_conflict(two_clones):
    a, b = two_clones
    new_question(a, "qa", "t", "Fan", "codex", date(2026,10,25)); _commit_all(a, "[question] a"); push(a)
    new_question(b, "qb", "t", "Lee", "claude-code", date(2026,10,25)); _commit_all(b, "[question] b")
    pull(b); assert unmerged_paths(b) == []
```

- [ ] **Step 2: Run to verify failure** → FAIL
- [ ] **Step 3: Implement `sync.py`; wire the subcommand; update the two skills** (start: `pull` then `conflicts`; end: `conflicts` then `push`; on exit 2 the skill records the paths in the log entry and tells the user, spec §12)
- [ ] **Step 4: Run to verify pass** → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(ra): sync and protected-conflict detection"`

### Task 15: `ra stats` and the two-clone handoff test

**Files:**
- Create: `template/protocol/ra/stats.py`, `tests/test_stats.py`, `tests/test_handoff.py`
- Modify: `template/protocol/ra.py` — `stats`; `tests/test_example.py` — remove xfail

**Interfaces:**
- Produces: `stats(repo: Path) -> dict` with keys `papers`, `claims`, `unverified_claims` (no `verified_by` entry from a reader other than `by`), `disputed_claims`, `duplicate_records`, `decisions_edited`, `open_questions`, `conflict_facts`.

- [ ] **Step 1: Write the failing tests**

```python
def test_stats_on_example():
    s = stats(Path("examples/smoke-plume"))
    assert s["papers"] == 3 and s["disputed_claims"] == 1 and s["conflict_facts"] == 2

def test_handoff_round_trip_file_level(two_clones):
    a, b = two_clones                                   # a = Fan/claude-code, b = Lee/codex
    # A: ingest paper, leave unfinished item in log, push
    # B: pull, digest names the paper and the unfinished item, B re-reads (verified-by), closes the item in its own log, push
    # A: pull; record has two readers; digest for Fan lists B's [literature] re-read and [log]
    assert len(parse(a/"literature"/"a2024-x.md")[0]["readers"]) == 2
    assert run_checks(a) == [] and run_checks(b) == []
```

- [ ] **Step 2: Run to verify failure** → FAIL
- [ ] **Step 3: Implement `stats.py`; write the handoff test body with `ra` calls only (no AI involved — this pins the protocol's conflict-freedom and attribution; the AI-level handoff is Task 17)**
- [ ] **Step 4: Run the full suite** — `pytest -v` → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(ra): stats; test: two-clone handoff"`

### Task 16: Codex runnable-alone verification

**Files:**
- Create: `docs/codex-verification.md`
- Modify: `template/AGENTS.md` and `template/PROTOCOL.md` as needed

- [ ] **Step 1: In a fresh clone of `examples/smoke-plume`, with Codex and no skills installed, run the same prompts as Task 9 step 5, Task 10 step 4 and Task 11 step 2.** Record for each: did Codex read PROTOCOL.md unprompted; which `ra` commands it ran; whether the PDF was read before claims were written; `ra check` result; exact commit subjects.
- [ ] **Step 2: Check whether this Codex version loads skill folders; if it does, repeat with `plugin/skills` installed and record the difference.**
- [ ] **Step 3: Fix PROTOCOL.md / AGENTS.md for every deviation; re-run `pytest tests/test_docs.py`; re-run the failing prompt until it passes.**
- [ ] **Step 4: Commit** — `git commit -m "docs: Codex runnable-alone verification"`

### Task 17: Pilot kit

**Files:**
- Create: `README.md` (install the plugin; `ra init` a project or clone one; run `session-start`), `docs/pilot-checklist.md` (success criteria from spec §16 with the measurement for each: `ra stats` fields, the scripted AI-level handoff in both directions, the fresh-session onboarding questions, the `git log` decision check)
- Modify: `examples/smoke-plume/literature/pdf/*.pdf` — replace generated PDFs with real open-access papers before the pilot starts

- [ ] **Step 1: Write README.md and the checklist**
- [ ] **Step 2: Run the AI-level handoff from spec §16.2 once in each direction on the example project with two team members; record results in `docs/pilot-checklist.md`**
- [ ] **Step 3: Run `pytest -v` → PASS; `python protocol/ra.py check` in the example → clean**
- [ ] **Step 4: Tag** — `git tag v0.1.0 -m "sub-project A: pilot-ready"`

---

## Self-review notes

- Spec coverage: §5–§13 and §16 map to Tasks 1–17; §15 (dual-run) is intentionally out of scope; §14's 16 sections are enforced by `test_protocol_has_all_sections_in_order`.
- Review Focus items 1–5 each have a test in the named task.
- Names used across tasks: `parse/write` (T1) in T2–T15; `parse_claims` (T3) in T4, T15; `run_checks` (T4) in T7, T8, T15; `commits_since_last/render` (T6) in T8, T15; `init_project` (T7) in conftest; `VERBS` (T9) in T10; `pull/push/protected_conflicts` (T14) in skills and T15.
