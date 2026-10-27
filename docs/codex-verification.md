# Codex runnable-alone verification

Status, 2026-10-27: prompts 1, 2a, 2b and 3 ran in the Codex macOS app with no skills and passed, with no claim written and no gate fired (section 6). The skill-folder check passed in the same app: it loads and uses skill folders (section 5). The with-skills repeat of prompts 1, 2 and 3 is open.

## 1. Purpose

Spec §13 (`docs/superpowers/specs/2026-10-25-ra-agent-framework-stage0-design.md`) sets the runnable-alone test: a fresh Codex session with no plugin, pointed at `AGENTS.md`, must perform every verb correctly from `PROTOCOL.md` and the repository alone. Spec §18 assumes the team's Codex version either loads skill folders or runs from `AGENTS.md` → `PROTOCOL.md` alone. Sections 2 to 4 test the second case; section 5 checks the first. In this file, "section N" is a section of this file, and `§N` is a section of PROTOCOL.md unless the text says "spec".

A prompt **passes** when:

1. Codex opens `PROTOCOL.md` before any other command, without being told to. Codex loads `AGENTS.md` by itself; `AGENTS.md` is what sends it to `PROTOCOL.md`.
2. It runs session-start before any other verb in the session (§6: every verb other than session-start needs it).
3. It runs the commands of each verb's runbook (§6) in the runbook's order, as `python protocol/ra.py <command>` (`python3` where §2 allows it).
4. It reads the whole PDF before it writes a claim (§7.1).
5. `python protocol/ra.py check` prints `check: no findings` after its writes.
6. Each commit subject matches the pattern in the Commit part of the runbook (format: §11).
7. It stops where the protocol says: when no Members row matches the git identity it asks the user which member they are (§2), and at a gate (§8) it asks and writes nothing of the proposal before the answer `Commit`.

A **deviation** is a step that breaks one of these. A **hesitation** is a point where Codex stopped to ask, or went back to the text for something it should have found at once. Record every deviation and hesitation (section 3); an approval stop of the sandbox is neither (section 2). Fix every deviation in `template/PROTOCOL.md` or `template/AGENTS.md` and run the prompt again until it passes (section 6).

## 2. Setup

Both routes use the same folder and the same prompts.

- **Codex macOS app.** Open `<work>` as the project. Send each prompt in a new thread, except 2a and 2b, which share one: session-end uses the start time that session-start noted. Answer gates in the thread.
- **`codex` CLI.** Run `cd <work>`, then `codex` (interactive). A new thread is a new chat: `/new`. Do not use `codex exec`: it runs without human interaction, so a gate cannot be answered. This route has not been run yet.

**Permission setting.** Use Codex's `Auto` preset on both routes: the `workspace-write` sandbox with approvals on request (`--sandbox workspace-write --ask-for-approval on-request`). Codex recommends it for a version-controlled folder, and `<work>` is one. It may start in `read-only` until you trust the folder; the CLI's `/permissions` switches the mode.

In `Auto`, `.git` is read-only inside the sandbox. So `ra commit`, `ra sync pull`, `ra sync push` and `git config --local`, which write under `.git`, need your approval. Approve them: these stops are not hesitation points. In the skill-folder check the first `sync pull` was blocked on `.git/FETCH_HEAD`, and Codex retried with write access. Source: https://learn.chatgpt.com/docs/agent-approvals-security.md ("Sandbox and approvals", "Protected paths in writable roots"), read 2026-10-27.

**Build the folder.** In the framework checkout, with three paths that do not exist yet, all outside the checkout:

```
uv run python examples/build_smoke_plume.py <seed>
git clone --bare <seed> <origin.git>
git clone <origin.git> <work>
```

`<origin.git>` is the project's remote. Without a remote, session-start step 2 skips every `ra sync pull` and `ra sync push`, and sync goes untested. Work only in `<work>`; leave `<seed>` as built, so that it can seed further clones.

**Python.** In a terminal in `<work>`, run `python --version` (3.10 or newer is needed) and `python -c "import yaml"`. If `python` is missing or older, install Python 3.10 or newer (python.org, Homebrew or conda) so that `python` in a new terminal is that version. If the import fails, run `python -m pip install -r protocol/requirements.txt`.

