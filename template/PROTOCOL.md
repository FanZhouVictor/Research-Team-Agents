---
version: 0.1.0
---
# PROTOCOL.md — Shared-repo protocol

## 1. Purpose and scope

This repository holds one research project of a team of up to five people. Each person works with their own AI agent, Claude Code or Codex. The repository keeps the project's literature, open questions, knowledge, decisions and work log in a form that any member's AI can read, verify and extend, so that:

- a finding one person's AI extracted from a paper is available to everyone, and verified rather than trusted;
- a session on either platform can continue work another session left unfinished, with no human relaying context between AIs;
- a new team member's AI can answer "what are we trying to find out, what do we know, what's decided, what's in progress" from the repository alone.

This file is the single source of truth for how an AI works in this repository. The plugin skills implement the verbs of section 6 and cite this file; where a skill and this file disagree, follow this file.

| Scope | Rule |
|---|---|
| Platforms | Claude Code and Codex only |
| Team | 5 people or fewer, listed in PROJECT.md |
| Repository | one git repository per project, hosted as a private GitHub repository |
| Sync | git itself (section 5); no server, database or service |
| Language | every shared file is written in English, in UTF-8 |
| Personal memory | stays on each person's machine (section 13) |
| Decisions | append-only: superseded, never edited (section 4) |
| Knowledge | editable; every fact carries its provenance (section 12) |
| Paper PDFs | committed into this repository (section 3) |
| Reference manager | none: this repository is the source of truth for literature |

The pilot ranks its priorities: (1) literature findings are shared, not siloed per person; (2) Claude Code and Codex sessions continue each other's work; (3) a new member gets up to speed from the repository alone; (4) decisions never get lost or re-argued.

This version covers the verbs of section 6. Experiment records (per-run configs, metrics, figures) are not kept in this repository.

## 2. Bootstrap

**On opening the repository**, read, before anything else:

1. sections 1–5, 9 and 11 of this file;
2. PROJECT.md;
3. `knowledge/README.md`, the topic registry;
4. every open question in `questions/`.

Items 2–4 are steps of session-start (section 6), which you run before any other work in a session.

**Per verb.** Before you run a verb, read its runbook in section 6, and also:

- section 7 for add-literature and reread-literature, and before you rely on a paper in any answer;
- section 8 for propose-question, propose-knowledge and propose-decision;
- section 10 when you name a new file, section 12 when you fill one, section 14 when `check` reports a finding.

**Who you are.** Commands, file names and provenance use two values:

- `<Person>` — the user's name exactly as in the Person column of PROJECT.md Members. Find the row whose Git author name matches `git config user.name` and `git config user.email`. If no row matches, ask the user which member they are and to set their git identity to that row's Git author name; never add a member yourself (section 4).
- `<agent>` — `claude-code` if you are Claude Code, `codex` if you are Codex.

**Placeholders.** Replace every `<…>` in a command or format with its value and keep the rest literally. `<date>` is today as `YYYY-MM-DD`. In running text, `ra <command>` is short for `python protocol/ra.py <command>`; fenced blocks show the full command.

**The helper.** Run every command from the project root, the folder that holds PROJECT.md. This lists the commands; `--help` after a command lists its flags:

```
python protocol/ra.py --help
```

The helper needs Python 3.10 or newer and PyYAML. If `python` is missing or `python --version` is older than 3.10, use `python3` in its place when `python3 --version` is 3.10 or newer; otherwise tell the user. If the module `yaml` is missing, ask the user to run `python -m pip install -r protocol/requirements.txt`.

**Human-only files.** Never edit PROTOCOL.md, CLAUDE.md, AGENTS.md or anything under `protocol/`. Section 16 says how to propose a change.

**When a runbook does not cover it.** If a command fails in a way its runbook does not handle, or a request would break a rule of this file, stop, name the section, and ask the user. Write to the repository only through the runbooks of section 6.

**Creating a project** is not a verb inside a project. PROJECT.md and this file arrive when a human runs `ra init` from a checkout of the framework repository (the project-init skill does this for Claude Code users), for example:

```
python <framework-checkout>/template/protocol/ra.py init <dest> --name "Smoke Plume" --person Fan --git-author "Fan <fan@x>" --platforms claude-code codex --role PI
```

## 3. Repo map

```
<project>/
  PROJECT.md        goals · members · phase · current status (AI-editable) · pointers
  PROTOCOL.md       this file: the rules, the single source of truth for AI behaviour
  CLAUDE.md         Claude Code entry point: read PROTOCOL.md and follow it
  AGENTS.md         Codex entry point: the same single instruction
  protocol/         ra.py (the helper), ra/ (its code), templates/, requirements.txt
  questions/        one file per question: Q-<date>-<slug>.md
  knowledge/        one file per topic: <topic>.md
    README.md       topic registry: every topic with a one-line scope
    glossary.md     the project's terms
  decisions/        one file per decision: D-<date>-<slug>.md
  literature/       one file per paper: <firstauthor><year>-<slug>.md
    pdf/            <same citekey>.pdf
  log/              one file per session: <date>-<person>-<agent>-<HHMM>.md  (HHMM = session start)
  .gitattributes    *.pdf binary
  .gitignore        .ra/ (local run folders, personal memory, generated digests), NEWS.md, __pycache__/
```

Layout rules:

- **No literature index file.** Each record's frontmatter is the index: list `literature/` and read the frontmatter.
- **Questions and decisions are one file each**, so a claim links a question by its ID and closing a question is a frontmatter edit.
- **`knowledge/README.md` is the topic registry**, one line `- <topic> — <scope>` per topic file. A new topic file and its registry line are created together, through the knowledge gate, in one commit (propose-knowledge).
- **`knowledge/glossary.md`** holds the project's terms as fact lines (section 12), added through propose-knowledge like any fact.
- **PROJECT.md Members** records each person's git author name, because "since this person's last commit" is how the digest finds what is new.
- **PDFs are committed as plain binary.** If the repository approaches 1 GB, tell the user: moving `literature/pdf/` to git LFS is a human decision.
- **Create nothing outside this map.** Local files go under `.ra/`, which git ignores.

