# INSTALL.md — Setup runbook

This file is for an AI session, Claude Code or Codex. A person who wants to use the RA_Agent protocol opens any folder in their app and pastes this sentence:

```
Set me up for the RA_Agent protocol: clone https://github.com/FanZhouVictor/Research-Team-Agents and follow its INSTALL.md.
```

You, the AI, then run the steps below in order. The person may have no programming background, so:

- run every command yourself, and never ask the person to type one;
- after each step, say in one plain sentence what it did;
- ask only the questions under "Ask the human", one at a time, and wait for each answer.

**Preconditions:** the person pasted the sentence above; you are a Claude Code or Codex session; the computer runs macOS, Linux or Windows.

**Plain words.** Explain with these meanings:

- a git repository: a project folder whose whole history git records, so that every member's copy can be brought up to date;
- a clone: a copy of a git repository on this computer that stays linked to the copy on GitHub;
- PyYAML: a small add-on for Python that the project helper needs to read the project's files;
- a skill folder: the folder from which the app loads its skills, `~/.claude/skills` or `~/.codex/skills`;
- an empty private GitHub repository: a new, empty project space on github.com that only invited people can see.

**Placeholders.** Replace every `<…>` with its value and keep the rest literally. Quote every path, because a path may contain a space.

- `<parent>`: the absolute path of the folder the person opened in the app.
- `<framework>`: the absolute path of your clone of this repository, normally `<parent>/Research-Team-Agents`.
- `<project>`: the absolute path of the project folder, chosen in step 5.

**Commands.** Each command line is complete: none relies on a `cd` made by an earlier command, so it works whether or not your shell keeps its folder between commands. A line that starts with `cd "<project>" &&` runs as one line; in Windows PowerShell 5, write `;` in place of `&&`. `python` means the interpreter that passed step 3, which may be `python3`.

**Permissions.** The app asks the person before some commands run, such as a clone (it uses the network) and the skill install (it writes in their home folder): tell the person to allow them. If a command fails with a permission or network error, run it again with your tool's request for more access, and tell the person to allow it. In Codex's Auto mode, every command that writes inside a `.git` folder, such as a clone, a pull, a push or `git config`, needs that approval.

## Steps

1. **Your tool and the operating system.** Note whether you are Claude Code or Codex; steps 4 and 7 need it. Note the operating system from your environment information; if it does not say, run the command below: `Darwin` is macOS, `Linux` is Linux, and anything else or an error is Windows.
   ```
   uname -s
   ```
2. **The framework.** Check that git is installed; it prints a version:
   ```
   git --version
   ```
   On macOS, a window may offer to install the "command line developer tools", which include git: tell the person to click Install, wait until it finishes, then run the check again. Then make sure `<framework>` holds the current version:
   - If you cloned this repository in this session to read this file, it does: go on.
   - If the clone was there already, from an earlier setup, update it; if the pull lists `INSTALL.md` among the changed files, read this file again from the start:
     ```
     git -C "<framework>" pull
     ```
   - Otherwise clone it:
     ```
     git clone https://github.com/FanZhouVictor/Research-Team-Agents "<parent>/Research-Team-Agents"
     ```
   If git cannot reach the repository, see "Sign-in" under Stop conditions.
3. **Python.** The project helper, `protocol/ra.py`, needs Python 3.10 or newer and PyYAML. Check the version:
   ```
   python --version
   ```
   If `python` is missing or older than 3.10, check `python3`; if that shows 3.10 or newer, write `python3` wherever this file writes `python`. On macOS the built-in `python3` is often 3.9, which is too old.
   ```
   python3 --version
   ```
   Check PyYAML; no output means it is installed:
   ```
   python -c "import yaml"
   ```
   If it reports `No module named 'yaml'`, install it, then run the check again:
   ```
   python -m pip install -r "<framework>/template/protocol/requirements.txt"
   ```
   If pip refuses with `externally-managed-environment`, this Python is managed by the system: install PyYAML for this person only, in their own folder, then run the check again:
   ```
   python -m pip install --user --break-system-packages pyyaml
   ```