The trap on macOS: `/usr/bin/python3` is Python 3.9 (3.9.6 on the test machine), and the helper dies on it with `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`. §2 lets Codex fall back to `python3` when that is 3.10 or newer. Record the interpreter Codex ran; the app's shell can differ from your terminal.

**Identity.** `<work>` has no local git identity, so git uses your global one, which matches no Members row of PROJECT.md (`Fan <fan@x>`, `Lee <lee@x>`). Leave it unset to test §2: Codex asks which member you are, sets the identity itself with `git config --local` (an approval stop) and tells you what it set. Or set it first:

```
git -C <work> config --local user.name "Fan"
git -C <work> config --local user.email "fan@x"
```

For prompt 3, switch to `Lee` and `lee@x` the same way, or tell Codex `I am Lee now; set the repository git identity to Lee's row`. One clone is enough. A second clone of `<origin.git>` also shows `ra sync pull` bringing in the other person's commits.

**PDF.** Any open-access PDF; it may lie outside `<work>` (§6 add-literature, Preconditions). The run in section 4 used arXiv 1505.04597v1 (U-Net): `curl -L -o <pdf> https://arxiv.org/pdf/1505.04597v1`. The download is byte-identical to the file the run committed (SHA-256 starts `a3172b2124f3`). Use the same PDF for prompts 1 and 3.

**Clean conditions.** The test needs none of the project's twelve skills and no user-level instructions. Before a no-skills run, none of the twelve skill folders may exist in `~/.codex/skills`, `<work>/.agents/skills`, `~/.agents/skills` or `/etc/codex/skills`, and `~/.codex/AGENTS.md` may not exist. The skills bundled with Codex (`~/.codex/skills/.system/`) and the user's own unrelated skills may stay.

Checked on the test machine on 2026-10-27: `~/.codex/AGENTS.md`, `~/.agents` and `/etc/codex` do not exist, and the clone has no `.agents`. The twelve folders in `~/.codex/skills` date from 11:28, after run 3's commit at 11:14, so runs 1 to 3 had none of them. They are installed there now for the check in section 5; remove them before any no-skills re-run.

**Synthetic dates.** The example's history is scripted and ends on 2026-10-28. Fan's last example log is `log/2026-10-28-fan-codex-1000.md`. Before 2026-10-28 on the real clock, a new Fan entry sorts before it, so session-start's "own latest log" (§6 session-start step 5: latest date, then latest HHMM) stays the example's entry, not the one the previous session wrote. Lee's last example log is `log/2026-10-27-lee-codex-0910.md`; a Lee entry written later on 2026-10-27 sorts after it. This comes from the example, not from Codex.

## 3. The three prompts

The prompts come from the plan, `docs/superpowers/plans/2026-10-25-sub-project-a-shared-repo-protocol.md`. Send each text as written, with `<pdf>` replaced by the PDF's absolute path. Do not mention PROTOCOL.md or `ra`.

**Record for every prompt** (the columns of section 4):

| Column | Where to find it |
|---|---|
| PROTOCOL.md read unprompted | The transcript: Codex opens `PROTOCOL.md` before its first other command (`AGENTS.md` itself is loaded automatically). In a thread that continues, whether it re-read the runbook before running it. |
| `ra` commands, in order | The transcript's command list: every `python protocol/ra.py <command>`, in order, grouped by verb with session-start first. |
| PDF read before claims | Every page read before the first write to `literature/`, and how. `n/a` when no PDF is involved. |
| `ra check` | Run `python protocol/ra.py check` in `<work>` afterwards. |
| Commit subjects | `git log --format='%h %an: %s' -5`; the trailers with `git show -s --format=%B <sha>`. |
| Hesitation points | Each place Codex stopped to ask or went back to the text. An approval stop of the sandbox is not one. |
| Deviations | Each step that differs from the runbook: a wrong or missing command, an extra write, a wrong subject, an edit outside the files the runbook names. |
| Interpreter, Codex version, model, permission setting | Once per thread, in the second table of section 4: the `python` Codex ran (its `python --version`); the app's About box or `codex --version`; the thread's model; the thread's sandbox and approval setting (CLI: `/permissions`). |

