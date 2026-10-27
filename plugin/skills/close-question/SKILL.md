---
name: close-question
description: Closes an open question of an RA_Agent shared research repository (a project folder holding PROTOCOL.md and protocol/ra.py) as answered or dropped by following the close-question runbook of its PROTOCOL.md, which sets the question's status, answered-by and closed-by, checks, commits and pushes. It runs only when a member of the project tells you to close a question. Make sure to use it whenever such a member says, for example, "close Q-2026-10-25-plume-baselines, knowledge/goes-abi.md answers it" or "drop that question", even if they do not name the skill. Never use it on your own judgement, even when a question looks answered. Closing a file, an issue or a pull request is not closing a question.
---

## Implements

PROTOCOL.md §6 close-question. Only a human starts it: before step 1, meet the **Preconditions** of §6 close-question (§4). Where this skill and PROTOCOL.md differ, follow PROTOCOL.md (§1).

## Steps

Run every command as §2 "The helper" says. `<Person>` is as §2 "Who you are" says, `<agent>` is `claude-code` (`codex` when this skill runs inside Codex). Without a remote, follow §6 session-start step 2.

1. Pull (§5):
   ```
   python protocol/ra.py sync pull
   ```
2. Ask the human what they have not said yet, as §6 close-question step 2 says.
3. Set the three frontmatter lines of `questions/<Q-id>.md`, as §6 close-question step 3 says.
4. Optionally add a working note, as §6 close-question step 4 says.
5. Check (§14):
   ```
   python protocol/ra.py check
   ```
6. Commit, with the `answered-by:` path of step 3 in place of `<answered-by path>`:
   ```
   python protocol/ra.py commit --type question --subject "closed <Q-id>" --person "<Person>" --agent <agent> --links questions/<Q-id>.md <answered-by path> -- questions/<Q-id>.md
   ```
7. Push (§5):
   ```
   python protocol/ra.py sync push
   ```

## Stop conditions

- **No human told you to close the question, or its `status` is not `open`**: do not close it; follow the **Preconditions** of §6 close-question.
- **`sync pull` exits 1 and prints `protected <path>` or `other <path>` lines**: stop and follow §9 "Git merge conflicts", which also says what to tell the user.
- **`sync pull` exits 1 without such lines**: stop, show the user the output, and follow §5 "During" on `ra sync pull`.
- **`sync push` exits 1**: follow §5 "During" on `ra sync push`.
- **`check` exits 1**: before you commit, do with each finding what §14 "When to run it" says.
- **Anything else a step does not cover**: follow §2 "When a runbook does not cover it".
