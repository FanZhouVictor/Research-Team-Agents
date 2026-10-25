# RA_Agent Framework — Stage 0 Design: Scope and Decisions

- Date: 2026-10-25
- Status: approved 2026-10-25 (sub-project A proceeds to planning; sub-project B deferred to the following week)
- Intended location in the framework repo: `docs/superpowers/specs/2026-10-25-ra-agent-framework-stage0-design.md`
- Next step after approval: writing-plans skill (sub-project A), then brainstorming for sub-project B

---

## 1. Purpose

A research team of up to five people, each using their own AI coding agent (Claude Code or Codex), collaborates on one research project through a shared git repository. The repository holds the project's literature, open questions, knowledge, decisions and work log in a form that any team member's AI can read, verify and extend, so that:

- a finding one person's AI extracted from a paper is available to everyone, and verified rather than trusted;
- a session on any platform can continue work another session left unfinished, with no human relaying context between AIs;
- a new team member's AI can answer "what are we trying to find out, what do we know, what's decided, what's in progress" from the repository alone.

The framework is delivered as (a) a protocol file that lives inside each project repository and (b) a plugin of skills that each person installs in their AI tool. The protocol is the authority; the skills are the convenient way to follow it.

## 2. Scope decisions

| Decision | Choice |
|---|---|
| Platforms | Claude Code and Codex only |
| Team size | 5 people or fewer |
| Repository | One git repository per project |
| Hosting | GitHub, private repository |
| Sync mechanism | git itself; no server, database or service |
| Working language of shared files | English |
| Personal memory | Stays on each person's machine; never enters the shared repo by default |
| Decisions | Append-only: supersede, never edit |
| Knowledge | Editable, every fact carries provenance |
| Paper PDFs | Committed into the project repository |
| Reference manager | None; the repository is the source of truth for literature |

## 3. Pilot priorities, ranked

1. Literature findings are shared, not siloed per person
2. Claude Code and Codex sessions continue each other's work
3. A new member gets up to speed from the repo alone
4. Decisions never get lost or re-argued

Design effort follows this order: the literature layer is the most carefully specified; the decisions layer is deliberately minimal for the pilot.

## 4. Two sub-projects

The framework has two parts with a small interface between them. This document fully specifies sub-project A and defines only the interface to sub-project B.

**Sub-project A — shared-repo protocol (this spec).** A data contract: what lives in the repository, who may write it, how, and what every session does at start and end. One person, one platform, git in between.

**Sub-project B — dual-run loop (separate spec).** An orchestration engine: the user gives one task; Claude Code and Codex each work on it independently; a verifier session splits the two answers into agreed and conflicting parts; conflicts go back for another round; the user sees agreed and conflicting parts after every round; stop at five rounds or zero conflicts. This is the only situation in which both platforms run together.

**Interface.** The loop reads the shared repository as common context for both runs, and its agreed output enters the repository only through the gates defined in section 7. Section 15 defines the `dual-run` verb and lists the open questions for spec B.

## 5. Information types in the shared repository

| # | Type | Holds |
|---|---|---|
| 1 | Literature records | One file per paper plus the PDF: metadata, summary, claims extracted for this project, relevance, verification trail |
| 2 | Open questions and hypotheses | What the project is trying to find out; status open / answered / dropped. Defines what "relevant" means when a paper is ingested |
| 3 | Knowledge | Durable facts the team treats as true: dataset facts, method details, measured results, domain facts synthesized from papers, glossary |
| 5 | Decisions | Choice, alternatives, rationale, evidence, status |
| 6 | Work log / handoff notes | What each session did, tried and failed, left unfinished, by whom |
| 7 | Feed | What's new — realised as the git log (section 9), not as a file |
| 8 | Index and protocol | PROJECT.md, PROTOCOL.md, CLAUDE.md, AGENTS.md |

Type 4, experiment records (per-run config, metrics, figures, commit hash), was considered and deliberately left out of the pilot.