### Prompt 1: add a paper (plan Task 9 step 5)

New thread, identity `Fan`.

```
Add this paper to the project: <pdf>
```

Expected (§2, §5, §6, §7):

1. Opens `PROTOCOL.md`. Finds its Members row from `git config user.name` and `user.email`; when none matches, asks which member you are, sets the identity itself and tells you (§2).
2. Runs session-start before the add (§6 session-start; the steps are under prompt 2).
3. add-literature: `sync pull`; reads the PDF's first page; `dedup --doi … --arxiv … --title …`. On `none`, reads every page, then judges the relevance against the open questions.
4. `new literature …` (it copies the PDF); replaces every guidance line; `check`; `commit --type literature --subject "added <citekey> — <title fragment>"`; `sync push`.
5. Metadata only from the PDF (§7.3 Preprints); one `readers` entry with `read: full-text`; every claim has its seven sub-bullets and a `where`; zero claims only for `background` or `not-useful`.
6. A claim that bears on no open question goes through the QUESTION gate before it is written; a claim to keep as a fact goes through the KNOWLEDGE gate after the push (§8). Codex waits for `Commit`.

Result: one record, one PDF, one `[literature]` commit. Record the columns above.

### Prompt 2: start and end a session (plan Task 10 step 4)

One new thread, identity `Fan`, two prompts in turn:

```
start my session
```

```
end my session
```

Expected for `start my session` (§6 session-start): note the start time; `git remote`; `sync pull`; read PROJECT.md; `digest --person "<git author>"`, then the log entries it lists and your own latest; the open questions; `knowledge/README.md`; `check`; `stats`; report the digest, the check summary, the §14 health line and the unfinished work. It writes nothing.

Expected for `end my session` (§6 session-end, update-status): `sync pull`; `new log --person "<Person>" --agent codex --start <noted start>`; fill the five headings; `check`; `commit --type log --subject "session <Person>/codex <date> <HH:MM>–<HH:MM>"`; rewrite only `## Current status` of PROJECT.md (3–8 lines); `check`; `commit --type status --subject "current status after the <Person>/codex session of <date>"`; `sync conflicts` (`sync: no conflicts`); `sync push`. Two commits. Record the columns above for each of the two prompts.

### Prompt 3: re-read as the second member (plan Task 11 step 2)

Switch the identity to `Lee` (section 2), then send the text of prompt 1 with the same PDF in a new thread.

Expected (§6 session-start, add-literature step 4, reread-literature, §7.2):

1. Runs session-start first.
2. add-literature: `sync pull`, the PDF's first page, `dedup`. It prints `literature/<citekey>.md`: Codex creates no second record and runs reread-literature on it.
3. It reads the whole PDF before it edits the record.
4. For each existing claim it adds itself to exactly one of `verified-by` and `disputed-by`; it appends the claims the record misses; it edits the summary only together with a `revised:` line.
5. It adds itself to `readers` in block form; `check`; `commit --type literature --subject "re-read <citekey> — verified <N>, disputed <N>, added <N> claims"`; `sync push`.

Result: still one record; `readers` gains Lee; two `[literature]` commits in all (`added …`, `re-read …`). Record the columns above.

## 4. Results

Run on 2026-10-27 in the Codex macOS app with no skills, in one clone with a local bare origin: identity Fan for prompts 1, 2a and 2b, Lee for prompt 3. PDF: arXiv 1505.04597v1. The user ran the prompts; the pushed repository was checked afterwards: `check: no findings`, and `stats` shows papers 4 (the example has 3) and every other count as in the example.

