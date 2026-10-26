---
name: project-init
description: Creates a new RA_Agent shared research project repository by running ra init from a local clone of the Research-Team-Agents framework repository with the project name and the first member's row, then sends the user to the new project's PROTOCOL.md. Make sure to use it whenever the user wants to create a new project, init a project repo, set up a shared repo for a research team, or start a new RA_Agent project, even if they do not say "init"; it is not for work inside an existing project.
---

## Implements

PROTOCOL.md §2 "Creating a project": a human runs `ra init` from a checkout of the framework repository. It is not a verb of §6. Until the project exists, the PROTOCOL.md to read is the clone's `template/PROTOCOL.md`; an installed plugin carries no `template/`.

## Steps

1. Ask the user for the path of their local clone of the framework repository, `<framework-checkout>`. Never assume one. Check that `<framework-checkout>/template/protocol/ra.py` exists.
2. Ask the user for the destination `<dest>`, an absolute path to a folder that does not exist yet or is empty; the project name; and the first member's row of PROJECT.md Members: `<Person>`, `<git author>` as `Name <email>`, `<platforms>` (`claude-code`, `codex`, or both separated by a space) and `<role>`.
3. Create the project; `ra init` makes its first commit and prints its path:
   ```
   python <framework-checkout>/template/protocol/ra.py init <dest> --name "<project name>" --person <Person> --git-author "<git author>" --platforms <platforms> --role <role>
   ```
4. Tell the user the printed path, and to open `<dest>/PROTOCOL.md` and read sections 1–5 before the first session there.

## Stop conditions

- **No clone path, or no `template/protocol/ra.py` under it**: ask again; never guess a path.
- **`init` exits 1**: show the user its `error:` line, such as a git author that is not `Name <email>` or a `<dest>` that is not empty, and ask for corrected values.
- **`init` exits 2**: its usage line names a missing flag or a refused value, such as an unknown platform; ask the user for the value and run the command again.
- **`python` is missing or too old, or `ra init` reports that `yaml` is missing**: follow §2 "The helper" of the clone's `template/PROTOCOL.md`.