### Never in the shared repository

- Personal memory of any team member
- Secrets, credentials, tokens
- Raw data
- Model checkpoints and large outputs
- Manuscript and grant text — a pointer to where it lives (Overleaf or similar), nothing more

## 6. Repository layout

```
<project>/
  PROJECT.md        goals · members · phase · [current status — AI-editable] · pointers (code repo, Overleaf)
  PROTOCOL.md       the rules; single source of truth for AI behaviour
  CLAUDE.md         Claude Code entry point: "read PROTOCOL.md and follow it" — nothing else
  AGENTS.md         Codex entry point: same single instruction
  protocol/         templates/ and check script referenced by PROTOCOL.md
  questions/        one file per question: Q-<date>-<slug>.md
  knowledge/        one file per topic: <topic>.md
    README.md       topic registry: every topic with a one-line scope
    glossary.md
  decisions/        one file per decision: D-<date>-<slug>.md
  literature/       one file per paper: <firstauthor><year>-<slug>.md
    pdf/            <same citekey>.pdf
  log/              one file per session: <date>-<person>-<platform>-<hhmm>.md  (hhmm = session start)
  .gitattributes    *.pdf binary
  .gitignore        .ra/ (local run folders, personal memory, generated digests)
```

Layout rules:

- **No literature index file.** Each record's frontmatter is the index; an AI lists the folder and reads frontmatter. A maintained index would be the one file every paper-add touches.
- **Questions and decisions are one file each**, so a claim can link a question by ID and closing a question is a one-line frontmatter edit.
- **`knowledge/README.md` is the topic registry.** Creating a new topic file goes through the knowledge gate together with the first fact, and the registry line is added in the same commit. This prevents two AIs creating differently named files for the same subject.
- **PROJECT.md members block** records each person's git author name, because "since this person's last commit" is how the feed works.
- **Repo size.** PDFs are committed as plain binary. If the repository approaches roughly 1 GB, move `literature/pdf/` to git LFS; this is the only anticipated change to the layout.

### PROJECT.md template

```markdown
# <Project name>

## Goals
<two to five lines>

## Members
| Person | Git author name | Platform(s) | Role |
|---|---|---|---|
| Fan | Fan <...> | claude-code, codex | PI |

## Phase
<e.g. literature review / method development / writing>

## Current status
<!-- AI-editable section: 3–8 lines, rewritten by update-status at session end -->

## Pointers
- Code repository:
- Manuscript:
```

## 7. Write rules

| Type | Who writes | How it lands | Conflict rule |
|---|---|---|---|
| 1 Literature | AI, directly | New file per paper plus PDF. Dedup check first (section 10). Claims link to existing questions only. Full provenance | Duplicate → re-read and update the existing record (section 10), never a second record |
| 2 Questions | AI proposes; **human approves, asked immediately** | AI presents the proposed question and asks whether it goes into the shared repo (section 8). On yes: new file, status `open`, `proposed-by` and `approved-by` filled. Closing (`answered` / `dropped`) is human-only and must link to the knowledge or decision that answers it | Add-only for AI; none |
| 3 Knowledge | AI proposes; **human approves, asked immediately** | AI presents each candidate fact with its source and target topic file and asks (section 8). On yes: fact line added with provenance. Changing or removing the content of a fact someone else authored is never allowed: add the new fact alongside and mark both `CONFLICT`. Setting the status field of another person's fact to `CONFLICT with <ref>` is the one permitted edit to it; a human resolves | Contradictions coexist until a human resolves them |
| 5 Decisions | AI proposes; **human accepts** | New file per decision, ID = date + slug. AI writes status `proposed`. Only a human sets `accepted`. Supersede = new file with `supersedes:`; the old file receives exactly one edit: `status: superseded` and `superseded-by:` | New-file; none |
| 6 Work log | AI, directly | One file per session, written at session end | New-file; none |
| 7 Feed | AI, automatically | One structured commit per write (section 9) | None by construction |
| 8 Index and protocol | Split | PROJECT.md "Current status": AI rewrites directly at session end. Goals, members, phase, and all of PROTOCOL.md / CLAUDE.md / AGENTS.md / protocol/: human-only. An AI may propose a protocol change as a diff in a commit message or log entry | Human-only; none |