## 4. Information types and write rules

Who writes each type, and how a write lands. "A human" means any member listed in PROJECT.md.

- **Literature records** (`literature/`): the AI writes directly. One record per paper plus its PDF, after the dedup check (section 7.2). Claims link only to existing questions, and every claim and every reader carries provenance (section 7.3). A paper that has a record is never recorded again: re-read and update the existing record (reread-literature).
- **Questions** (`questions/`): the AI proposes; a human approves at the question gate (section 8). On `Commit`: a new file with `status: open` and `proposed-by` and `approved-by` filled (propose-question). For the AI, questions are add-only. Closing a question, as `answered` or `dropped`, is a human decision and links the knowledge file or decision that answers it; the AI makes that edit only when a human tells it to (close-question).
- **Knowledge** (`knowledge/`): the AI proposes; a human approves each fact at the knowledge gate (section 8). On `Commit`: one fact line with its provenance (propose-knowledge). Changing or removing the content of a fact someone else authored is never allowed; a contradiction is added alongside and marked (section 9).
- **Decisions** (`decisions/`): the AI proposes, as a new file with `status: proposed` (propose-decision). Only a human accepts; the AI sets `accepted` only when a human tells it to (accept-decision). A decision is never edited: a new decision supersedes it, and the old file receives exactly one edit, `status: superseded` and `superseded-by:` (supersede-decision).
- **Work log** (`log/`): the AI writes directly, one new file per session, at session end (session-end).
- **Feed**: the git log; there is no feed file. Every write is one structured commit (section 11), and `ra digest` shows what is new (session-start).
- **PROJECT.md and the protocol files**: the AI rewrites only the "Current status" section of PROJECT.md (update-status). Goals, Members, Phase and Pointers are human-only, as are PROTOCOL.md, CLAUDE.md, AGENTS.md and `protocol/` (section 2).

**Roles.** Any member may approve a question, approve a fact, accept a decision or close a question; there is no designated approver.

## 5. Session procedure

**Start.** Run session-start (section 6) before any other work: `ra sync pull` → read PROJECT.md → `ra digest --person <Person>` → read the open questions → read the knowledge files relevant to the task → `ra check` → report.

**During.**

- Pull before every write; push after every write batch. Every writing runbook of section 6 runs `ra sync pull` before its first write and `ra sync push` after its last commit. Pull and push with these two commands only.
  - `ra sync pull` prints nothing and exits 0 when it succeeds. On exit 1, stop and show the user the output. If `protected <path>` or `other <path>` lines follow the `error:` line, a merge conflict is in place: section 9. Otherwise (no network, no upstream, a local change in the way), continue only if the user tells you to.
  - `ra sync push` prints nothing and exits 0 when it succeeds. On exit 1, run `ra sync pull` and then `ra sync push` once more; if that fails too, tell the user.
  - A project with no remote (`git remote` prints nothing), such as a local example, can neither pull nor push: tell the user once, then skip both commands for the rest of the session.
- One commit per logical write; small commits, not one large commit at the end (section 11).
- Gates fire immediately when a shareable question or fact arises (section 8).
- Any use of a paper opens its PDF (section 7.1).

**End.** When the user ends the session, run session-end (section 6): `ra new log` → `[log]` commit → rewrite PROJECT.md "Current status" → `[status]` commit → `ra sync conflicts` → `ra sync push`.

**Conflicts.** If git reports a merge conflict in `knowledge/` or `decisions/`, the AI stops, leaves the conflict in place, records it in the log entry, and tells the user. It never resolves those conflicts itself. Conflicts elsewhere are structurally unlikely (new-file-per-item); if one occurs, the same rule applies.

Section 9 turns this rule into steps.

## 6. Verbs

One runbook per verb. Each has five parts: **Preconditions**, what must hold before you start; **Steps**, done in order; **Ask the human**, the exact prompt, or none; **Files changed**; and **Commit**, the exact `ra commit` call, which the step "Commit (below)" runs. Every verb other than session-start needs session-start to have run in this session. A verb that runs another verb, as add-literature runs propose-question, follows that verb's runbook in full and then continues.

`dual-run`, in which Claude Code and Codex work on one task in rounds, is defined by a separate specification and is not part of this protocol version; leave the `dual-run:` field of a log entry empty.

### session-start

**Preconditions:** you are opening the repository for a new session and have read sections 1–5, 9 and 11 (section 2).

**Steps:**

1. Note the session start as `YYYY-MM-DDTHH:MM`, local time, 24-hour clock; session-end needs it.
2. Pull (section 5):
   ```
   python protocol/ra.py sync pull
   ```
3. Read PROJECT.md.
4. List what is new since your own last commit:
   ```
   python protocol/ra.py digest --person <Person>
   ```
   For each commit under its heading `## log (<N>)`, read `## Unfinished` and `## Suggested next step` of that log entry: the subject `session <Person>/<agent> <date> <HH:MM>–<HH:MM>` names the file `log/<date>-<person>-<agent>-<HHMM>.md` (section 10).
5. Read every open question: the frontmatter and `## Context` of each file in `questions/` with `status: open`.
6. Read `knowledge/README.md`, then only the knowledge files relevant to the task at hand.
7. Run the check. Its findings are the ones that were there before your writes (section 14):
   ```
   python protocol/ra.py check
   ```
8. Report to the user what section 14 lists for session-start: the digest, the check summary and the health line.

**Ask the human:** none