| Prompt | PROTOCOL.md read unprompted | `ra` commands, in order | PDF read before claims | `ra check` | Commit subjects | Hesitations | Deviations |
|---|---|---|---|---|---|---|---|
| 1 add a paper (Fan) | Yes: `AGENTS.md` → `PROTOCOL.md`; it cited §2 | `sync pull`, `dedup` (`none`), `new literature` (inferred), `check`, `commit` (inferred), `sync push` (inferred); session-start only partly evidenced (notes below) | Yes: all 8 pages, before the record | no findings | `[literature] added ronneberger2015-u-net — U-Net: Convolutional Networks for Biomedical Image Segmentation` (`da57344`) | 1 (section 6) | none found |
| 2a start my session (Fan) | Yes | session-start: `sync pull`, `digest --person 'Fan <fan@x>'`, `check` | n/a | no findings | none (writes nothing) | none | none |
| 2b end my session (Fan) | Yes (re-read it in the same thread) | `sync pull`, `new log --help`, `new log --person Fan --agent codex --start 2026-10-27T11:03`, `check`, `commit --type log`, `check`, `commit --type status`, `sync conflicts` (`sync: no conflicts`), `sync push` | n/a | no findings | `[log] session Fan/codex 2026-10-27 11:03–11:06` (`da5cce8`); `[status] current status after the Fan/codex session of 2026-10-27` (`1b36a8c`) | none | none |
| 3 re-read as the second member (Lee) | Yes | session-start: `sync pull`, `digest --person 'Lee <lee@x>'`, `check`; add-literature: `sync pull`, `dedup --arxiv 1505.04597 --title '…'` (printed `literature/ronneberger2015-u-net.md`); reread-literature: `sync pull`, `check`, `commit --type literature`, `sync push` | Yes: the whole stored PDF, before it edited the record | no findings | `[literature] re-read ronneberger2015-u-net — verified 0, disputed 0, added 0 claims` (`0a75c42`, author `Lee <lee@x>`) | none | none |

| Run | Interpreter | Codex version | Model | Permission setting |
|---|---|---|---|---|
| Prompts 1, 2a, 2b, 3 | not recorded (Codex ran `python --version` in 2a) | not recorded | not recorded (the app's configuration showed `gpt-6.1-sol` on 2026-10-27) | not recorded |
| Skill check (section 5) | not recorded (Codex ran `python --version`) | not recorded | not recorded | not recorded; the sandbox blocked the first `sync pull` |

Notes on prompt 1:

- **session-start** is only partly evidenced: `sync pull` is confirmed; the digest and the open-question reading are not shown by the evidence. The user can expand the prompt-1 command list from the thread to settle it.
- **Inferred commands.** The user confirmed `sync pull`, `dedup` and `check`. `new literature`, `commit` and `sync push` are inferred: the record's frontmatter equals what `ra new literature` writes for these arguments, except `code:` and `data:`, which §6 add-literature step 9 has the AI fill; the commit has the `ra commit` message format (`Person: Fan`, `Agent: codex`, `Links:` the record and its PDF); and it is on origin.
- **The record:** asked the identity question first (section 6); `relevance: background` with zero claims (§7.3 allows it), `venue: arXiv preprint`, arXiv id without version, empty `doi`, code and data URLs the paper prints, a dated Notes line, BibTeX.

Other commands and reads:

- **2a.** `git config user.name` and `user.email`, `git remote`, `date`, `python --version`, `git status`; the open questions read with an inline Python script. Report: start time, no new commits, check clean, the §14 health line (4 papers; 2 with claims awaiting a second reader; 1 disputed claim; 2 facts in CONFLICT), the open questions, the Unfinished items of Fan's latest log.
- **2b.** `date`, `git status --short --branch`, `git diff --check`, `git log -2`, `git status`; a script showed that only `## Current status` of PROJECT.md changed (6 lines). The entry `log/2026-10-27-fan-codex-1103.md` has the five headings filled, with four concrete Unfinished items.
- **3, identity.** The user said `I am Lee now; set the repository git identity to Lee's row`. Codex read §2 and the Members table and ran `git config --local user.name Lee` and `git config --local user.email lee@x` itself.
- **3, session-start.** `digest` listed Fan's two papers, the closed question, the loss decision, two logs and the status updates. Codex read three log entries (Lee's own latest among them), `knowledge/README.md`, `goes-abi.md`, `glossary.md` and the open questions, and computed the §14 health line with its own script (same numbers as 2a).
- **3, add and re-read.** `pdftotext -f 1 -l 1` for the metadata, `dedup`; then `pdftotext -layout` on the stored PDF, a byte comparison of the stored and the supplied PDF, and pages 2–7 rendered to PNG under `.ra/paper-ingest-unet/` and viewed. It added Lee to `readers` and one Notes line, left Summary, Why it matters, Claims and BibTeX as they were (no `revised:` line, because it did not edit the summary, §7.4 rule 7), and checked its own diff with a script.