Roles for the pilot: any team member may approve a question, approve a fact, accept a decision or close a question. A designated-approver rule is deferred.

The gates for questions and knowledge fire immediately, each time the AI learns something it considers shareable — not batched at session end. The team accepts this friction: accuracy over speed.

## 8. Human gates — prompt format

Both platforms ask the same way. The prompt states what is proposed, where it would go, and offers exactly three choices.

```
Proposed for the shared repo — KNOWLEDGE
  Topic file: knowledge/goes-abi.md (existing)
  Fact:       GOES-16 ABI band 7 is 3.9 µm with 2 km nadir resolution
  Source:     smith2024-plume-goes §2.1 p.3
Commit / Edit / Skip?
```

```
Proposed for the shared repo — QUESTION
  ID:      Q-2026-10-25-plume-baselines
  Title:   What are the strongest published baselines for plume segmentation on GOES-16?
  Context: <one or two lines>
Commit / Edit / Skip?
```

```
Proposed for the shared repo — DECISION (status will be: proposed)
  ID:      D-2026-10-25-eval-metric
  Title:   Use mIoU as the primary segmentation metric
  Evidence: <links>
Commit / Edit / Skip?
```

`Edit` returns the proposal to the user for changes and re-asks. `Skip` records nothing in the shared repo; the AI may keep it in local personal memory.

## 9. Feed: the git log

There is no feed file. Every write to the shared repository is its own commit with a structured message, and "what's new" at session start is `git log --since=<this person's last commit>` rendered as a short digest.

Commit message format:

```
[literature] added Smith 2024 — plume segmentation from GOES imagery

Person: Fan
Agent: codex
Links: literature/smith2024-plume-goes.md, questions/Q-2026-10-25-plume-baselines.md
```

- Type tags: `literature` `question` `knowledge` `decision` `log` `status` `protocol`
- One commit per logical write. The session-end log entry is its own `[log]` commit; the status rewrite is its own `[status]` commit.
- History is never squashed or rebased.
- GitHub "watch repository" gives each teammate email notification per commit; the structured subject line makes those notifications readable. Any richer notification (digests, Slack) is Stage 6, not pilot.
- Optional, not pilot-critical: `session-start` may render the digest to a local, git-ignored `NEWS.md` for humans who want to read it outside their AI.

## 10. Literature

### 10.1 The PDF-first rule

An AI must read the original PDF any time it **uses** a paper. It never relies on another AI's summary or claims, because a summary loses information by default.

- **Navigating** a record is not use: listing papers, filtering by relevance tag or linked question, reading frontmatter to decide what is relevant.
- **Using** is relying on any content of the paper — a claim, a number, a method, a limitation — in reasoning, in an answer to the user, in a knowledge proposal, or in writing. Before an AI says "Smith 2024 found X", it opens the PDF at the claim's `where` and confirms it.
- Writing to a record requires a full read of the PDF. A record is never updated from the record alone.
- The `where` field is what keeps this affordable: verification of an existing claim is targeted at the cited table, figure, section or page; a full re-read is reserved for writing to the record.
- Verification is recorded only the first time a given reader confirms a given claim; routine use by the same reader re-checks the PDF but does not generate a commit.

### 10.2 Dedup

Before creating a record: match on DOI, then arXiv ID, then normalised title. If a record exists, the AI does not create a second one; it performs `reread-literature` (10.4).

### 10.3 Record template

