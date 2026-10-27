---
name: add-literature
description: Adds a paper to an RA_Agent shared research repository (a project folder holding PROTOCOL.md and protocol/ra.py) by following the add-literature runbook of its PROTOCOL.md, which looks for an existing record with ra dedup, reads the whole PDF, creates the record with its claims for the project, checks, commits and pushes, and hands a paper that already has a record to reread-literature. Make sure to use it whenever the user gives you a paper PDF for such a project or asks you to add, ingest or record a paper in its literature, for example says "add this paper to the project" or "put smith2024.pdf in our literature", even if they do not name the skill. Reading or summarising a paper only to answer a question does not add it.
---

## Implements

PROTOCOL.md §6 add-literature, with §7; it runs §6 reread-literature (step 4), propose-question (step 7) and propose-knowledge (step 13). Before step 1, meet the **Preconditions** of §6 add-literature, and read its runbook, those of the verbs it runs and the sections that §2 "Per verb" names. Where this skill and PROTOCOL.md differ, follow PROTOCOL.md (§1).

## Steps

Run every command as §2 "The helper" says. `<Person>` is as §2 "Who you are" says, `<agent>` is `claude-code` (`codex` when this skill runs inside Codex). Without a remote, follow §6 session-start step 2. A step that runs another verb says where that verb's steps without a command fall, its gate among them, and shows its commands in a nested block, each run only at its own step; run that verb as §6 says.

1. Pull (§5):
   ```
   python protocol/ra.py sync pull
   ```
2. Note the DOI, arXiv id and title from the PDF, as §6 add-literature step 2 says.
3. Look for an existing record with the values step 2 noted (§7.2):
   ```
   python protocol/ra.py dedup --doi <DOI> --arxiv <arXiv id> --title "<title>"
   ```
4. If it prints `literature/<citekey>.md`, run reread-literature on that record instead, as §6 add-literature step 4 says; add-literature ends there. Its steps 1–11 run here as steps 4.1–4.11: 4.2–4.8, the full read, the drafts of new claims (with propose-question and its §8 QUESTION gate for one that bears on no existing question), one verification or dispute per existing claim, the new claims, the summary, `readers` and a note, come after the pull and before the check, as §6 reread-literature steps 2–8 say. Its commands, each run at its own step:
      ```
      python protocol/ra.py sync pull
      python protocol/ra.py check
      python protocol/ra.py commit --type literature --subject "re-read <citekey> — verified <N>, disputed <N>, added <N> claims" --person "<Person>" --agent <agent> --links literature/<citekey>.md -- literature/<citekey>.md
      python protocol/ra.py sync push
      ```
5. If it prints `none`, read the whole PDF (§7.1).
6. Decide the relevance and draft the claims, as §6 add-literature step 6 says.
7. For a claim that bears on no existing question, run propose-question first and keep the claim only on `Commit`, as §6 add-literature step 7 says. Its steps 1–9 run here as steps 7.1–7.9: 7.2–7.4, the search, the draft and its §8 QUESTION gate (verbatim), come after the pull and before `new question`; 7.5–7.9 run only on `Commit`, and 7.6 fills the new file before the check, as §6 propose-question steps 2–9 say. Its commands, each run at its own step:
      ```
      python protocol/ra.py sync pull
      python protocol/ra.py new question --slug <slug> --title "<title>" --person "<Person>" --agent <agent>
      python protocol/ra.py check
      python protocol/ra.py commit --type question --subject "proposed <Q-id> — <title>" --person "<Person>" --agent <agent> --links questions/<Q-id>.md -- questions/<Q-id>.md
      python protocol/ra.py sync push
      ```
8. Choose the citekey (§10) and create the record, which also copies the PDF, with the values §6 add-literature step 8 says:
   ```
   python protocol/ra.py new literature --citekey <citekey> --pdf "<path to the PDF>" --person "<Person>" --agent <agent> --title "<title>" --year <year> --authors "<Family I>; <Family I>" --venue "<venue>" --doi <DOI> --arxiv <arXiv id> --relevance <relevance> --bears-on <Q-id> <Q-id>
   ```
9. Fill `literature/<citekey>.md` as §6 add-literature step 9 says.
10. Check (§14):
    ```
    python protocol/ra.py check
    ```
11. Commit, with `--links` and `<title fragment>` as the **Commit** part of §6 add-literature says:
    ```
    python protocol/ra.py commit --type literature --subject "added <citekey> — <title fragment>" --person "<Person>" --agent <agent> --links literature/<citekey>.md literature/pdf/<citekey>.pdf questions/<Q-id>.md -- literature/<citekey>.md literature/pdf/<citekey>.pdf
    ```
12. Push (§5):
    ```
    python protocol/ra.py sync push
    ```
13. For each claim the team should treat as a durable fact, run propose-knowledge now, as §6 add-literature step 13 says. Its steps 1–9 run here as steps 13.1–13.9: 13.2–13.4, the topic, the contradiction check and its §8 KNOWLEDGE gate (verbatim), come after the pull; 13.5–13.9 run only on `Commit`, `new topic` only for a new topic, and 13.6 adds the fact line before the check, as §6 propose-knowledge steps 2–9 say. Its commands, each run at its own step:
       ```
       python protocol/ra.py sync pull
       python protocol/ra.py new topic --topic <topic> --scope "<scope>"
       python protocol/ra.py check
       python protocol/ra.py commit --type knowledge --subject "<topic>: <fact fragment>" --person "<Person>" --agent <agent> --links knowledge/<topic>.md literature/<citekey>.md -- knowledge/<topic>.md
       python protocol/ra.py sync push
       ```

## Stop conditions

- **The user gave no PDF file on this machine**: ask for its path; meet the **Preconditions** of §6 add-literature.
- **`sync pull` exits 1 and prints `protected <path>` or `other <path>` lines**: stop and follow §9 "Git merge conflicts", which also says what to tell the user.
- **`sync pull` exits 1 without such lines**: stop, show the user the output, and follow §5 "During" on `ra sync pull`.
- **`sync push` exits 1**: follow §5 "During" on `ra sync push`.
- **`check` exits 1**: before you commit, do with each finding what §14 "When to run it" says.
- **The gate of step 7 or 13 is answered `Edit` or `Skip`, or no human is there to answer it**: do what §8 says.
- **`new literature` or `new question` exits 1**: if its `error:` line says that the file already exists, follow §10 "Slug"; otherwise show the user the line and follow §2 "When a runbook does not cover it".
- **Anything else a step does not cover**: follow §2 "When a runbook does not cover it".
