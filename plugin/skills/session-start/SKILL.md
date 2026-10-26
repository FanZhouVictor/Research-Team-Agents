---
name: session-start
description: Opens a work session in an RA_Agent shared research repository (a project folder holding PROTOCOL.md and protocol/ra.py) by following the session-start runbook of its PROTOCOL.md, which pulls, reads PROJECT.md, lists what is new since your last commit, reads the open questions and the relevant knowledge, runs ra check and reports. Make sure to use it before any other work in such a repository, and whenever the user opens or resumes the project, says "start my session", or asks what is new, what changed or what was left unfinished, even if they do not name the skill.
---

## Implements

PROTOCOL.md §6 session-start, the Start of §5. Its precondition: you have read PROTOCOL.md §1–5, 9 and 11 (§2). Where this skill and PROTOCOL.md differ, follow PROTOCOL.md (§1).

## Steps

Run every command from the project root, the folder that holds PROJECT.md (§2 "The helper").

1. Note the session start as `YYYY-MM-DDTHH:MM`, local time; session-end needs it.
2. Check for a remote:
   ```
   git remote
   ```
   No output: tell the user once, and skip every `sync pull` and `sync push` this session.
3. Pull (§5):
   ```
   python protocol/ra.py sync pull
   ```
4. Read PROJECT.md. Find your row in Members as §2 "Who you are" says; its Git author name is `<git author>`.
5. List what is new since your last commit, then read `## Unfinished` and `## Suggested next step` of each log entry it lists (runbook step 5 says how a log subject names its file):
   ```
   python protocol/ra.py digest --person "<git author>"
   ```
6. Read the frontmatter and `## Context` of every file in `questions/` with `status: open`.
7. Read `knowledge/README.md`, then only the knowledge files relevant to the task at hand.
8. Run the check; its findings are the ones from before your writes (§14):
   ```
   python protocol/ra.py check
   ```
9. Report what §14 "What session-start reports" lists: the digest, the check summary and the health line. End with what is new and what earlier sessions left unfinished.

## Stop conditions

- **`sync pull` exits 1 and prints `protected <path>` or `other <path>` lines**: a merge conflict is in place. Stop as PROTOCOL.md §9 "Git merge conflicts" says; never resolve it; tell the user which paths conflict.
- **`sync pull` exits 1 without such lines** (no network, no upstream branch, a local change in the way): show the user the output; go on without the pull only with their go-ahead (§5).
- **No row in Members matches your git identity**: ask the user which member they are; never add a member (§2 "Who you are").
- **`python` is missing or too old, or the helper reports that `yaml` is missing**: follow §2 "The helper".
- **`check` exits 1**: not a stop. Report every finding; a finding you did not cause is reported, not fixed (§14).
- **Anything a step does not cover**: stop, name the section, ask the user (§2 "When a runbook does not cover it").
