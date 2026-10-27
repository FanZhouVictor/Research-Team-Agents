---
name: propose-knowledge
description: Proposes one durable fact for the knowledge files of an RA_Agent shared research repository (a project folder holding PROTOCOL.md and protocol/ra.py) by following the propose-knowledge runbook of its PROTOCOL.md, which chooses the topic, asks a human at once with the KNOWLEDGE gate of its section 8 and, only on Commit, adds the fact line with its provenance, creating a new topic and its registry line when no topic fits, then checks, commits and pushes. Make sure to use it each time you learn a dataset fact, method detail, measured result, domain fact or project term that the team of such a project should share, rather than batching facts until the session ends, and whenever the user says "add this to the knowledge base" or "record this fact for the team", even if they do not name the skill. Keeping a note in your own memory is not proposing it.
---

## Implements

PROTOCOL.md §6 propose-knowledge, with §8, and §9 "Contradicting facts" when the fact contradicts one. Before step 1, meet the **Preconditions** of §6 propose-knowledge, and read its runbook and the sections that §2 "Per verb" names. Where this skill and PROTOCOL.md differ, follow PROTOCOL.md (§1).

## Steps

Run every command as §2 "The helper" says. `<Person>` is as §2 "Who you are" says, `<agent>` is `claude-code` (`codex` when this skill runs inside Codex). Without a remote, follow §6 session-start step 2.

1. Pull (§5):
   ```
   python protocol/ra.py sync pull
   ```
2. Choose the topic, or draft a new topic and its scope, as §6 propose-knowledge step 2 says (§10).
3. Read the topic file for a fact that the new one contradicts, as §6 propose-knowledge step 3 says.
4. Ask the human now with the §8 KNOWLEDGE prompt, verbatim, in the form that the **Ask the human** part of §6 propose-knowledge shows for an existing or a new topic, and wait for the answer, as its step 4 says; for a contradiction, first say so as that part says (§8 "When").
5. On `Commit`, if the topic is new, create it with its registry line:
   ```
   python protocol/ra.py new topic --topic <topic> --scope "<scope>"
   ```
6. Add the fact line to `knowledge/<topic>.md` as §6 propose-knowledge step 6 says (§12); for a contradiction, mark both facts as §9 "Contradicting facts" says.
7. Check (§14):
   ```
   python protocol/ra.py check
   ```
8. Commit; for a new topic, add `knowledge/README.md` as the **Commit** part of §6 propose-knowledge says:
   ```
   python protocol/ra.py commit --type knowledge --subject "<topic>: <fact fragment>" --person "<Person>" --agent <agent> --links knowledge/<topic>.md literature/<citekey>.md -- knowledge/<topic>.md
   ```
9. Push (§5):
   ```
   python protocol/ra.py sync push
   ```

## Stop conditions

- **The fact comes from a paper and you have not confirmed it in the PDF at its `where`, or a claim at that `where` is disputed**: meet the **Preconditions** of §6 propose-knowledge before step 1.
- **The human answers `Edit`, or neither `Commit` nor `Skip`**: follow §8 "Answers" and ask step 4 again.
- **The human answers `Skip`**: stop here and follow §8 "Answers".
- **No human is there to answer**: follow §8 "No one to answer".
- **`sync pull` exits 1 and prints `protected <path>` or `other <path>` lines**: stop and follow §9 "Git merge conflicts", which also says what to tell the user.
- **`sync pull` exits 1 without such lines**: stop, show the user the output, and follow §5 "During" on `ra sync pull`.
- **`sync push` exits 1**: follow §5 "During" on `ra sync push`.
- **`check` exits 1**: before you commit, do with each finding what §14 "When to run it" says.
- **`new topic` exits 1**: show the user its `error:` line and follow §2 "When a runbook does not cover it".
- **Anything else a step does not cover**: follow §2 "When a runbook does not cover it".