4. **The skills.** Copy the twelve skills of `plugin/skills/` into the skill folder of each AI tool on this computer:
   ```
   python "<framework>/scripts/install_skills.py"
   ```
   It prints one `copied <skill> -> <folder>` line per skill and tool, then a `done:` line and a `next:` line, and exits 0. A line `skipped claude: … not found` or `skipped codex: … not found` means that tool has never run on this computer, which is fine. Exit 2 means it found neither tool's folder: run it once more for your own tool only. If you are Claude Code:
   ```
   python "<framework>/scripts/install_skills.py" --claude
   ```
   If you are Codex:
   ```
   python "<framework>/scripts/install_skills.py" --codex
   ```
   A `refused <skill>` line names a folder of that name, in a skill folder, that is not an RA_Agent skill. Tell the person, and ask whether you may move it aside. On yes, move it out of the skill folder to `<backup>`, the folder `<skill>-backup-<date>` in the tool's folder, for example `~/.claude/session-start-backup-2026-10-27`; write both paths in full. Then run the install again.
   ```
   python -c "import shutil, sys; shutil.move(sys.argv[1], sys.argv[2])" "<refused folder>" "<backup>"
   ```
   Tell the person how many skills were copied and where. The skills are conveniences: each project's PROTOCOL.md holds the rules, and an AI without the skills follows it alone. Claude Code loads the skills in a new session. Codex loads them when the app starts: tell the person to quit the Codex app and open it again before step 7's first session.
5. **The project.** If step 2 found the clone already there, this is a repeat of an earlier setup: ask whether the person has their project on this computer already. If yes, that folder is `<project>`: go to step 6. Otherwise ask whether the person joins a project their team already has, or creates a new one.
   - **Join.** Ask for the project's GitHub address. `<project>` is `<parent>/<name>`, `<name>` being the last part of the address without `.git`. Clone it, unless `<project>` exists already: then ask whether it is their clone of this project; if yes, use it and go to step 6; if no, ask for another folder name.
     ```
     git clone <project URL> "<project>"
     ```
   - **Create.** Ask the questions for a new project (Ask the human). `<project>` is `<parent>/<folder>`, `<folder>` being a short name made from the project name, in lowercase with `-` between words; it must not exist yet. `<platforms>` is `claude-code`, `codex`, or both separated by a space. Create the project; this makes its first commit and prints its path:
     ```
     python "<framework>/template/protocol/ra.py" init "<project>" --name "<project name>" --person "<Person>" --git-author "<git author>" --platforms <platforms> --role "<role>"
     ```
     If it exits 1, show the person its `error:` line and ask for the corrected value. If it exits 2 and names `unrecognized arguments`, a value with a space lost its quotes: quote it and run the command again.
6. **Connect, update and check the project.** See whether the project has a remote, its copy on GitHub; this prints `origin` when it has one:
   ```
   git -C "<project>" remote
   ```
   - It prints `origin`: bring in the team's latest work; it prints nothing when that succeeds.
     ```
     cd "<project>" && python protocol/ra.py sync pull
     ```
     If its `error:` line says there is no tracking information, the project's first push never went through: send it now, with only the second command of the next block, `git -C "<project>" push -u origin main`. For any other error, see Stop conditions.
   - It prints nothing: ask the GitHub question (Ask the human). If the person gives an address, connect the project to it and send its history:
     ```
     git -C "<project>" remote add origin <project URL>
     git -C "<project>" push -u origin main
     ```
     If they answer "later", the project stays on this computer and sessions skip pull and push (PROTOCOL.md §6, session-start step 2); pasting the setup sentence again asks once more.

   Then find who the person is. `ra init` set this already for a project created in step 5. Otherwise read the Members table of `<project>/PROJECT.md`, and print the name and email git uses in the project:
   ```
   git -C "<project>" config user.name
   git -C "<project>" config user.email
   ```
   If they form a row's Git author name, `Name <email>`, the identity is set. Otherwise ask which row is the person's, and set the identity to that row's Git author name, `<Name>` and `<email>` being its two parts (PROTOCOL.md §2); then tell the person what you set. If no row is theirs, see Stop conditions.
   ```
   git -C "<project>" config --local user.name "<Name>"
   git -C "<project>" config --local user.email "<email>"
   ```
   Check the project; it prints `check: no findings` when the files are in order:
   ```
   cd "<project>" && python protocol/ra.py check
   ```
   Findings in a joined project were there before the person joined: report them; they do not stop the setup (PROTOCOL.md §14).
7. **Hand over.** Tell the person, in these words or plainer:
   - If you use Codex, quit the app and open it again first.
   - Open the folder `<project>` in Claude Code or Codex, in a new session, and say `start my session`.
   - Day to day, three sentences do the work: `start my session`; `Add this paper to the project: <path to the PDF>`; `end my session`.
   - When the AI proposes a question, fact or decision for the shared repository, it asks `Commit / Edit / Skip?`. `Commit` saves it with you as the approver, `Edit` lets you change it first, and `Skip` saves nothing.
   - A teammate can join once a member has added them. To add one, say in a session: `Add <their name> to the project as a member: <their name> <their email>, <Claude Code, Codex or both>, <their role>.` The AI shows the new row of PROJECT.md Members and asks `Commit / Edit / Skip?` (PROTOCOL.md §2, Adding a member).
   - To update the framework and the skills later, paste the setup sentence again.