**Files changed:** none

**Commit:** none

### session-end

**Preconditions:** the user ends the session or asks you to end it.

**Steps:**

1. Pull (section 5):
   ```
   python protocol/ra.py sync pull
   ```
2. Create the log entry with the start you noted in session-start step 1. It prints the path, `log/<date>-<person>-<agent>-<HHMM>.md`:
   ```
   python protocol/ra.py new log --person <Person> --agent <agent> --start <YYYY-MM-DDTHH:MM>
   ```
3. Fill the log entry. In the frontmatter, add the end time after the en dash of `session:` (`14:32–` becomes `14:32–16:05`) and leave `dual-run:` empty. Under each heading write `- ` bullets, or `- none` where there is nothing to say:
   - `## Done`: every write of the session, by ID, citekey or path.
   - `## Tried and failed`: what did not work, and why.
   - `## Unfinished`: open work, specific enough for another session to pick it up.
   - `## Suggested next step`: what the next session should do first.
   - `## Files touched`: every repository path the session changed.
4. Check (section 14):
   ```
   python protocol/ra.py check
   ```
5. Commit the log entry (below).
6. Run update-status; it makes the `[status]` commit.
7. Make sure no merge conflict is in place. `sync: no conflicts` (exit 0): go on. Exit 2: stop as section 9 says.
   ```
   python protocol/ra.py sync conflicts
   ```
8. Push (section 5):
   ```
   python protocol/ra.py sync push
   ```

**Ask the human:** none

**Files changed:** `log/<date>-<person>-<agent>-<HHMM>.md` (new); PROJECT.md (update-status).

**Commit:** two commits: the log entry, then the `[status]` commit of update-status.

```
python protocol/ra.py commit --type log --subject "session <Person>/<agent> <date> <HH:MM>–<HH:MM>" --person <Person> --agent <agent> --links log/<date>-<person>-<agent>-<HHMM>.md -- log/<date>-<person>-<agent>-<HHMM>.md
```

### add-literature

**Preconditions:** the user gives you a paper to add, as a PDF file on this machine; it may be outside the repository.

**Steps:**

1. Pull (section 5):
   ```
   python protocol/ra.py sync pull
   ```
2. Read the first page of the PDF and note its DOI, arXiv id and title, as far as it shows them.
3. Look for an existing record, giving every value you noted:
   ```
   python protocol/ra.py dedup --doi <DOI> --arxiv <arXiv id> --title "<title>"
   ```
4. If it prints `literature/<citekey>.md`, the paper already has a record: create no second one; run reread-literature on that record instead, and add-literature ends there (section 7.2).
5. If it prints `none`, read the whole PDF.
6. Decide the relevance, `core`, `supporting`, `background` or `not-useful`, against the questions open today (section 7.4 rule 10). Draft the claims for this project, each in your own words, with its `where` and the open question it bears on (section 7.3).
7. For a claim that bears on no existing question, run propose-question first. Keep the claim only if the human answers `Commit`; on `Skip`, drop it (section 7.4 rule 3).
8. Choose the citekey (section 10) and create the record, which also copies the PDF to `literature/pdf/<citekey>.pdf`. Give every value the PDF shows; leave out only the flags whose value is unknown:
   ```
   python protocol/ra.py new literature --citekey <citekey> --pdf <path to the PDF> --person <Person> --agent <agent> --title "<title>" --year <year> --authors "<Family I>; <Family I>" --venue "<venue>" --doi <DOI> --arxiv <arXiv id> --relevance <relevance> --bears-on <Q-id> <Q-id>
   ```
9. Open `literature/<citekey>.md` and replace each guidance line with content (section 7.3):
   - `## Summary`: at most 150 words in your own words: problem, method, data, main result.
   - `## Why it matters here`: one or two lines tying the paper to the project; for `not-useful`, why it is not useful.
   - `## Claims for this project`: the claims of steps 6 and 7.
   - `## Notes`: optional lines `- <date> · <Person> · <agent>: <note>`.
   - `## BibTeX`: the entry, keyed by the citekey.
   - Frontmatter `code:`, `data:` and `related:` (citekeys of related records), when known.
10. Check (section 14):
    ```
    python protocol/ra.py check
    ```
11. Commit (below).
12. Push (section 5):
    ```
    python protocol/ra.py sync push
    ```
13. For each claim the team should treat as a durable fact, run propose-knowledge now (section 8).

**Ask the human:** none for the record; propose-question (step 7) and propose-knowledge (step 13) ask their own gates.

**Files changed:** `literature/<citekey>.md` and `literature/pdf/<citekey>.pdf`, both new.

**Commit:** `--links` names the record, its PDF and the questions its claims bear on.

```
python protocol/ra.py commit --type literature --subject "added <citekey> — <title fragment>" --person <Person> --agent <agent> --links literature/<citekey>.md literature/pdf/<citekey>.pdf questions/<Q-id>.md -- literature/<citekey>.md literature/pdf/<citekey>.pdf
```

### reread-literature

**Preconditions:** the paper has a record, `literature/<citekey>.md`: `ra dedup` printed it (add-literature step 4) or the user names it. You are not yet in its `readers` as `<Person>` with `<agent>`; if you are, your verifications are already recorded (section 7.1): tell the user and stop.

**Steps:**

1. Pull (section 5):
   ```
   python protocol/ra.py sync pull
   ```
2. Read the whole PDF, `literature/pdf/<citekey>.pdf`, before you read the record's claims.
3. Draft the claims the record misses, each bearing on an existing question. For one that bears on no existing question, run propose-question now, before you edit the record, and keep the claim only on `Commit` (section 7.4 rule 3).
4. For each existing claim, open the PDF at its `where` and add yourself to exactly one of its two fields (section 7.4 rule 6). Replace a lone `—` with your entry; after an existing entry, write `; ` and then yours. Change nothing else in the claim.
   - The PDF supports the claim: `verified-by: <Person> · <agent> · <date>`.
   - It does not: `disputed-by: <Person> · <agent> · <date> — <one-line reason>`.