**Verdict, 2026-10-27:** PASS for prompts 1, 2a, 2b and 3 as run, with no claim written and no gate fired. One hesitation: prompt 1's request that the user run `git config --local` (section 6). Prompt 1's session-start is only partly evidenced. The paths under "Not exercised" in section 6 are outside this verdict.

## 5. Skill folders

Question (spec §13, §18): does the team's Codex version load skill folders? **Yes: they load and are used (2026-10-27, Codex macOS app).**

This version keeps skills at `~/.codex/skills/<name>/SKILL.md`, with the same `name` and `description` frontmatter as `plugin/skills/<name>/SKILL.md`; the bundled system skills sit under `~/.codex/skills/.system/`.

Codex's documentation (read 2026-10-27 at https://developers.openai.com/codex/skills; append `.md` for plain text) names other places, which the check did not test: `.agents/skills` in each directory from the working directory up to the repository root, `$HOME/.agents/skills` and `/etc/codex/skills`. It also says Codex follows symlinks, picks up changes (restart if a skill does not appear), lists skills with `/skills` in the CLI, and shows them under Skills in the desktop app's sidebar.

To repeat the check, on this or another version:

1. Record the version: the app's About box, or `codex --version`.
2. Install the skills and restart the app: `cp -R <framework-checkout>/plugin/skills/. ~/.codex/skills/`. A `.agents/skills` folder in a clone also works according to the documentation; then add `.agents/` to `<clone>/.git/info/exclude`, so that `git status` stays clean.
3. In a new thread ask **Loads:** `List the skills you have available, by name`. Do the twelve names (`project-init`, `session-start`, `session-end`, `add-literature`, `reread-literature`, `propose-question`, `close-question`, `propose-knowledge`, `propose-decision`, `accept-decision`, `supersede-decision`, `update-status`) appear? Then **Uses:** `Use the session-start skill`. Does Codex say it is using it, open its `SKILL.md` and run the runbook? A version that lists no skills answers no.
4. If it loads, run prompts 1, 2 and 3 with the skills in a fresh clone: a new `<origin.git>` cloned from the same `<seed>`, then a new `<work-skills>` cloned from it, so it starts where `<work>` did. Use the same PDF and identities, add a row marked "with skills" to the table in section 4 for each, and write the difference here: commands, subjects and hesitations that change, and any rule a skill states that the transcript shows Codex did not need or got wrong. A skill holds no rule of its own (`plugin/README.md`), so a difference points to a PROTOCOL.md passage that the skill makes clearer.

Result, 2026-10-27 11:30, Codex macOS app, after `cp -R plugin/skills/. ~/.codex/skills/` and an app restart:

- **Loads: yes.** `List the skills you have available, by name` returned all twelve protocol skills, with the user's own skills and the system skills.
- **Uses: yes.** `Use the session-start skill`: Codex announced "I'm using the session-start skill", read it, and ran the runbook in order for Lee.
  - Commands: `git config user.name`, `git remote`, `git config user.email`, `date`, `python --version`, `python protocol/ra.py sync pull` (the first attempt was blocked by the sandbox writing `.git/FETCH_HEAD`; retried with write access), read PROJECT.md, `digest --person "Lee <lee@x>"` (`No new commits.`), listed `log/` and read Lee's latest log, searched `^status:` in `questions/` and read the two open ones, read `knowledge/README.md`, `check` (no findings).
  - Report: the §14 health line (4 papers; 2 with claims awaiting a second reader; 1 disputed claim; 2 facts in CONFLICT) and the unfinished items.
