---
name: accept-decision
description: Records that a human accepted a proposed decision in an RA_Agent shared research repository (a project folder holding PROTOCOL.md and protocol/ra.py) by following the accept-decision runbook of its PROTOCOL.md, which changes only the decision's status and accepted-by lines, checks, commits and pushes, and then finishes the supersession when the decision supersedes another. It runs only when a member of the project tells you to accept a decision. Make sure to use it whenever such a member says, for example, "accept D-2026-10-25-eval-metric" or "we agreed, mark that decision accepted", even if they do not name the skill. Never infer an acceptance from a discussion or from your own judgement; agreeing with a suggestion in conversation is not accepting a decision.
---

## Implements

PROTOCOL.md §6 accept-decision; at step 6 it continues with §6 supersede-decision from its step 3. Only a human accepts: before step 1, meet the **Preconditions** of §6 accept-decision (§4). Where this skill and PROTOCOL.md differ, follow PROTOCOL.md (§1).

## Steps

Run every command as §2 "The helper" says. `<Person>` is as §2 "Who you are" says, `<agent>` is `claude-code` (`codex` when this skill runs inside Codex). Without a remote, follow §6 session-start step 2. A step that runs another verb shows that verb's commands in a nested block, in the order its steps run them; run that verb as §6 says.

1. Pull (§5):
   ```
   python protocol/ra.py sync pull
   ```
2. Change only the `status:` and `accepted-by:` lines of `decisions/<D-id>.md`, as §6 accept-decision step 2 says (§14 `DECISION_EDITED`).
3. Check (§14):
   ```
   python protocol/ra.py check
   ```
4. Commit:
   ```
   python protocol/ra.py commit --type decision --subject "accepted <D-id>" --person "<Person>" --agent <agent> --links decisions/<D-id>.md -- decisions/<D-id>.md
   ```
5. Push (§5):
   ```
   python protocol/ra.py sync push
   ```
6. If its `supersedes:` names a decision, continue with supersede-decision from its step 3, as §6 accept-decision step 6 says, with `<new-id>` the decision you accepted and `<old-id>` the one its `supersedes:` names. Its steps 3–7 run here as steps 6.3–6.7, with these commands:
      ```
      python protocol/ra.py sync pull
      python protocol/ra.py check
      python protocol/ra.py commit --type decision --subject "superseded <old-id> by <new-id>" --person "<Person>" --agent <agent> --links decisions/<old-id>.md decisions/<new-id>.md -- decisions/<old-id>.md
      python protocol/ra.py sync push
      ```

## Stop conditions

- **No human told you to accept the decision, or its `status` is not `proposed`**: do not accept it; follow the **Preconditions** of §6 accept-decision.
- **`sync pull` exits 1 and prints `protected <path>` or `other <path>` lines**: stop and follow §9 "Git merge conflicts", which also says what to tell the user.
- **`sync pull` exits 1 without such lines**: stop, show the user the output, and follow §5 "During" on `ra sync pull`.
- **`sync push` exits 1**: follow §5 "During" on `ra sync push`.
- **`check` exits 1**: before you commit, do with each finding what §14 "When to run it" says.
- **Anything else a step does not cover**: follow §2 "When a runbook does not cover it".