```markdown
---
citekey: smith2024-plume-goes
title: Transformer-based smoke plume segmentation from GOES-16 imagery
authors: [Smith J, Lee K]
year: 2024
venue: Remote Sensing of Environment
doi: 10.1016/...
arxiv:
pdf: literature/pdf/smith2024-plume-goes.pdf
relevance: core                 # core | supporting | background | not-useful
bears-on: [Q-2026-10-25-plume-baselines]
readers:
  - {person: Fan, agent: codex, date: 2026-10-25, read: full-text}
  - {person: Lee, agent: claude-code, date: 2026-10-28, read: full-text}
code:
data:
related: [jones2023-plume-unet]
---

## Summary
≤150 words, own words: problem, method, data, main result.
revised: 2026-10-28 Lee/claude-code — added dataset split and training details

## Why it matters here
One or two lines tying the paper to the project. If relevance is not-useful: say why,
so nobody spends an hour rediscovering that.

## Claims for this project
- Transformer segmentation beats U-Net by 4.2 mIoU on GOES-16 plume masks
  - where: Table 3, p.7
  - bears on: Q-2026-10-25-plume-baselines — supports
  - kind: result                 # result | method | dataset | definition | limitation
  - basis: stated by paper       # or: inferred by <agent>
  - by: Fan · codex · 2026-10-25
  - verified-by: Lee · claude-code · 2026-10-28
  - disputed-by: —

## Notes
- 2026-10-28 · Lee · claude-code: ...

## BibTeX
```bibtex
@article{smith2024-plume-goes, ...}
```
```

`read` values: `full-text` | `abstract-only` | `skimmed`. Only a `full-text` reader may write or verify claims.

### 10.4 Rules

1. **Every claim has a `where`** — section, table, figure or page. A claim without a location is not written.
2. **`basis` is the honesty field.** "Stated by paper" versus "inferred by <agent>". Inferred claims are permitted but always labelled.
3. **Claims link only to questions that exist.** If a paper suggests a new question, the question goes through its gate first; the claim is written after approval.
4. **`not-useful` is a first-class outcome.** Recording what was read and rejected, with the reason, is half of "not siloed".
5. **Own words throughout.** No copied passages; a short quoted phrase only where exact wording is the point.
6. **Re-read (`reread-literature`).** A second reader reads the PDF in full, then for each existing claim does exactly one of: adds itself to `verified-by`; or adds itself to `disputed-by` with a one-line reason, leaving the claim in place. Never delete, never silently correct — a misread number is a dispute. New claims are appended with the reader's own provenance. The reader adds itself to `readers`.
7. **Summary refinement.** The summary is editable: refinement means adding detail or fixing an error; it never shortens or removes something another reader wrote. Each edit appends a `revised:` trail line stating why; git diff is the full audit.
8. **Disputes.** Resolved by a human, as for knowledge conflicts. A disputed claim cannot be proposed to knowledge until resolved.
9. **Promotion to knowledge** happens only through the knowledge gate; the resulting fact's source points back to `citekey · where`.
10. **Relevance is relative to the questions open on the ingest date.** Optional Stage 2 skill: when a new question is approved, list papers ingested before it and offer to re-read them for that question.
11. **Health signal.** `session-start` may report, for example, "12 papers; 4 have claims no second reader has verified".

Commit messages: `[literature] added <citekey> — <title fragment>` and `[literature] re-read <citekey> — verified 3, disputed 1, added 2 claims`.

## 11. Other templates

### Question — `questions/Q-<date>-<slug>.md`

```markdown
---
id: Q-2026-10-25-plume-baselines
title: What are the strongest published baselines for plume segmentation on GOES-16?
status: open                    # open | answered | dropped
proposed-by: {person: Fan, agent: claude-code, date: 2026-10-25}
approved-by: Fan
answered-by:                    # knowledge/<topic>.md or decisions/D-... — filled on close
closed-by:                      # person · date — human only
---

## Context
Why this matters to the project.

## Working notes
- 2026-10-25 · Fan · claude-code: ...
```

### Decision — `decisions/D-<date>-<slug>.md`