5. Append the claims of step 3 under `## Claims for this project` (section 7.3) with your own `by:`, and add their questions to `bears-on`.
6. If the summary misses a detail or has an error, refine it as section 7.4 rule 7 says, and append the line `revised: <date> <Person>/<agent> — <why>` under it.
7. Add yourself to `readers` in the frontmatter, in the block form of the entries already there:
   ```
   - person: <Person>
     agent: <agent>
     date: <date>
     read: full-text
   ```
8. Optionally add a line `- <date> · <Person> · <agent>: <note>` under `## Notes`.
9. Check (section 14):
   ```
   python protocol/ra.py check
   ```
10. Commit (below).
11. Push (section 5):
    ```
    python protocol/ra.py sync push
    ```

**Ask the human:** none for the record; propose-question (step 3) asks its own gate.

**Files changed:** `literature/<citekey>.md`.

**Commit:** each `<N>` counts the claims you verified, disputed and added.

```
python protocol/ra.py commit --type literature --subject "re-read <citekey> — verified <N>, disputed <N>, added <N> claims" --person <Person> --agent <agent> --links literature/<citekey>.md -- literature/<citekey>.md
```

### propose-question

**Preconditions:** a question the project should track has come up, from a paper, the user or your own work.

**Steps:**

1. Pull (section 5):
   ```
   python protocol/ra.py sync pull
   ```
2. Read the titles in `questions/`. If a question already asks it, stop: use that question.
3. Draft the ID `Q-<date>-<slug>` (section 10), the title (the question in one sentence) and one or two lines of context.
4. Ask the human now, with the prompt below, and wait for the answer. On `Edit` or `Skip`, do what section 8 says.
5. On `Commit`, create the question file; it prints `questions/<Q-id>.md`:
   ```
   python protocol/ra.py new question --slug <slug> --title "<title>" --person <Person> --agent <agent>
   ```
6. In that file, set `approved-by: <approver>` (section 8) and replace the guidance line under `## Context` with the context.
7. Check (section 14):
   ```
   python protocol/ra.py check
   ```
8. Commit (below).
9. Push (section 5):
   ```
   python protocol/ra.py sync push
   ```

**Ask the human:**

```
Proposed for the shared repo — QUESTION
  ID:      Q-<date>-<slug>
  Title:   <the question>
  Context: <one or two lines>
Commit / Edit / Skip?
```

**Files changed:** `questions/<Q-id>.md`, new.

**Commit:**

```
python protocol/ra.py commit --type question --subject "proposed <Q-id> — <title>" --person <Person> --agent <agent> --links questions/<Q-id>.md -- questions/<Q-id>.md
```

### close-question

**Preconditions:** a human has told you to close question `<Q-id>`, and its `status` is `open`. Never close a question on your own judgement (section 4).

**Steps:**

1. Pull (section 5):
   ```
   python protocol/ra.py sync pull
   ```
2. If the human has not said both, ask whether the question is `answered` or `dropped`, and which knowledge file or decision answers it.
3. In `questions/<Q-id>.md`, set three frontmatter lines:
   - `status: answered` or `status: dropped`;
   - `answered-by:` the path of the file that answers it, `knowledge/<topic>.md` or `decisions/<D-id>.md`;
   - `closed-by: <Person> · <date>`, naming the member who closed it.
4. Optionally add a line `- <date> · <Person> · <agent>: <how that file answers the question>` under `## Working notes`.
5. Check (section 14):
   ```
   python protocol/ra.py check
   ```
6. Commit (below).
7. Push (section 5):
   ```
   python protocol/ra.py sync push
   ```

**Ask the human:** only what step 2 needs; it is not a gate.

**Files changed:** `questions/<Q-id>.md`.

**Commit:** `--links` names the question and the file that answers it.

```
python protocol/ra.py commit --type question --subject "closed <Q-id>" --person <Person> --agent <agent> --links questions/<Q-id>.md <answered-by path> -- questions/<Q-id>.md
```

### propose-knowledge

**Preconditions:** you consider a fact durable and worth sharing: a dataset fact, method detail, measured result, domain fact or project term. When it comes from a paper, you opened the PDF at the `where` you cite and confirmed it (section 7.1), and no claim at that `where` in the paper's record is disputed (section 7.4 rule 8).

**Steps:**

1. Pull (section 5):
   ```
   python protocol/ra.py sync pull
   ```
2. Choose the topic: read `knowledge/README.md` and take the topic whose scope covers the fact; a project term goes to `knowledge/glossary.md`. Only if no topic fits, draft a new topic name (section 10) and a one-line scope.
3. Read the topic file. If the new fact contradicts a fact in it, the new fact goes in as section 9 says.
4. Ask the human now, with the prompt below, and wait for the answer. On `Edit` or `Skip`, do what section 8 says.
5. On `Commit`, if the topic is new, create it; this also adds its registry line to `knowledge/README.md`:
   ```
   python protocol/ra.py new topic --topic <topic> --scope "<scope>"
   ```
6. Add the fact as one line (section 12) at the end of `knowledge/<topic>.md`, or, when it contradicts a fact, as section 9 says:
   ```
   - <fact> (src: <citekey> <where> · <Person>/<agent> <date> · approved <approver> · ok)
   ```
7. Check (section 14):
   ```
   python protocol/ra.py check
   ```
8. Commit (below).
9. Push (section 5):
   ```
   python protocol/ra.py sync push
   ```

**Ask the human:** for a topic that exists:

```
Proposed for the shared repo — KNOWLEDGE
  Topic file: knowledge/<topic>.md (existing)
  Fact:       <the fact>
  Source:     <citekey> <where>
Commit / Edit / Skip?
```

For a new topic, the prompt says `(new)` and adds the registry line:

```
Proposed for the shared repo — KNOWLEDGE
  Topic file: knowledge/<topic>.md (new)
  Registry:   - <topic> — <scope>
  Fact:       <the fact>
  Source:     <citekey> <where>
Commit / Edit / Skip?
```

When the fact contradicts a fact in the topic file, say so in one line before the prompt and quote that fact: both will be marked as a conflict (section 9).

**Files changed:** `knowledge/<topic>.md`; for a new topic, also `knowledge/README.md`.

**Commit:** for a new topic, add `knowledge/README.md` to `--links` and to the paths.

```
python protocol/ra.py commit --type knowledge --subject "<topic>: <fact fragment>" --person <Person> --agent <agent> --links knowledge/<topic>.md literature/<citekey>.md -- knowledge/<topic>.md
```

### propose-decision

**Preconditions:** a choice the project should record has come up, and its evidence is in the repository: question IDs, and paths of records, knowledge files or log entries.

**Steps:**

1. Pull (section 5):
   ```
   python protocol/ra.py sync pull
   ```
2. Draft the ID `D-<date>-<slug>` (section 10), the title (the decision in one line), the evidence links, and the text of the four sections: Decision, Alternatives considered, Rationale and evidence, Consequences.
3. Ask the human now, with the prompt below, and wait for the answer. On `Edit` or `Skip`, do what section 8 says.
4. On `Commit`, create the decision file in status `proposed`, with each evidence link after `--link`; it prints `decisions/<D-id>.md`:
   ```
   python protocol/ra.py new decision --slug <slug> --title "<title>" --person <Person> --agent <agent> --link <Q-id or path> <Q-id or path>
   ```
5. Write the four sections under their headings. When the decision replaces another, set `supersedes: <old D-id>` (supersede-decision). Leave `status: proposed` and `accepted-by:` as they are: only a human accepts (accept-decision).
6. Check (section 14):
   ```
   python protocol/ra.py check
   ```
7. Commit (below).
8. Push (section 5):
   ```
   python protocol/ra.py sync push
   ```

**Ask the human:**

```
Proposed for the shared repo — DECISION (status will be: proposed)
  ID:      D-<date>-<slug>
  Title:   <the decision>
  Evidence: <links>
Commit / Edit / Skip?
```

When the decision replaces another, say so in one line before the prompt, naming the decision it supersedes.

**Files changed:** `decisions/<D-id>.md`, new.

**Commit:** `--links` names the decision file and the files of its links, a question ID as `questions/<Q-id>.md`.

```
python protocol/ra.py commit --type decision --subject "proposed <D-id> — <title>" --person <Person> --agent <agent> --links decisions/<D-id>.md questions/<Q-id>.md -- decisions/<D-id>.md
```

### accept-decision

**Preconditions:** a human has told you to accept decision `<D-id>`, and its `status` is `proposed`. Never infer an acceptance from anything else (section 4).

**Steps:**

1. Pull (section 5):
   ```
   python protocol/ra.py sync pull
   ```
2. In `decisions/<D-id>.md`, change these two frontmatter lines and nothing else, with `<Person>` the member who accepted:
   ```
   status: accepted
   accepted-by: <Person> · <date>
   ```
   Both changes go into one commit: from that commit on, only `status:` and `superseded-by:` may ever change (`DECISION_EDITED`, section 14).
3. Check (section 14):
   ```
   python protocol/ra.py check
   ```
4. Commit (below).
5. Push (section 5):
   ```
   python protocol/ra.py sync push
   ```
6. If its `supersedes:` names a decision, continue with supersede-decision from step 3.

**Ask the human:** none; the human's instruction is the acceptance.

**Files changed:** `decisions/<D-id>.md`.

**Commit:**

```
python protocol/ra.py commit --type decision --subject "accepted <D-id>" --person <Person> --agent <agent> --links decisions/<D-id>.md -- decisions/<D-id>.md
```

### supersede-decision

**Preconditions:** an accepted decision, `<old-id>`, is to be replaced by a new one.

**Steps:**

1. Run propose-decision for the new decision, `<new-id>`, with `supersedes: <old-id>` (propose-decision step 5).
2. Wait until a human accepts `<new-id>` (accept-decision); this may happen in a later session. Until then, leave `<old-id>` as it is.
3. Pull (section 5):
   ```
   python protocol/ra.py sync pull
   ```
4. In `decisions/<old-id>.md`, change these two frontmatter lines and nothing else; this is the one edit an accepted decision ever receives:
   ```
   status: superseded
   superseded-by: <new-id>
   ```
5. Check (section 14):
   ```
   python protocol/ra.py check
   ```
6. Commit (below).
7. Push (section 5):
   ```
   python protocol/ra.py sync push
   ```

**Ask the human:** the DECISION gate of step 1 (propose-decision); the edit of step 4 asks nothing.

**Files changed:** `decisions/<new-id>.md`, new (step 1); `decisions/<old-id>.md` (step 4).

**Commit:** after the `proposed` and `accepted` commits of steps 1 and 2:

```
python protocol/ra.py commit --type decision --subject "superseded <old-id> by <new-id>" --person <Person> --agent <agent> --links decisions/<old-id>.md decisions/<new-id>.md -- decisions/<old-id>.md
```

### update-status

**Preconditions:** session-end runs it after the `[log]` commit; run it on its own only when the user asks.

**Steps:**

1. Pull (section 5):
   ```
   python protocol/ra.py sync pull
   ```