## Ask the human

One question at a time, in plain words; the placeholder each answer fills is in brackets.

- Step 5, repeated setup: "Is your project on this computer already? If yes, which folder is it in?" (`<project>`)
- Step 5: "Do you want to join a project your team already has, or create a new one?"
- Step 5, join: "What is the project's GitHub address?" (`<project URL>`)
- Step 5, create:
  - "What is the project's name?" (`<project name>`)
  - "What is your name, as your teammates should see it?" (`<Person>`)
  - "Which name and email should the project record for your work? Use the email of your GitHub account, for example `Ana Silva <ana@uni.edu>`." (`<git author>`)
  - "Which AI tools will you use for this project: Claude Code, Codex, or both?" (`<platforms>`)
  - "What is your role in the project, for example PI or PhD student?" (`<role>`)
- Step 6, no remote: "Your teammates reach the project through GitHub. On github.com, click New repository, give it a name, choose Private, and add nothing: no README, no .gitignore and no license, so that it starts empty. Then paste its address here, or say 'later' to keep the project on this computer for now." (`<project URL>`)
- Step 6, when no row matches: "Which of these members are you?", followed by the Person column of PROJECT.md Members.

## Stop conditions

Stop and tell the person in plain words what happened and what fixes it. Where the fix below is yours to run, offer it and, on yes, run it, then retry the failed command. Where the person must act, such as installing something, wait; afterwards they paste the setup sentence again, and the finished steps repeat without harm.

- **git is missing** (step 2): the person installs it from https://git-scm.com/downloads, then quits and reopens the app.
- **Sign-in** (a clone, pull or push in steps 2, 5 or 6 fails with `Repository not found`, `Authentication failed`, `could not read Username` or a request for a password): git on this computer is not signed in to a GitHub account that may use this repository. Tell the person that their computer needs to be signed in to GitHub, with an account to which the repository's owner has given access. If `gh --version` prints a version, offer to sign them in. Run the first command below in the background if your tool can, because it waits until the person has signed in; it prints a one-time code. Tell the person the code; they enter it on the GitHub page that opens, or at https://github.com/login/device, and sign in. Then run the second command, so that git uses this sign-in, and retry.
  ```
  gh auth login --web --git-protocol https
  gh auth setup-git
  ```
  If `gh` is missing, the person installs GitHub CLI from https://cli.github.com, as they would any app, and tells you; then sign them in as above. On Windows, git may instead open a sign-in window of its own when you retry; the person signs in there.
- **Python is missing or older than 3.10** (step 3): the person installs Python from https://www.python.org/downloads/ (on Windows, ticking "Add python.exe to PATH" in the installer), then quits and reopens the app.
- **PyYAML still does not install** (step 3): show pip's error; the person installs Python from python.org, as above.
- **`install_skills.py` exits 1** (step 4) for another reason than a refused folder, or exits 2 again with your tool's flag: show its output.
- **The pull of step 6 reports a merge conflict** (`protected` or `other` lines after its `error:` line): leave it in place and tell the person; a human resolves it (PROTOCOL.md §9).
- **The push of step 6 is rejected** because the GitHub repository is not empty: ask the person for a new, empty one, as the GitHub question says, then point the project at it and push again. A sign-in error: see "Sign-in", then push again.
  ```
  git -C "<project>" remote set-url origin <project URL>
  git -C "<project>" push -u origin main
  ```
- **No Members row is the person's** (step 6): only an existing member may add one (PROTOCOL.md §2, Adding a member); never add it yourself. Ask the person for the four values of the create questions (name, name and email, tools, role), and give them this sentence for a teammate who is a member to say in a project session: `Add <Person> to the project as a member: <git author>, <platforms>, <role>.` When that teammate has added the row, the person pastes the setup sentence again; step 6 pulls the new row before it reads Members.
- **`check` prints an `error:` line** (step 6), rather than findings: show it.

## What this changes on the computer

- `<framework>`: a clone of this repository.
- `~/.claude/skills/<skill>/` and `~/.codex/skills/<skill>/`: one folder per skill, for each tool present; other folders there stay as they are, except a refused folder the person let you move to its backup.
- `<project>`: the project, cloned or created, with the person's name and email, and the address of its GitHub copy, in its git settings.
- PyYAML, if step 3 installed it; git's sign-in settings, if you signed the person in.
