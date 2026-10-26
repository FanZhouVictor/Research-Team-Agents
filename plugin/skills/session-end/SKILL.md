---
name: session-end
description: Ends a work session in an RA_Agent shared research repository (a project folder holding PROTOCOL.md and protocol/ra.py) by following the session-end runbook of its PROTOCOL.md, which pulls, writes and commits the session's log entry, rewrites and commits the Current status of PROJECT.md, checks for merge conflicts and pushes. Make sure to use it whenever the user ends or wraps up the session, says "end my session", "wrap up", "write the log" or "that's all for today", or is about to leave such a repository, so that no session ends without its log entry.
---

## Implements

PROTOCOL.md §6 session-end, which runs §6 update-status as its step 6; the End of §5. Read both runbooks first (§2 "Per verb"). Where this skill and PROTOCOL.md differ, follow PROTOCOL.md (§1).

## Steps

Run every command from the project root. `<Person>` is the Person of your row in PROJECT.md Members (§2 "Who you are"), `<agent>` is `claude-code`, and `<YYYY-MM-DDTHH:MM>` is the start that session-start step 1 noted. Without a remote, skip every `sync pull` and `sync push` (session-start step 2).

1. Pull (§5):
   ```
   python protocol/ra.py sync pull
   ```
2. Create the log entry; it prints the path:
   ```
   python protocol/ra.py new log --person <Person> --agent <agent> --start <YYYY-MM-DDTHH:MM>
   ```
3. Fill the entry as runbook step 3 says: the end time in `session:`, then all five headings, replacing any guidance line the template left (§12).
4. Check (§14):
   ```
   python protocol/ra.py check
   ```
5. Commit the log entry:
   ```
   python protocol/ra.py commit --type log --subject "session <Person>/<agent> <date> <HH:MM>–<HH:MM>" --person <Person> --agent <agent> --links log/<date>-<person>-<agent>-<HHMM>.md -- log/<date>-<person>-<agent>-<HHMM>.md
   ```
6. Run update-status (§6 update-status); it makes the `[status]` commit:
   1. Pull:
      ```
      python protocol/ra.py sync pull
      ```
   2. Rewrite only `## Current status` of PROJECT.md as its step 2 says. If the status has not changed, change nothing and go on with step 7.
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
7. Make sure no merge conflict is in place; `sync: no conflicts` (exit 0) means go on:
   ```
   python protocol/ra.py sync conflicts
   ```
8. Push (§5):
   ```
   python protocol/ra.py sync push
   ```

## Stop conditions

- **A merge conflict is in place** (`sync pull` exits 1 and prints `protected <path>` or `other <path>` lines, or `sync conflicts` exits 2): stop as PROTOCOL.md §9 "Git merge conflicts" says. Resolve nothing; write the log entry but leave it uncommitted; tell the user which paths conflict.
- **`sync pull` exits 1 without such lines**: show the user the output; go on without the pull only with their go-ahead (§5).
- **`sync push` exits 1**: pull and push once more; if that fails too, tell the user (§5).
- **`check` reports a finding this session caused**: fix it before you commit. `DISPUTED_IN_KNOWLEDGE` is the exception: commit anyway and do what §14 says for it. A finding you did not cause is reported, not fixed, and does not block the commits (§14).
- **No session start was noted** (session-start did not run in this session): ask the user (§2 "When a runbook does not cover it").
- **Anything else a step does not cover**: stop, name the section, ask the user (§2).