- **Not recorded:** version, model, permission setting (the app's configuration shows model `gpt-6.1-sol`). Codex also had other skills installed (superpowers and others) and consulted them in passing.
- **Difference with skills:** not known yet. Only session-start ran with skills; step 4 is open.

Verdict: skill folders load and are used in this version, so spec §18's assumption holds for it. The runnable-alone result of section 4 stands either way.

## 6. Deviations and fixes

No deviation was found in prompts 1, 2a, 2b or 3, so no fix was needed for them. `template/AGENTS.md` is unchanged. `template/PROTOCOL.md` changed once after the runs, in §2, by ruling R59 (below).

**Hesitation 1 (prompt 1): the identity.** No Members row matched the git identity. §2 as the runs read it said "ask the user which member they are and to set their git identity to that row's Git author name", and Codex did that: it asked which member the user is, then asked the user to run `git config --local user.name "Fan"` and `git config --local user.email "fan@x"`. So the request followed §2.

In prompt 3 the user told Codex `I am Lee now; set the repository git identity to Lee's row`, and Codex read §2 and the Members table and ran the two commands itself, in the same clone. Whether the sandbox would have allowed that without the instruction is unknown: the permission setting was not recorded, and `.git` is read-only in `Auto` (section 2).

**Change made after the run (ruling R59).** §2 "Who you are" now says: once the user names their row, the AI sets the repository-local git identity itself, with the two `git config --local` commands shown in a fenced block, and tells the user what it set. Reason: teammates without a CS background must not be asked to run git commands. Runs 1 to 3 used the earlier wording, so they do not test the new sentence; the first checklist item below does. `tests/test_docs.py` and `tests/test_skills.py` stay green; the session-start skill points to §2, so no skill changed.

**Observations, not deviations.**

- Codex read the open questions (2a) and computed the §14 health line (3) with inline scripts. `ra stats` reports `papers` and `unverified_claims`; the §14 health line needs the number of papers with an unverified claim, which `stats` did not print. Codex's numbers were right. Since these runs, `stats` prints that number as `papers_with_unverified_claims`, and session-start runs `ra stats` (§6 session-start step 9).
- It read the PDFs with `pdftotext` or as page images under `.ra/` (git-ignored, §3). All of these are reads, or writes to `.ra/`.

**Not exercised.**

- No gate fired. The prompt-1 record is `background` with zero claims, so no claim bore on an open question and none became a fact: the QUESTION and KNOWLEDGE gates did not appear, and `Edit` and `Skip` were not answered.
- reread-literature step 4, adding `verified-by` or `disputed-by` to an existing claim, did not run, because the record has no claims; prompt 3 gave `verified 0, disputed 0, added 0`. The example's own records cannot cover it: their PDFs are one-line placeholders.
- Six verbs have no Codex evidence: propose-question, close-question, propose-knowledge, propose-decision, accept-decision and supersede-decision. Spec §13 asks for every verb; the plan's three prompts reach session-start, session-end with update-status, add-literature and reread-literature.
- Merge conflicts (§9), the CLI route, and the new §2 identity sentence.

To cover the first two, run prompt 1 with a second open-access PDF that bears on an open question (`Q-2026-10-25-plume-baselines` asks for the strongest published baselines for plume segmentation on GOES-16), answer its gates, then run prompt 3 on it as the second member. If Codex records no claim, pick a paper that answers an open question directly.

**Still open** (none of it changes the verdict above):

- [ ] Run prompt 1 in a fresh clone with the identity unset, to test the new §2 sentence: Codex should ask which member you are, set the identity itself and tell you. Add a row to the table in section 4.
- [ ] Section 5, step 4: run prompts 1, 2 and 3 with the skills installed, add the rows marked "with skills" and write the difference in section 5. Remove the skills afterwards if a no-skills re-run follows.
- [ ] Cover the items under "Not exercised" that matter to the pilot, at least one run with a gate and one with `verified-by` or `disputed-by`, and add their rows.
- [ ] Fill the second table of section 4 for every run from now on.