2. In PROJECT.md, under `## Current status`, keep the comment line `<!-- AI-editable section: … -->` and replace every line after it, up to `## Pointers`, with 3–8 lines on where the project stands: what is in progress, what is decided, what waits for a human. Change nothing else in PROJECT.md. If the status has not changed, change nothing and skip steps 3–5.
3. Check (section 14):
   ```
   python protocol/ra.py check
   ```
4. Commit (below).
5. Push (section 5):
   ```
   python protocol/ra.py sync push
   ```

**Ask the human:** none

**Files changed:** PROJECT.md.

**Commit:**

```
python protocol/ra.py commit --type status --subject "<one-line summary of the new status>" --person <Person> --agent <agent> --links PROJECT.md -- PROJECT.md
```

## 7. Literature rules

### 7.1 Use versus navigate: the PDF-first rule

An AI must read the original PDF any time it **uses** a paper. It never relies on another AI's summary or claims, because a summary loses information by default.

- **Navigating** a record is not use: listing papers, filtering by relevance tag or linked question, reading frontmatter to decide what is relevant.
- **Using** is relying on any content of the paper — a claim, a number, a method, a limitation — in reasoning, in an answer to the user, in a knowledge proposal, or in writing. Before an AI says "Smith 2024 found X", it opens the PDF at the claim's `where` and confirms it.
- Writing to a record requires a full read of the PDF. A record is never updated from the record alone.
- The `where` field is what keeps this affordable: verification of an existing claim is targeted at the cited table, figure, section or page; a full re-read is reserved for writing to the record.
- Verification is recorded only the first time a given reader confirms a given claim; routine use by the same reader re-checks the PDF but does not generate a commit.

### 7.2 Dedup

Before creating a record, match on DOI, then arXiv ID, then normalised title; `ra dedup` does this (add-literature step 3). If a record exists, do not create a second one: run reread-literature on it. `ra check` reports two records with the same DOI or arXiv ID as `DUP_LITERATURE`.

### 7.3 Record and claim format

A record is `literature/<citekey>.md`, made by `ra new literature` from `protocol/templates/literature.md` (section 12); its PDF is `literature/pdf/<citekey>.pdf`. Frontmatter:

- `citekey`, `title`, `authors`, `year`, `venue`, `doi`, `arxiv`: the paper. `pdf`: `literature/pdf/<citekey>.pdf`.
- `relevance`: `core` | `supporting` | `background` | `not-useful`.
- `bears-on`: the IDs of the questions its claims bear on.
- `readers`: one entry per reader, with `person`, `agent`, `date` and `read`.
- `code`, `data`: where the paper's code and data are, if anywhere. `related`: citekeys of related records.

`read` values: `full-text` | `abstract-only` | `skimmed`. Only a `full-text` reader may write or verify claims. You write to a record only after a full read, so every `readers` entry you add says `full-text`.

Body: `## Summary` (at most 150 words, own words: problem, method, data, main result; after it, one `revised:` line per later edit), `## Why it matters here`, `## Claims for this project`, `## Notes`, `## BibTeX`.

A claim is one bullet with seven sub-bullets, each indented two spaces:

```
## Claims for this project
- <the claim, in your own words>
  - where: <section, table, figure or page>
  - bears on: <Q-id> — supports
  - kind: result                 # result | method | dataset | definition | limitation
  - basis: stated by paper       # or: inferred by <agent>
  - by: <Person> · <agent> · <date>
  - verified-by: —
  - disputed-by: —
```

- `bears on`: a question ID and its relation, a word such as `supports` or `contradicts`; several are separated by `; `.
- `verified-by` and `disputed-by`: `—` alone means none, and several entries are separated by `; `. A verification is `<Person> · <agent> · <date>`; a dispute is `<Person> · <agent> · <date> — <one-line reason>`.

### 7.4 Rules

1. **Every claim has a `where`**: section, table, figure or page. A claim without a location is not written (`CLAIM_NO_WHERE`).
2. **`basis` is the honesty field**: `stated by paper` versus `inferred by <agent>`. Inferred claims are permitted but always labelled.
3. **Claims link only to questions that exist.** If a paper suggests a new question, the question goes through its gate first (propose-question); the claim is written after approval.
4. **`not-useful` is a first-class outcome.** Recording what was read and rejected, with the reason, is half of "not siloed".
5. **Own words throughout.** No copied passages; a short quoted phrase only where exact wording is the point.
6. **Re-read** (reread-literature). A second reader reads the PDF in full, then for each existing claim does exactly one of: adds itself to `verified-by`; or adds itself to `disputed-by` with a one-line reason, leaving the claim in place. Never delete, never silently correct: a misread number is a dispute. New claims are appended with the reader's own provenance. The reader adds itself to `readers`.
7. **Summary refinement.** The summary is editable: refinement means adding detail or fixing an error; it never shortens or removes something another reader wrote. Each edit appends a `revised:` trail line stating why; git diff is the full audit.
8. **Disputes** are resolved by a human, as knowledge conflicts are (section 9). A disputed claim cannot be proposed to knowledge until resolved (`DISPUTED_IN_KNOWLEDGE`).
9. **Promotion to knowledge** happens only through the knowledge gate (propose-knowledge); the resulting fact's source is `src: <citekey> <where>` (section 12).
10. **Relevance is relative to the questions open on the ingest date.**
11. **Health signal.** session-start reports how many papers have claims no second reader has verified (section 14).

Commit subjects: `[literature] added <citekey> — <title fragment>` and `[literature] re-read <citekey> — verified <N>, disputed <N>, added <N> claims`.

## 8. Human gates

Both platforms ask the same way. The prompt states what is proposed, where it would go, and offers exactly three choices.

**When.** The gates for questions and knowledge fire immediately, each time you learn something you consider shareable, not batched at session end. The team accepts this friction: accuracy over speed. The decision gate fires when you propose a decision.

