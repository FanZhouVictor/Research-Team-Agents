---
name: session-end
description: Ends a work session in an RA_Agent shared research repository (a project folder holding PROTOCOL.md and protocol/ra.py) by following the session-end runbook of its PROTOCOL.md, which pulls, writes and commits the session's log entry, rewrites and commits the Current status of PROJECT.md, checks for merge conflicts and pushes. Make sure to use it whenever the user ends the work session in such a repository, for example says "end my session", "write the session log" or "I'm done for today in this project", so that no session ends without its log entry. Finishing or wrapping up a piece of code or text does not end the session.
---

## Implements

PROTOCOL.md §6 session-end, which runs §6 update-status as its step 6; the End of §5. Before step 1, meet the **Preconditions** of §6 session-end and read both runbooks (§2 "Per verb"). Where this skill and PROTOCOL.md differ, follow PROTOCOL.md (§1).

## Steps

Run every command as §2 "The helper" says. `<Person>` is as §2 "Who you are" says, `<agent>` is `claude-code`, and `<YYYY-MM-DDTHH:MM>` is the start you noted at session-start step 1. Without a remote, follow §6 session-start step 2.

1. Pull (§5):
   ```
   python protocol/ra.py sync pull
   ```
2. Create the log entry; it prints the path of the new file:
   ```
   python protocol/ra.py new log --person <Person> --agent <agent> --start <YYYY-MM-DDTHH:MM>
   ```
3. Fill the file whose path step 2 printed, as §6 session-end step 3 says.
4. Check (§14):
   ```
   python protocol/ra.py check
   ```
5. Commit the log entry, with the path step 2 printed in place of `log/<date>-<person>-<agent>-<HHMM>.md`:
   ```
   python protocol/ra.py commit --type log --subject "session <Person>/<agent> <date> <HH:MM>–<HH:MM>" --person <Person> --agent <agent> --links log/<date>-<person>-<agent>-<HHMM>.md -- log/<date>-<person>-<agent>-<HHMM>.md
   ```
6. Run update-status (§6 update-status); it makes the `[status]` commit:
   1. Pull:
      ```
      python protocol/ra.py sync pull
      ```
   2. Update `## Current status` of PROJECT.md as update-status step 2 says; its steps 3–5 are steps 6.3–6.5 here.
   3. Check:
      ```
      python protocol/ra.py check
      ```
   4. Commit:
      ```
      python protocol/ra.py commit --type status --subject "<one-line summary of the new status>" --person <Person> --agent <agent> --links PROJECT.md -- PROJECT.md
      ```
   5. Push:
      ```
      python protocol/ra.py sync push
      ```
7. Make sure no merge conflict is in place (§9):
   ```
   python protocol/ra.py sync conflicts
   ```
8. Push (§5):
   ```
   python protocol/ra.py sync push
   ```

## Stop conditions

- **`sync pull` exits 1 and prints `protected <path>` or `other <path>` lines, or `sync conflicts` exits 2**: stop and follow §9 "Git merge conflicts", which also says what to tell the user.
- **`sync pull` exits 1 without such lines**: stop, show the user the output, and follow §5 "During" on `ra sync pull`.
- **`sync push` exits 1**: follow §5 "During" on `ra sync push`.
- **`check` exits 1**: before you commit, do with each finding what §14 "When to run it" says.
- **No session start was noted** (session-start did not run in this session): follow §2 "When a runbook does not cover it".
- **Anything else a step does not cover**: follow §2 "When a runbook does not cover it".
