---
name: supersede-decision
description: Replaces an accepted decision of an RA_Agent shared research repository (a project folder holding PROTOCOL.md and protocol/ra.py) by following the supersede-decision runbook of its PROTOCOL.md, which proposes the new decision with supersedes set, waits until a human accepts it, then marks the old decision superseded with the one edit it may receive, checks, commits and pushes. Make sure to use it whenever the user of such a project wants to change, replace, revise or overturn a decision that is already accepted, for example says "we now use F1 instead of mIoU, replace D-2026-10-25-eval-metric", even if they do not name the skill. Replacing text or code is not replacing a decision.
---

## Implements

PROTOCOL.md §6 supersede-decision; it runs §6 propose-decision (step 1), and accept-decision returns to it at step 3 (accept-decision step 6). Before step 1, meet the **Preconditions** of §6 supersede-decision, and read its runbook, that of propose-decision and the sections that §2 "Per verb" names. Where this skill and PROTOCOL.md differ, follow PROTOCOL.md (§1).

## Steps

Run every command as §2 "The helper" says. `<Person>` is as §2 "Who you are" says, `<agent>` is `claude-code` (`codex` when this skill runs inside Codex). Without a remote, follow §6 session-start step 2. A step that runs another verb says where that verb's steps without a command fall, its gate among them, and shows its commands in a nested block, each run only at its own step; run that verb as §6 says.

1. Run propose-decision for the new decision, `<new-id>`, with `supersedes: <old-id>`, as §6 supersede-decision step 1 says; `<new-id>` is its `<D-id>`. Its steps 1–8 run here as steps 1.1–1.8: 1.2–1.3, the draft and its §8 DECISION gate (verbatim, after the one-line notice that its **Ask the human** part asks for), come after the pull and before `new decision`; 1.4–1.8 run only on `Commit`, and 1.5 writes the sections and `supersedes:` before the check, as §6 propose-decision steps 2–8 say. Its commands, each run at its own step:
      ```
      python protocol/ra.py sync pull
      python protocol/ra.py new decision --slug <slug> --title "<title>" --person "<Person>" --agent <agent> --link <Q-id or path> <Q-id or path>
      python protocol/ra.py check
      python protocol/ra.py commit --type decision --subject "proposed <D-id> — <title>" --person "<Person>" --agent <agent> --links decisions/<D-id>.md questions/<Q-id>.md -- decisions/<D-id>.md
      python protocol/ra.py sync push
      ```
2. Wait until a human accepts `<new-id>`, as §6 supersede-decision step 2 says; the acceptance runs accept-decision, whose step 6 continues here at step 3.
3. Pull (§5):
   ```
   python protocol/ra.py sync pull
   ```
4. Make the one edit to `decisions/<old-id>.md`, as §6 supersede-decision step 4 says.
5. Check (§14):
   ```
   python protocol/ra.py check
   ```
6. Commit:
   ```
   python protocol/ra.py commit --type decision --subject "superseded <old-id> by <new-id>" --person "<Person>" --agent <agent> --links decisions/<old-id>.md decisions/<new-id>.md -- decisions/<old-id>.md
   ```
7. Push (§5):
   ```
   python protocol/ra.py sync push
   ```

## Stop conditions

- **The decision to replace is not accepted**: follow the **Preconditions** of §6 supersede-decision.
- **The gate of step 1 is answered `Edit` or `Skip`, or no human is there to answer it**: do what §8 says.
- **No human has accepted `<new-id>` yet**: stop at step 2, as §6 supersede-decision step 2 says.
- **`sync pull` exits 1 and prints `protected <path>` or `other <path>` lines**: stop and follow §9 "Git merge conflicts", which also says what to tell the user.
- **`sync pull` exits 1 without such lines**: stop, show the user the output, and follow §5 "During" on `ra sync pull`.
- **`sync push` exits 1**: follow §5 "During" on `ra sync push`.
- **`check` exits 1**: before you commit, do with each finding what §14 "When to run it" says.
- **Anything else a step does not cover**: follow §2 "When a runbook does not cover it".
