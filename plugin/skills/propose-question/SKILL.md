---
name: propose-question
description: Proposes a new open question for an RA_Agent shared research repository (a project folder holding PROTOCOL.md and protocol/ra.py) by following the propose-question runbook of its PROTOCOL.md, which drafts the question, asks a human at once with the QUESTION gate of its section 8 and, only on Commit, creates the question file, checks, commits and pushes. Make sure to use it each time a question the team should track comes up in such a project, from a paper, the user or your own work, rather than batching questions until the session ends, and whenever the user says "add this as an open question" or "we should track this question", even if they do not name the skill. A question you ask the user in conversation is not a project question.
---

## Implements

PROTOCOL.md §6 propose-question, with §8. Before step 1, meet the **Preconditions** of §6 propose-question, and read its runbook and the sections that §2 "Per verb" names. Where this skill and PROTOCOL.md differ, follow PROTOCOL.md (§1).

## Steps

Run every command as §2 "The helper" says. `<Person>` is as §2 "Who you are" says, `<agent>` is `claude-code` (`codex` when this skill runs inside Codex). Without a remote, follow §6 session-start step 2.

1. Pull (§5):
   ```
   python protocol/ra.py sync pull
   ```
2. Read the titles in `questions/`, as §6 propose-question step 2 says.
3. Draft the ID, the title and the context, as §6 propose-question step 3 says (§10).
4. Ask the human now with the §8 QUESTION prompt, verbatim, and wait for the answer, as §6 propose-question step 4 says (§8 "When").
5. On `Commit`, create the question file; it prints its path:
   ```
   python protocol/ra.py new question --slug <slug> --title "<title>" --person "<Person>" --agent <agent>
   ```
6. In the file step 5 printed, fill `approved-by` and the context, as §6 propose-question step 6 says.
7. Check (§14):
   ```
   python protocol/ra.py check
   ```
8. Commit, with `<Q-id>` taken from the path step 5 printed:
   ```
   python protocol/ra.py commit --type question --subject "proposed <Q-id> — <title>" --person "<Person>" --agent <agent> --links questions/<Q-id>.md -- questions/<Q-id>.md
   ```
9. Push (§5):
   ```
   python protocol/ra.py sync push
   ```

## Stop conditions

- **A question in `questions/` already asks it**: follow §6 propose-question step 2.
- **The human answers `Edit`, or neither `Commit` nor `Skip`**: follow §8 "Answers" and ask step 4 again.
- **The human answers `Skip`**: stop here and follow §8 "Answers".
- **No human is there to answer**: follow §8 "No one to answer".
- **`sync pull` exits 1 and prints `protected <path>` or `other <path>` lines**: stop and follow §9 "Git merge conflicts", which also says what to tell the user.
- **`sync pull` exits 1 without such lines**: stop, show the user the output, and follow §5 "During" on `ra sync pull`.
- **`sync push` exits 1**: follow §5 "During" on `ra sync push`.
- **`check` exits 1**: before you commit, do with each finding what §14 "When to run it" says.
- **`new question` exits 1**: if its `error:` line says that the file already exists, follow §10 "Slug"; otherwise show the user the line and follow §2 "When a runbook does not cover it".
- **Anything else a step does not cover**: follow §2 "When a runbook does not cover it".
