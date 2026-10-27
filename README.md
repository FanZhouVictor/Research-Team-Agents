# Research-Team-Agents

RA_Agent lets a research team of up to five people work on one project, each person with their own AI assistant: Claude Code or Codex. Each project is one private git repository on GitHub, a project folder whose whole history git records, and it holds the project's papers, open questions, agreed facts, decisions and session logs. Any member's AI can read that repository, check a finding against the paper's PDF, and continue work that another member's AI left unfinished, without anyone copying text between AIs. A new member's AI can tell from the repository alone what the team is trying to find out, what it knows, what is decided and what is in progress. The rules every AI follows are in `PROTOCOL.md`, a file inside each project, and that file is the authority. The skills in this repository are conveniences that run the same steps; an AI without them follows `PROTOCOL.md` alone.

## What you need

- **Claude Code or Codex**, either one:
  - Claude Code comes with the Claude desktop app (its Code tab), which needs a paid Claude plan. Download links: https://code.claude.com/docs/en/overview.
  - Codex: the Codex app, from https://learn.chatgpt.com/docs/app.
- **Python 3.10 or newer**, from https://www.python.org/downloads/. On macOS, the built-in `python3` is often 3.9, which is too old. On Windows, tick "Add python.exe to PATH" in the installer.
- **git**, from https://git-scm.com/downloads.
- **A GitHub account** with access to this repository and to your team's project repository, and git on your computer signed in to it: https://docs.github.com/en/get-started/git-basics/caching-your-github-credentials-in-git.

## Get started in one sentence

Open any folder in Claude Code or Codex, paste this sentence, and answer the questions it asks:

```
Set me up for the RA_Agent protocol: clone https://github.com/FanZhouVictor/Research-Team-Agents and follow its INSTALL.md.
```

Your app asks before it runs some commands, such as the clone and the skill install: allow them.

What the AI will do, following [INSTALL.md](INSTALL.md):

1. Note which app it runs in and which operating system you use.
2. Check that git is installed, then clone this repository into the folder you opened (a clone is a copy that stays linked to the one on GitHub), or update an earlier clone.
3. Check for Python 3.10 or newer, and install PyYAML, a small Python add-on the helper needs, if it is missing.
4. Copy the twelve skills into your app's skill folder, the folder it loads skills from, with `scripts/install_skills.py`. If you use Codex, you quit and reopen the app afterwards.
5. Ask whether you join your team's project or create a new one, then clone or create it next to this repository.
6. Bring the project up to date from GitHub, or connect a new project to an empty private GitHub repository (a new, empty project space on github.com that only invited people can see); then set your name and email for your work in it, and check its files.
7. Tell you to open the project folder and say `start my session`.

If something is missing, such as Python, the AI stops and tells you what to install. Afterwards, paste the sentence again.

## Manual route, for people who prefer a terminal

Use `python3` wherever `python` is missing or older than 3.10.

```
git clone https://github.com/FanZhouVictor/Research-Team-Agents
cd Research-Team-Agents
python scripts/install_skills.py
```

The script copies the skills to `~/.claude/skills/` and `~/.codex/skills/`, for each of the two apps it finds; `--dry-run` shows what it would do. Then create a project. `<project>` is a folder outside the framework folder, for example `../my-project`:

```
python template/protocol/ra.py init <project> --name "<project name>" --person "<Person>" --git-author "<git author>" --platforms <platforms> --role "<role>"
```

`<git author>` is your name and email as `Name <email>`, and `<platforms>` is `claude-code`, `codex` or both. Or clone your team's project, again outside the framework folder; if its PROJECT.md Members has no row for you yet, a member adds you first (Daily use). Then set your name and email in the project to those of your row; `ra init` does this for a project you create:

```
git clone <project URL> <project>
git -C <project> config --local user.name "<Name>"
git -C <project> config --local user.email "<email>"
```

