---
name: reread-literature
description: Re-reads a paper that already has a record in an RA_Agent shared research repository (a project folder holding PROTOCOL.md and protocol/ra.py) by following the reread-literature runbook of its PROTOCOL.md, which reads the whole PDF, verifies or disputes each existing claim at its where, appends new claims, refines the summary, adds you to the record's readers, checks, commits and pushes. Make sure to use it whenever add-literature finds that a paper already has a record, or the user of such a project asks you to re-read a recorded paper, verify or dispute its claims or add claims to its record, for example says "re-read smith2024-plume-goes" or "verify the claims of this paper", even if they do not name the skill. Opening a record or its PDF only to answer a question does not re-read it.
---

## Implements

PROTOCOL.md §6 reread-literature, with §7; it runs §6 propose-question (step 3). Before step 1, meet the **Preconditions** of §6 reread-literature, and read its runbook, that of propose-question and the sections that §2 "Per verb" names. Where this skill and PROTOCOL.md differ, follow PROTOCOL.md (§1).

## Steps

Run every command as §2 "The helper" says. `<Person>` is as §2 "Who you are" says, `<agent>` is `claude-code` (`codex` when this skill runs inside Codex). Without a remote, follow §6 session-start step 2. A step that runs another verb says where that verb's steps without a command fall, its gate among them, and shows its commands in a nested block, each run only at its own step; run that verb as §6 says.

1. Pull (§5):
   ```
   python protocol/ra.py sync pull
   ```
2. Read the whole PDF before the record's claims, as §6 reread-literature step 2 says (§7.1).
3. Draft the claims the record misses, as §6 reread-literature step 3 says; for one that bears on no existing question, run propose-question now. Its steps 1–9 run here as steps 3.1–3.9: 3.2–3.4, the search, the draft and its §8 QUESTION gate (verbatim), come after the pull and before `new question`; 3.5–3.9 run only on `Commit`, and 3.6 fills the new file before the check, as §6 propose-question steps 2–9 say. Its commands, each run at its own step:
      ```
      python protocol/ra.py sync pull
      python protocol/ra.py new question --slug <slug> --title "<title>" --person "<Person>" --agent <agent>
      python protocol/ra.py check
      python protocol/ra.py commit --type question --subject "proposed <Q-id> — <title>" --person "<Person>" --agent <agent> --links questions/<Q-id>.md -- questions/<Q-id>.md
      python protocol/ra.py sync push
      ```
4. For each existing claim, open the PDF at its `where` and add yourself to exactly one of `verified-by` and `disputed-by`, as §6 reread-literature step 4 says (§7.4 rule 6).
5. Append the claims of step 3 with your own `by:`, as §6 reread-literature step 5 says.
6. If the summary misses a detail or has an error, refine it and append its `revised:` line, as §6 reread-literature step 6 says (§7.4 rule 7).
7. Add yourself to the record's `readers`, as §6 reread-literature step 7 says.
8. Optionally add a note, as §6 reread-literature step 8 says.
9. Check, as §6 reread-literature step 9 says (§14):
   ```
   python protocol/ra.py check
   ```
10. Commit, with each `<N>` as the **Commit** part of §6 reread-literature says:
    ```
    python protocol/ra.py commit --type literature --subject "re-read <citekey> — verified <N>, disputed <N>, added <N> claims" --person "<Person>" --agent <agent> --links literature/<citekey>.md -- literature/<citekey>.md
    ```
11. Push (§5):
    ```
    python protocol/ra.py sync push
    ```

## Stop conditions

- **You are already in `readers` as `<Person>` with `<agent>`**, for example to append a claim whose question was approved in a later session: follow the **Preconditions** of §6 reread-literature.
- **`sync pull` exits 1 and prints `protected <path>` or `other <path>` lines**: stop and follow §9 "Git merge conflicts", which also says what to tell the user.
- **`sync pull` exits 1 without such lines**: stop, show the user the output, and follow §5 "During" on `ra sync pull`.
- **`sync push` exits 1**: follow §5 "During" on `ra sync push`.
- **`check` exits 1**: before you commit, do with each finding what §14 "When to run it" says.
- **The gate of step 3 is answered `Edit` or `Skip`, or no human is there to answer it**: do what §8 says.
- **`new question` exits 1**: if its `error:` line says that the file already exists, follow §10 "Slug"; otherwise show the user the line and follow §2 "When a runbook does not cover it".
- **Anything else a step does not cover**: follow §2 "When a runbook does not cover it".
