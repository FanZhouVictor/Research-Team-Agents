# Pilot checklist — sub-project A

What the pilot measures (spec §16), how to measure it, and the live checks left before the `v0.1.0` tag. Fill in each empty "Result / date" cell when you run its row. "Spec §N" is a section of `docs/superpowers/specs/2026-10-25-ra-agent-framework-stage0-design.md`; "§N" alone is a section of PROTOCOL.md.

Run every `python protocol/ra.py` command from the root of a project clone, the folder that holds PROJECT.md, after a pull. Use `python3` where `python` is missing or older than 3.10.

```
python protocol/ra.py sync pull
```

## 1. Success criteria (spec §16)

The pilot runs on one active project for 3–4 weeks. `ra stats` prints eight counts (`template/protocol/ra/stats.py`):

```
python protocol/ra.py stats
```

- `papers`: records in `literature/`.
- `claims`: claims of all records.
- `unverified_claims`: claims with no `verified-by` entry from a person other than the claim's author; a dispute is no verification.
- `disputed_claims`: claims with a `disputed-by` entry.
- `duplicate_records`: `DUP_LITERATURE` findings of `check`.
- `decisions_edited`: `DECISION_EDITED` findings of `check`.
- `open_questions`: questions with `status: open`.
- `conflict_facts`: fact lines in `knowledge/` whose status is CONFLICT; a pair counts 2.

The §14 health line's "papers with an unverified claim" is not a stats key yet; session-start computes it.

| # | Criterion | Measurement | Target | Result / date |
|---|---|---|---|---|
| 1.1 | Papers ingested by at least two different people | `git shortlog -sn --grep="^\[literature\] added" HEAD`: the authors of the `[literature] added` commits | 2 or more names | |
| 1.2 | Every claim has a `where` | `python protocol/ra.py check` | no `CLAIM_NO_WHERE` line | |
| 1.3 | No paper exists as two records | `stats`: `duplicate_records` | 0 | |
| 1.4 | A majority of claims verified by a second reader, by pilot end | `stats`: `claims` and `unverified_claims` | `unverified_claims` below half of `claims` | |
| 2 | Continuity: a scripted handoff in each direction, with no human relaying context | live check (d) | both directions PASS | |
| 3 | Onboarding: a fresh session answers the four questions from one `start my session` | live check (e), on the pilot project in week 3 or 4 | 4 of 4 correct | |
| 4.1 | Every accepted decision links to its evidence | `git grep -n -A8 -e "^links:" -- decisions/`: the `- ` lines under `links:`, up to `---`, of each file with `status: accepted` | at least one question ID or path each, and each named file exists | |
| 4.2 | Git history shows no decision edited in place | `stats`: `decisions_edited`; `check`; `git log --format="%h %ad %an %s" --date=short -- decisions/` | 0; no `DECISION_EDITED` line; after the `[protocol]` init commit, only `[decision] proposed`, `accepted` and `superseded … by …` commits | |

Global checks:

| Check | Measurement | Target | Result / date |
|---|---|---|---|
| Zero copy-paste between AIs | At the end of each week, ask every member: "Did you paste text from one AI into another this week?" | 0 yes answers | |
| No git conflict in `knowledge/` or `decisions/` left unresolved longer than a week | `git grep -n -i "merge conflict" -- log/` lists the log entries that report one (§9 step 3); the member whose clone it is records the day the merge was committed | each resolved within 7 days | |

The counts, once a week:

| Week ending | papers | claims | unverified_claims | disputed_claims | duplicate_records | decisions_edited | open_questions | conflict_facts |
|---|---|---|---|---|---|---|---|---|
| | | | | | | | | |
| | | | | | | | | |
| | | | | | | | | |
| | | | | | | | | |

## 2. Already passed