```markdown
---
id: D-2026-10-25-eval-metric
title: Use mIoU as the primary segmentation metric
status: proposed                # proposed | accepted | superseded
proposed-by: {person: Fan, agent: codex, date: 2026-10-25}
accepted-by:                    # person · date — human only
supersedes:                     # D-... if any
superseded-by:                  # the only edit ever made to an accepted decision
links: [Q-2026-10-25-plume-baselines, literature/smith2024-plume-goes.md]
---

## Decision
## Alternatives considered
## Rationale and evidence
## Consequences
```

### Knowledge fact line — inside `knowledge/<topic>.md`

One line per fact, metadata in a trailing parenthesis:

```markdown
- GOES-16 ABI band 7 is 3.9 µm with 2 km nadir resolution (src: smith2024-plume-goes §2.1 p.3 · Fan/codex 2026-10-25 · approved Fan · CONFLICT with line below)
- GOES-16 ABI band 7 nadir resolution is 1 km (src: lee2023-abi-spec Table 1 · Lee/claude-code 2026-10-28 · approved Lee · CONFLICT with line above)
```

Status values: `ok` | `CONFLICT with <ref>` | `superseded by <ref>`. Topic files begin with a two-line scope header matching the registry entry.

### Log entry — `log/<date>-<person>-<platform>-<hhmm>.md`

```markdown
---
date: 2026-10-25
person: Fan
agent: codex
session: 14:32–16:05
dual-run:                       # run id if a dual-run happened this session
---

## Done
## Tried and failed
## Unfinished
## Suggested next step
## Files touched
```

## 12. Session procedure

**Start**

1. `git pull`
2. Read PROJECT.md
3. Read the git log since this person's last commit (or the last 20 commits if the person has none); render a short digest of what's new
4. Read all open questions (frontmatter and context)
5. Read only the knowledge files relevant to the task at hand
6. Optionally run `check` and report its findings

**During**

- Pull before every write; push after every write batch
- One commit per logical write; small commits, not one large commit at the end
- Gates fire immediately when a shareable question or fact arises
- Any use of a paper opens its PDF (10.1)

**End**

1. Write the log entry → `[log]` commit
2. Rewrite PROJECT.md "Current status" → `[status]` commit
3. `git push`

**Conflicts.** If git reports a merge conflict in `knowledge/` or `decisions/`, the AI stops, leaves the conflict in place, records it in the log entry, and tells the user. It never resolves those conflicts itself. Conflicts elsewhere are structurally unlikely (new-file-per-item); if one occurs, the same rule applies.

## 13. How each platform learns the protocol

- **PROTOCOL.md is the single source of truth** and travels with the project repository.
- **CLAUDE.md and AGENTS.md** each contain one instruction: read PROTOCOL.md before anything else and follow it.
- **The plugin's skills implement the verbs**: `session-start`, `session-end`, `add-literature`, `reread-literature`, `propose-question`, `close-question`, `propose-knowledge`, `propose-decision`, `accept-decision`, `supersede-decision`, `update-status`, `dual-run` (sub-project B). Skills cite PROTOCOL.md sections rather than restating rules, so a rule is changed in one place and cannot drift between platforms.
- **Runnable-alone test.** A fresh Codex session with no plugin, pointed at AGENTS.md, must be able to perform every verb correctly from PROTOCOL.md and the repository alone. Claude Code loads the skills natively; whether the team's Codex version can load the same skill folders is verified in Stage 4. Either way, the protocol must pass the runnable-alone test.
- **Enforcement** is the text itself plus an auditable git log. The one hard check is `protocol/check` (a small script either AI can run): frontmatter valid; every claim has a `where`; no disputed claim cited as a knowledge source; no in-place edit to an accepted decision other than `superseded-by`; every file name follows the naming rules.

## 14. PROTOCOL.md — table of contents

PROTOCOL.md is written as a runbook: ordered, imperative steps with exact paths, commands and prompt wording. Templates and the check script live in `protocol/`.

