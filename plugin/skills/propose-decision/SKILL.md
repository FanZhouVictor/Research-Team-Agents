---
name: propose-decision
description: Proposes a decision for an RA_Agent shared research repository (a project folder holding PROTOCOL.md and protocol/ra.py) by following the propose-decision runbook of its PROTOCOL.md, which drafts the decision with its evidence, asks a human at once with the DECISION gate of its section 8 and, only on Commit, creates the decision file in status proposed, checks, commits and pushes; a human accepts it later. Make sure to use it whenever a choice the project should record comes up in such a project, such as a metric, dataset, baseline or method to adopt, or the user says "record this as a decision" or "let's make this a project decision", even if they do not name the skill. A choice you make while writing your own code or text is not a project decision.
---

## Implements

PROTOCOL.md §6 propose-decision, with §8. Before step 1, meet the **Preconditions** of §6 propose-decision, and read its runbook and the sections that §2 "Per verb" names. Where this skill and PROTOCOL.md differ, follow PROTOCOL.md (§1).

## Steps

Run every command as §2 "The helper" says. `<Person>` is as §2 "Who you are" says, `<agent>` is `claude-code` (`codex` when this skill runs inside Codex). Without a remote, follow §6 session-start step 2.

1. Pull (§5):
   ```
   python protocol/ra.py sync pull
   ```
2. Draft the ID, the title, the evidence links and the four sections, as §6 propose-decision step 2 says (§10).
3. Ask the human now with the §8 DECISION prompt, verbatim, and wait for the answer, as §6 propose-decision step 3 says; when the decision replaces another, first say so as its **Ask the human** part says (§8 "When").
4. On `Commit`, create the decision file with its evidence links; it prints its path:
   ```
   python protocol/ra.py new decision --slug <slug> --title "<title>" --person "<Person>" --agent <agent> --link <Q-id or path> <Q-id or path>
   ```
5. Write the four sections in the file step 4 printed, and `supersedes:` when the decision replaces another, as §6 propose-decision step 5 says.
6. Check (§14):
   ```
   python protocol/ra.py check
   ```
7. Commit, with `<D-id>` taken from the path step 4 printed and `--links` as the **Commit** part of §6 propose-decision says:
   ```
   python protocol/ra.py commit --type decision --subject "proposed <D-id> — <title>" --person "<Person>" --agent <agent> --links decisions/<D-id>.md questions/<Q-id>.md -- decisions/<D-id>.md
   ```
8. Push (§5):
   ```
   python protocol/ra.py sync push
   ```

## Stop conditions

- **The human answers `Edit`, or neither `Commit` nor `Skip`**: follow §8 "Answers" and ask step 3 again.
- **The human answers `Skip`**: stop here and follow §8 "Answers".
- **No human is there to answer**: follow §8 "No one to answer".
- **`sync pull` exits 1 and prints `protected <path>` or `other <path>` lines**: stop and follow §9 "Git merge conflicts", which also says what to tell the user.
- **`sync pull` exits 1 without such lines**: stop, show the user the output, and follow §5 "During" on `ra sync pull`.
- **`sync push` exits 1**: follow §5 "During" on `ra sync push`.
- **`check` exits 1**: before you commit, do with each finding what §14 "When to run it" says.
- **`new decision` exits 1**: if its `error:` line says that the file already exists, follow §10 "Slug"; otherwise show the user the line and follow §2 "When a runbook does not cover it".
- **Anything else a step does not cover**: follow §2 "When a runbook does not cover it".