**How.** Ask before you write anything, one proposal per prompt. Print the prompt in exactly this form, with your values in place of the example values, and wait for the answer:

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

For a new knowledge topic, the prompt says `(new)` instead of `(existing)` and adds the registry line after the topic file line; propose-knowledge shows the form.

**Answers.** `Edit` returns the proposal to the user for changes and re-asks. `Skip` records nothing in the shared repo; the AI may keep it in local personal memory.

- `Commit` lets the runbook continue. The member who answered is the approver, normally the user, `<Person>`; the approver's name goes where a runbook says `<approver>`.
- Any other answer: ask again.
- Any member listed in PROJECT.md may answer (section 4).
- Local personal memory is your tool's own memory or `.ra/`, never a shared file (section 13).

## 9. Conflict rules

**Contradicting facts.** A contradiction never changes the content of an existing fact or removes it. When a new fact contradicts a fact in the topic file:

1. Insert the new fact on the line directly below the existing fact, with the status `CONFLICT with line above`.
2. Change the existing fact's status, the last segment inside its parentheses, to `CONFLICT with line below`. This is the one permitted edit to a fact someone else authored.

Both facts stay until a human resolves the pair. `superseded by <ref>` is the status of a fact that a human has replaced.

**Disputed claims** follow section 7.4 rules 6 and 8: the dispute stays beside the claim until a human resolves it.

**A second record for a paper** is never created (section 7.2).

**Git merge conflicts** follow the Conflicts rule of section 5:

1. A merge conflict is in place when `ra sync pull` exits 1 and prints `protected <path>` or `other <path>` lines after its `error:` line, or when `ra sync conflicts` exits 2 and prints such lines. `protected` marks paths under `knowledge/` or `decisions/`; `other` paths get the same treatment.
2. Stop. Do not edit, stage, restore or delete a conflicted file, and run no git command that resolves or ends the merge, such as `git add`, `git checkout`, `git restore`, `git reset` or `git merge --abort`.
3. While the conflict is in place, git refuses every commit. Write the session's log entry anyway (session-end steps 2 and 3), with the conflicted paths under `## Unfinished` and "a human resolves the merge conflict" under `## Suggested next step`, and leave it uncommitted. Make no other write and do not push.
4. Tell the user which paths conflict, and that the log entry is written but not committed.
5. Once a human has resolved the conflict and committed the merge, commit the log entry as session-end step 5 does and finish session-end from step 6.

## 10. Naming conventions

- **Citekey**: `<firstauthor><year>-<slug>`, all lowercase, `[a-z0-9-]+`: the first author's family name in ASCII letters, the four-digit year, then a slug of one to three title words. Example: `smith2024-plume-goes`. Record `literature/<citekey>.md`, PDF `literature/pdf/<citekey>.pdf`.
- **Question ID**: `Q-<date>-<slug>`, dated the day it is proposed; file `questions/<Q-id>.md`. Example: `Q-2026-10-25-plume-baselines`.
- **Decision ID**: `D-<date>-<slug>`, dated the day it is proposed; file `decisions/<D-id>.md`. Example: `D-2026-10-25-eval-metric`.
- **Slug**: `[a-z0-9-]+`, a few words joined by `-`. If `ra new` reports that the file already exists, choose another slug.
- **Log entry**: `log/<date>-<person>-<agent>-<HHMM>.md`. `<HHMM>` is the session start. `<person>` is `<Person>` case-folded, with letters and digits of any script kept, every run of other characters turned into one `-`, and hyphens trimmed from both ends: `Fan Zhou` gives `fan-zhou`, `José` gives `josé`. `ra new log` writes the name.
- **Topic**: `[a-z0-9-]+`, naming the subject, for example `goes-abi`; file `knowledge/<topic>.md`, registry line `- <topic> — <scope>` in `knowledge/README.md`.
- **Dates and times**: dates `YYYY-MM-DD`; times on the 24-hour clock as `HH:MM`, written `HHMM` in log file names; local time.
- **People and agents**: `<Person>` as in PROJECT.md Members, `<agent>` `claude-code` or `codex` (section 2).

`ra check` reports a file name that breaks these rules as `BAD_FILENAME`.

## 11. Commit conventions

Every write to the repository is its own commit with a structured message:

```
[literature] added Smith 2024 — plume segmentation from GOES imagery

Person: Fan
Agent: codex
Links: literature/smith2024-plume-goes.md, questions/Q-2026-10-25-plume-baselines.md
```

- **Type tags**: `literature` `question` `knowledge` `decision` `log` `status` `protocol`. `protocol` marks a human's change to PROJECT.md outside "Current status", to this file, CLAUDE.md, AGENTS.md or `protocol/`.
- **Subjects** follow the pattern in the Commit part of the verb's runbook (section 6).
- **One commit per logical write.** The session-end log entry is its own `[log]` commit; the status rewrite is its own `[status]` commit.
- **History is never squashed or rebased**: no `git rebase`, `git commit --amend`, `git reset` of commits or `git push --force`.
- **Commit only with `ra commit`.** It writes the message above, stages the paths given after `--`, commits and prints the new commit's sha. `--links` lists every path the commit adds, changes or cites. Whatever is already staged is committed too, so stage nothing any other way. Run `ra check` first (section 14).

```
python protocol/ra.py commit --type <tag> --subject "<subject>" --person <Person> --agent <agent> --links <path> <path> -- <path> <path>
```

## 12. File templates

`protocol/templates/` holds the templates that `ra new` fills: `literature.md`, `question.md`, `decision.md`, `log.md` and `topic.md`. Create files only with `ra new <kind>` (section 6), never by copying a template. A template's `<!-- … -->` comments are notes and are not copied. A new file starts with the template's guidance lines, such as `≤150 words, own words: problem, method, data, main result.` or `Why this matters to the project.`; replace each with real content before you commit.