1. Purpose and scope
2. Bootstrap — what an AI reads on first opening the repo, and what it reads only per verb
3. Repo map
4. Information types and write rules (section 7 of this spec)
5. Session procedure (section 12)
6. Verbs — one runbook each: preconditions, steps, prompts, files changed, commit message
7. Literature rules (section 10)
8. Human gates — exact prompt format (section 8)
9. Conflict rules
10. Naming conventions — citekeys, IDs, log filenames, topic names, dates
11. Commit conventions (section 9)
12. File templates — pointer to `protocol/templates/`
13. Never-in-repo list
14. Health checks — what `check` verifies, what session-start reports
15. Glossary — claim, fact, record, reader, gate, use versus navigate
16. Protocol version and change procedure — version number, changelog, human-only edits, how an AI proposes a change

"Complete" means complete for the pilot's verbs, not for everything the framework may do later.

## 15. Sub-project B interface — the `dual-run` verb

Defined here only as far as sub-project A needs it.

- **Input:** one task from the user, plus the shared repository as identical context for both platforms.
- **Rounds:** at most five. In each round, Claude Code and Codex each produce an answer independently; a fresh verifier session on either platform receives the task and both answers and splits the content into *agreed* and *conflict*; the user is shown both parts after every round; conflict items go back for the next round.
- **Stop:** zero conflicts, or five rounds. Remaining conflicts are shown to the user as unresolved, never dropped.
- **Output path:** agreed content enters the shared repository only through the normal gates (section 7). For literature, each run reads the PDF itself (10.1), so claims agreed by both platforms are recorded with both as `verified-by`.
- **Artifacts:** per-round answers and verdicts live in a local, git-ignored run folder (`.ra/runs/<id>/`). The session log entry records the run ID.
- **Open questions for spec B** (not decided here): what launches both CLIs and collects their output — an external script (LangGraph is a candidate) or one CLI driving the other; which platform verifies, fixed or alternating; how round 2+ is framed to each AI (conflict item, both prior positions, the verifier's statement of the disagreement); retention of run artifacts; cost and time budget per run.

## 16. Pilot success criteria

One active project, 3–4 weeks.

1. **Literature** — papers ingested by at least two different people; every claim has a `where`; no paper exists as two records; a majority of claims verified by a second reader by pilot end.
2. **Continuity** — a scripted handoff in each direction: a Claude Code session ingests a paper and leaves an unfinished task in the log; a Codex session under a different person picks it up and finishes it with no human relaying context; then reversed.
3. **Onboarding** — a fresh session with no prior context correctly answers "what are we trying to find out, what do we know, what's decided, what's in progress" from one `session-start`.
4. **Decisions** — every accepted decision links to its evidence; git history shows none edited in place.

Global checks: zero copy-paste between AIs during the pilot; no git conflict in `knowledge/` or `decisions/` left unresolved longer than a week.

## 17. Non-goals for the pilot

- Platforms beyond Claude Code and Codex
- Experiment records
- Manuscript or grant text in the repository
- Any sync other than git and GitHub: no server, database or web UI
- Real-time co-editing
- Automation — LangGraph watchers, digests, scheduled agents (Stage 6)
- Sharing personal memory
- Automatic conflict resolution in knowledge or decisions
- Zotero or any reference-manager integration
- Access control finer than GitHub repository permissions
- A designated-approver role

## 18. Assumptions to confirm

- ~~Hosting is a private GitHub repository~~ — confirmed 2026-10-25
- ~~Shared files are written in English~~ — confirmed 2026-10-25
- Both CLIs can read PDFs from the repository on each person's machine
- The team's Codex version either supports skill folders or can run from AGENTS.md → PROTOCOL.md alone (Stage 4 verifies; the runnable-alone test covers the second case)

## 19. Next steps

1. Fan reviews this spec; changes are folded in
2. Writing-plans skill produces the implementation plan for sub-project A (Stage 1 schema and templates, Stage 2 skills, Stage 3 sync)
3. Brainstorming for sub-project B, the dual-run loop, starting from section 15
