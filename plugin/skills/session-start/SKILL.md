---
name: session-start
description: Opens a work session in an RA_Agent shared research repository (a project folder holding PROTOCOL.md and protocol/ra.py) by following the session-start runbook of its PROTOCOL.md, which pulls, reads PROJECT.md, lists what is new since your last commit, reads the open questions and the relevant knowledge, runs ra check and reports. Make sure to use it before any other work in such a repository, and whenever the user opens or resumes the project, says "start my session", or asks what is new in the project, what changed in it since their last session or what earlier sessions left unfinished, even if they do not name the skill.
---

## Implements

PROTOCOL.md §6 session-start, the Start of §5. Before step 1, meet the **Preconditions** of §6 session-start. Where this skill and PROTOCOL.md differ, follow PROTOCOL.md (§1).

## Steps

Run every command as §2 "The helper" says.

1. Note the session start as §6 session-start step 1 says.
2. Check for a remote:
   ```
   git remote
   ```
   If it prints nothing, follow §6 session-start step 2.
3. Pull (§5):
   ```
   python protocol/ra.py sync pull
   ```
4. Read PROJECT.md. Find your Members row and `<git author>` as §2 "Who you are" says.
5. List what is new, then read the log entries it lists, as §6 session-start step 5 says:
   ```
   python protocol/ra.py digest --person "<git author>"
   ```
6. Read the open questions as §6 session-start step 6 says.
7. Read the knowledge as §6 session-start step 7 says.
8. Run the check (§14):
   ```
   python protocol/ra.py check
   ```
9. Report to the user what §14 "What session-start reports" lists; end with what the log entries of step 5 left unfinished.

## Stop conditions

- **`sync pull` exits 1 and prints `protected <path>` or `other <path>` lines**: stop and follow §9 "Git merge conflicts", which also says what to tell the user.
- **`sync pull` exits 1 without such lines**: stop, show the user the output, and follow §5 "During" on `ra sync pull`.
- **No row in Members matches your git identity**: follow §2 "Who you are".
- **`python` is missing or too old, or the helper reports that `yaml` is missing**: follow §2 "The helper".
- **`check` exits 1**: not a stop; report its findings in step 9 as §14 says.
- **Anything a step does not cover**: follow §2 "When a runbook does not cover it".