The dashes and dots of the formats are exact characters: `—` is an em dash (U+2014), `–` an en dash (U+2013, only in `session:` and log subjects), and `·` a middle dot (U+00B7).

**Fact line.** A topic file has no frontmatter. Its first two lines are `# <topic>` and the scope line of its registry entry, which `ra new topic` writes; then come the facts, one per line, each with its metadata in a trailing parenthesis:

```
- <fact> (src: <citekey> <where> · <Person>/<agent> <date> · approved <approver> · <status>)
```

- `src:`: the citekey and `where` of the paper claim behind the fact. A fact that does not come from a paper names the repository file it comes from instead.
- `<Person>/<agent> <date>`: who proposed the fact, and when. `approved <approver>`: who answered `Commit` (section 8).
- `<status>`: `ok` | `CONFLICT with <ref>` | `superseded by <ref>` (section 9).

Two facts in conflict:

```
- GOES-16 ABI band 7 is 3.9 µm with 2 km nadir resolution (src: smith2024-plume-goes §2.1 p.3 · Fan/codex 2026-10-25 · approved Fan · CONFLICT with line below)
- GOES-16 ABI band 7 nadir resolution is 1 km (src: lee2023-abi-spec Table 1 · Lee/claude-code 2026-10-28 · approved Lee · CONFLICT with line above)
```

## 13. Never-in-repo list

Never commit:

- Personal memory of any team member
- Secrets, credentials, tokens
- Raw data
- Model checkpoints and large outputs
- Manuscript and grant text — a pointer to where it lives (Overleaf or similar), nothing more

Keep personal memory in your tool's user-level memory or under `.ra/`, which git ignores; never write it into CLAUDE.md, AGENTS.md or another shared file. The manuscript pointer belongs in PROJECT.md Pointers, which a human edits. If a write would include any of these, leave it out and tell the user.

## 14. Health checks

**What `check` verifies.** `python protocol/ra.py check` reads the files in `questions/`, `decisions/`, `literature/`, `literature/pdf/`, `log/` and `knowledge/`. It prints `check: no findings` and exits 0, or prints one `CODE path: message` line per finding and exits 1:

- `FM_INVALID`: frontmatter unreadable, a required key missing, or the `id` or `citekey` not equal to the file name.
- `BAD_FILENAME`: a file name that breaks the naming rule of its folder (section 10).
- `CLAIM_NO_WHERE`: a claim whose `where` is missing, empty or `—`.
- `PDF_MISSING`: a record whose `pdf:` is empty, is not `literature/pdf/<citekey>.pdf`, or names no file.
- `DUP_LITERATURE`: two records with the same DOI or arXiv ID.
- `DISPUTED_IN_KNOWLEDGE`: a fact whose source is a claim with a `disputed-by` entry.
- `TOPIC_UNREGISTERED`: a topic file without its `- <topic> — ` line in `knowledge/README.md`.
- `DECISION_EDITED`: an accepted or superseded decision with a changed line other than `status:` or `superseded-by:`. The comparison is between the commit that accepted it and the working tree, so an uncommitted edit counts.

**When to run it.** At session start (session-start step 7) and before every commit. Fix every finding your write caused before you commit. A finding that session-start already reported is not yours to fix: it is reported to the user and does not block your commits.

**What session-start reports**, in a few lines:

1. The digest: what is new since your last commit, by type.
2. The check summary: `check: no findings`, or each finding.
3. The health line, for example "12 papers; 4 have claims no second reader has verified": the number of records in `literature/`, and how many of them have a claim whose `verified-by` is `—`. Add the number of disputed claims and of facts in CONFLICT when either is not zero; they wait for a human (section 9). Counting reads only the records, which is navigation (section 7.1).

## 15. Glossary

- **Claim**: one statement a reader took from a paper for this project; a bullet under `## Claims for this project` with its `where` and provenance (section 7.3).
- **Fact**: one line of a knowledge file that the team treats as true, with its source and approval (section 12). Facts enter only through the knowledge gate.
- **Gate**: the prompt at which a human answers `Commit`, `Edit` or `Skip` to a proposed question, fact or decision (section 8).
- **Reader**: one person with one agent who read a paper, listed in the record's `readers` with how they read it.
- **Record**: the file `literature/<citekey>.md` for one paper, with its PDF.
- **Session**: one person's work with one agent, from session-start to session-end; it leaves one log entry.
- **Topic**: a knowledge file `knowledge/<topic>.md`, registered with a one-line scope in `knowledge/README.md`.
- **Use versus navigate**: navigating a record (listing, filtering, reading frontmatter) needs no PDF; using any content of a paper requires its PDF (section 7.1).
- **Verb**: one of the operations of section 6, each with a runbook.
- **Write**: a change to this repository; each logical write is one commit (section 11).

## 16. Protocol version and change procedure

- **Version.** The protocol version is the `version` in this file's frontmatter. `ra init` stamps it into PROJECT.md as `protocol-version`, so every project records the version it follows.
- **Changelog.**
  - `0.1.0 — 2026-10-25 — initial protocol`
- **Changes.** Only a human edits this file (section 2). An AI proposes a change as a unified diff of the file, in a fenced block under `## Suggested next step` of its session's log entry, and tells the user. `ra commit` messages carry no body, so the log entry is the place for the diff.
- **Adopting a new version.** A human replaces `PROTOCOL.md` and `protocol/` with those of the framework repository's `template/`, sets `protocol-version:` in PROJECT.md to the new version, and commits the three in one `[protocol]` commit:

```
python protocol/ra.py commit --type protocol --subject "adopted protocol <version>" --person <Person> --agent <agent> --links PROTOCOL.md PROJECT.md protocol -- PROTOCOL.md PROJECT.md protocol
```