| Check | Evidence | Result / date |
|---|---|---|
| Codex runs the protocol from PROTOCOL.md alone (runnable-alone test, spec §13): prompts 1, 2a, 2b and 3 in the Codex macOS app, no skills | [docs/codex-verification.md](codex-verification.md), section 4 | PASS, 2026-10-27 |
| Codex loads the skill folders from `~/.codex/skills/` and uses them | [docs/codex-verification.md](codex-verification.md), section 5 | PASS, 2026-10-27 |
| Two clones hand work over at file level, with `ra` commands and no AI | `tests/test_handoff.py`, in `uv run pytest` (all tests pass) | PASS, 2026-10-27 |
| The example project builds and checks clean | `uv run python examples/build_smoke_plume.py <dir>`, then `python protocol/ra.py check` in `<dir>` | `check: no findings`, 2026-10-27 |

Still open from docs/codex-verification.md section 6: the with-skills repeat of prompts 1–3, a run of the §2 identity sentence, and runs with a gate and with `verified-by` or `disputed-by`. Below, (a) fires a gate, (d) writes `verified-by` or `disputed-by`, and the clones of the setup start with no identity, which tests the §2 sentence.

## 3. Live checks before tagging

**Setup.** In the framework checkout, with four paths outside it that do not exist yet:

```
uv run python examples/build_smoke_plume.py <seed>
git clone --bare <seed> <origin.git>
git clone <origin.git> <fan-clone>
git clone <origin.git> <lee-clone>
```

- Leave the clones' git identity unset: at the first session the AI asks which member you are, Fan or Lee, and sets it itself (§2).
- Install the skills first: `python scripts/install_skills.py`. Quit and reopen the Codex app afterwards.
- Choose two real open-access PDFs, `<pdf-1>` and `<pdf-2>`, that bear on `Q-2026-10-25-plume-baselines` or `Q-2026-10-25-abi-band-choice` (smoke-plume segmentation, GOES-16 ABI bands), so that their records get claims. The example's own PDFs are placeholders with no paper text.
- The example's history ends on 2026-10-28. Until that day, a new Fan log entry sorts before the example's last one (docs/codex-verification.md section 2, "Synthetic dates").

Each check gives what you type, word for word, and what must happen.

### (a) Knowledge gate

Run it in a new project: the example's `knowledge/goes-abi.md` already holds this fact, and its placeholder PDFs cannot confirm it. `<abi-pdf>` is a real PDF that gives ABI band 7 as 3.9 µm with 2 km resolution, and `<gate-project>` a folder outside the framework checkout that does not exist yet. In the framework checkout:

```
python template/protocol/ra.py init <gate-project> --name "Gate Test" --person "<you>" --git-author "<git author>" --platforms claude-code codex --role "PI"
```

Open `<gate-project>` in your app and type `start my session`, then `Add this paper to the project: <abi-pdf>` (answer its gates as you like), then:

```
I learned from the PDF that ABI band 7 is 3.9 µm, 2 km.
```

| Step | Expected | Result / date |
|---|---|---|
| The sentence | The AI opens the PDF where the fact is (§7.1) and prints the KNOWLEDGE prompt of §6 propose-knowledge for a new topic, line for line: `Proposed for the shared repo — KNOWLEDGE`, `Topic file: knowledge/<topic>.md (new)`, `Registry: - <topic> — <scope>`, `Fact:`, `Source: <citekey> <where>`, `Commit / Edit / Skip?`. It writes nothing before the answer. | |
| Answer `Skip` | `git -C <gate-project> status --short` prints nothing, and `git -C <gate-project> log -1 --format=%s` is unchanged | |
| The sentence again; answer `Commit` | `knowledge/<topic>.md` ends with `- <fact> (src: <citekey> <where> · <you>/<agent> <date> · approved <you> · ok)`; `knowledge/README.md` holds `- <topic> — <scope>`; one new commit `[knowledge] <topic>: <fact fragment>`; `check` prints `check: no findings` | |

### (b) Decision flow

In `<fan-clone>`, as Fan, after `start my session`:

| Type | Expected | Result / date |
|---|---|---|
| `Propose a decision: keep the downloaded GOES-16 scans on the lab's network drive, not on laptops. Evidence: Q-2026-10-26-dataset-size.` | The DECISION prompt of §8 with `(status will be: proposed)`. On `Commit`: `decisions/D-<date>-<slug>.md` with `status: proposed` and an empty `accepted-by:`; commit `[decision] proposed <D-id> — <title>`; `check` clean | |
| `I accept <D-id>.` | Only `status: accepted` and `accepted-by: Fan · <date>` change; commit `[decision] accepted <D-id>`; `check` clean | |
| `Supersede <D-id>: keep the scans in the university's cloud storage instead, because the network drive is full. Evidence: Q-2026-10-26-dataset-size.` | One line naming `<D-id>` as the decision replaced, then the DECISION prompt. On `Commit`: a new `<new-id>` with `supersedes: <D-id>`, and `<D-id>` unchanged; `check` clean | |
| `I accept <new-id>.` | Commit `[decision] accepted <new-id>`, then `[decision] superseded <D-id> by <new-id>`, which changes only `status: superseded` and `superseded-by: <new-id>` in `<D-id>`; `check` clean after each | |
| By hand, change one word under `## Rationale and evidence` in `decisions/<new-id>.md`, save it, and run `python protocol/ra.py check` | `DECISION_EDITED decisions/<new-id>.md: edited after acceptance: only status: and superseded-by: may change`, exit 1 | |
| Undo it with `git checkout -- decisions/<new-id>.md`, then run `check` | `check: no findings` | |

### (c) Claude Code with the skills

Open `<fan-clone>` in a new Claude Code session, as Fan. This run can be the first half of (d), direction 1.

| Type | Expected | Result / date |
|---|---|---|
| `start my session` | The transcript shows the session-start skill in use, and Claude Code runs §6 session-start: `git remote`, `sync pull`, `digest --person "Fan <fan@x>"`, `check`. It reports the digest, the check summary, the §14 health line and the unfinished work, and writes nothing. | |
| `Add this paper to the project: <pdf-1>` | add-literature: `sync pull`; `dedup` prints `none`; the whole PDF is read; `new literature`; `check`; commit `[literature] added <citekey> — <title fragment>`; `sync push`. Gates appear as §8 says. | |
| `end my session` | session-end: commits `[log] session Fan/claude-code <date> <HH:MM>–<HH:MM>` and `[status] current status after the Fan/claude-code session of <date>`; `sync conflicts` prints `sync: no conflicts`; `sync push` | |

### (d) Cross-platform handoff (spec §16.2)

Best with two people at two computers. One person may play both members, in the two clones, if they type only the sentences below. The second member types nothing about the first member's work.

- **Direction 1, Claude Code to Codex.** Fan, in Claude Code, in `<fan-clone>`: `start my session`; `Add this paper to the project: <pdf-1>`; `End my session. Leave the second reading of that paper to another member.` Then Lee, in Codex, in `<lee-clone>`: `start my session`; `Go ahead with the unfinished work you found.`; `end my session`.
- **Direction 2, Codex to Claude Code.** The same with `<pdf-2>`: Lee in Codex first, then Fan in Claude Code.

The item that counts is the second reading of the paper the first session added (`<pdf-1>`, then `<pdf-2>`). The example's older Unfinished items, the `jones2023-plume-unet` re-read and the band-7 conflict, do not count, though the report may list them too.

Expected in each direction: the second session's start report names the paper and its open second reading, taken from the first member's log. The second session runs reread-literature on that record, not a second add. Every original claim gains the second member in `verified-by` or `disputed-by`. The second member commits `[literature] re-read <citekey> — verified <N>, disputed <N>, added <N> claims` and lists it under `## Done` in their log. After `sync pull`, `check` prints `check: no findings` in both clones.

| Direction | First session, citekey | Its Unfinished item | Second session | Item found without being told | Second session's commits | `check`, both clones | PASS / FAIL | Date |
|---|---|---|---|---|---|---|---|---|
| 1: Claude Code → Codex | Fan/claude-code, | | Lee/codex | | | | | |
| 2: Codex → Claude Code | Lee/codex, | | Fan/claude-code | | | | | |