If a command reports that the module `yaml` is missing, run `python -m pip install -r template/protocol/requirements.txt`. Then open the project folder in Claude Code or Codex and say `start my session`.

## Daily use

Open the project folder in your app. Three sentences do most of the work:

- `start my session`: the AI pulls your teammates' work, tells you what is new and what was left unfinished, and checks the files.
- `Add this paper to the project: <path to the PDF>`: the AI reads the whole paper, records it with the claims that matter to the project, and shares the record. If the paper is recorded already, it re-reads it and checks the existing claims against it instead.
- `end my session`: the AI writes the session log, updates the project status and shares both.

When the AI proposes a question, a fact or a decision for the shared repository, it shows the proposal and asks `Commit / Edit / Skip?`:

- `Commit`: save it, with you as the approver.
- `Edit`: change it first; the AI then asks again.
- `Skip`: save nothing.

A decision counts as accepted only when a person says so, for example `I accept D-2026-10-26-eval-metric.`

A teammate can join once a member has added them to PROJECT.md Members. The member says, in a session, for example `Add Ana to the project as a member: Ana Silva <ana@uni.edu>, Codex, PhD student.` The AI shows the new row and asks `Commit / Edit / Skip?`; it never adds a member on its own.

## The example project

`examples/build_smoke_plume.py` builds a small project, Smoke Plume, whose git history shows the protocol at work: two members, Fan, who works in Claude Code and Codex, and Lee, who works in Codex; three papers; questions; facts with a conflict; and accepted and superseded decisions. `<dir>` is a folder that does not exist yet:

```
uv run python examples/build_smoke_plume.py <dir>
```

Without uv, `python examples/build_smoke_plume.py <dir>` works too, given Python 3.10 or newer with PyYAML. The example is synthetic: its papers, their authors and their DOIs (prefix 10.5555) are invented, its PDFs are one-line placeholders, and its history is dated 2026-10-25 to 2026-10-28. The tests use it, and you can use it to try the protocol; to try adding a paper, give it a real PDF.

## For developers

```
uv sync
uv run pytest
```

| Folder | Holds |
|---|---|
| `template/` | what `ra init` copies into every project: PROTOCOL.md, CLAUDE.md, AGENTS.md, PROJECT.md, file templates, and the helper `protocol/ra.py` with the commands `init`, `new`, `check`, `dedup`, `commit`, `digest`, `sync` and `stats` |
| `plugin/` | the twelve skills, one per verb of PROTOCOL.md §6 plus `project-init`, and the Claude Code plugin manifest |
| `examples/` | the builder of the example project |
| `scripts/` | `install_skills.py`, which installs the skills for Claude Code and Codex |
| `docs/` | the design spec, the implementation plan, the Codex verification and the pilot checklist |
| `tests/` | the pytest suite |

## Documents

- [INSTALL.md](INSTALL.md): the setup runbook an AI follows.
- [docs/superpowers/specs/2026-10-25-ra-agent-framework-stage0-design.md](docs/superpowers/specs/2026-10-25-ra-agent-framework-stage0-design.md): the design spec.
- [docs/superpowers/plans/2026-10-25-sub-project-a-shared-repo-protocol.md](docs/superpowers/plans/2026-10-25-sub-project-a-shared-repo-protocol.md): the implementation plan.
- [docs/codex-verification.md](docs/codex-verification.md): Codex runs the protocol from PROTOCOL.md alone, and loads the skills.
- [docs/pilot-checklist.md](docs/pilot-checklist.md): what the pilot measures, and the checks left before the `v0.1.0` tag.
- [plugin/README.md](plugin/README.md): the skills, and how they are installed.
- [template/PROTOCOL.md](template/PROTOCOL.md): the protocol that every project carries.

## Status

0.1.0, pilot candidate; see [docs/pilot-checklist.md](docs/pilot-checklist.md) for what remains before tagging. So far it has run only on macOS; Linux and Windows are untested.
