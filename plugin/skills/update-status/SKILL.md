---
name: update-status
description: Rewrites the Current status section of PROJECT.md in an RA_Agent shared research repository (a project folder holding PROTOCOL.md and protocol/ra.py) by following the update-status runbook of its PROTOCOL.md, which rewrites only that section, then checks, commits and pushes. session-end runs it at the end of every session. Make sure to use it on its own whenever the user of such a project asks you to update, refresh or rewrite the project's current status, for example says "update the project status" or "refresh Current status in PROJECT.md", even if they do not name the skill. A status report you give the user in conversation is not this update.
---

## Implements

PROTOCOL.md §6 update-status, which session-end runs as its step 6. Before step 1, meet the **Preconditions** of §6 update-status. Where this skill and PROTOCOL.md differ, follow PROTOCOL.md (§1).

## Steps

Run every command as §2 "The helper" says. `<Person>` is as §2 "Who you are" says, `<agent>` is `claude-code` (`codex` when this skill runs inside Codex). Without a remote, follow §6 session-start step 2.

1. Pull, unless session-end runs this skill, as §6 update-status step 1 says (§5):
   ```
   python protocol/ra.py sync pull
   ```
2. Rewrite only `## Current status` of PROJECT.md, as §6 update-status step 2 says; it also says when to skip steps 3–5.
3. Check (§14):
   ```
   python protocol/ra.py check
   ```
4. Commit:
   ```
   python protocol/ra.py commit --type status --subject "current status after the <Person>/<agent> session of <date>" --person "<Person>" --agent <agent> --links PROJECT.md -- PROJECT.md
   ```
5. Push, unless session-end runs this skill, as §6 update-status step 5 says (§5):
   ```
   python protocol/ra.py sync push
   ```

## Stop conditions

- **Neither the user nor session-end asked for it**: do not run it; follow the **Preconditions** of §6 update-status.
- **`sync pull` exits 1 and prints `protected <path>` or `other <path>` lines**: stop and follow §9 "Git merge conflicts", which also says what to tell the user.
- **`sync pull` exits 1 without such lines**: stop, show the user the output, and follow §5 "During" on `ra sync pull`.
- **`sync push` exits 1**: follow §5 "During" on `ra sync push`.
- **`check` exits 1**: before you commit, do with each finding what §14 "When to run it" says.
- **Anything else a step does not cover**: follow §2 "When a runbook does not cover it".