### (e) Fresh-session onboarding (spec §16.3)

Make a new clone, `git clone <origin.git> <new-clone>`, and open it in a new session with no earlier conversation, as Lee. Type `start my session`, then:

```
What are we trying to find out, what do we know, what's decided, and what's in progress?
```

Expected for the example as built, plus what (b) and (d) added:

| Question | A correct answer names | Result / date |
|---|---|---|
| Trying to find out | the open questions `Q-2026-10-25-plume-baselines` and `Q-2026-10-25-abi-band-choice`; `Q-2026-10-26-dataset-size` is answered | |
| Know | `knowledge/goes-abi.md`: band 7 is 3.9 µm, and its resolution is in CONFLICT (2 km against 1 km) until a human resolves it; the records and their relevance (core, supporting, not-useful); one disputed claim | |
| Decided | `D-2026-10-26-eval-metric` (mIoU) and `D-2026-10-28-loss-function-v2` (Dice plus cross-entropy), which supersedes `D-2026-10-25-loss-function` | |
| In progress | PROJECT.md "Current status" and the Unfinished items of the latest logs: the band-7 conflict, and `jones2023-plume-unet` without a second reader | |

PASS: all four correct, with nothing invented. Repeat it on the pilot project in week 3 or 4 (criterion 3), checking the answers against its PROJECT.md, `questions/`, `knowledge/` and `decisions/`.

### (f) Decision history (spec §16.4)

In `<fan-clone>`, after (b) and a pull, run the commands of criteria 4.1 and 4.2.

| Expected | Result / date |
|---|---|
| `decisions_edited: 0`; no `DECISION_EDITED` line from `check`; only `[decision] proposed`, `accepted` and `superseded … by …` commits in `git log -- decisions/` after the `[protocol]` init commit; every accepted decision lists its evidence under `links:` | |

### (g) Setup in one sentence (INSTALL.md)

On a computer or user account that has neither the framework nor the skills, once in Claude Code and once in Codex: open an empty folder and paste the sentence from README.md. Until this branch is merged into `main`, the sentence clones `main`, which has no INSTALL.md; test with this sentence instead:

```
Set me up for the RA_Agent protocol: clone https://github.com/FanZhouVictor/Research-Team-Agents, check out the branch feat/sub-project-a-shared-repo-protocol, and follow its INSTALL.md.
```

| App | Expected | Result / date |
|---|---|---|
| Claude Code, creating a project (answer `later` to the GitHub question) | The AI runs INSTALL.md steps 1–7 and never asks the person to type a command. It asks only the questions under "Ask the human", ends step 6 with `check: no findings`, and hands over with `start my session`. | |
| Codex, joining `<origin.git>` as Lee, from an account on the computer that holds it | The same, and step 4 asks the person to quit and reopen the app. | |

### (h) Adding a member (PROTOCOL.md §2)

In `<fan-clone>`, as Fan, in a session:

| Type | Expected | Result / date |
|---|---|---|
| `Add Ana to the project as a member: Ana Silva <ana@x>, Codex, PhD student.` | The MEMBER prompt of §2 Adding a member, with the row `\| Ana \| Ana Silva <ana@x> \| codex \| PhD student \|`; nothing written before the answer | |
| Answer `Skip` | `git status --short` prints nothing | |
| The sentence again; answer `Commit` | The row is the last line of PROJECT.md Members and nothing else in PROJECT.md changed; one commit `[protocol] add member Ana` with `Person: Fan`; `check` clean; pushed | |

## 4. Tag v0.1.0

When every row of sections 2 and 3 shows a pass, tag the framework repository on the commit that teammates will clone, `main` after the merge, and push the tag:

```
git tag v0.1.0 -m "sub-project A: pilot-ready"
git push origin v0.1.0
```

Section 1 is measured during the pilot, after the tag.
