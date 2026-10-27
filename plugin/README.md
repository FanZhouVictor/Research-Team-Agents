# ra-agent: the Claude Code plugin

This plugin gives Claude Code the skills that run the RA_Agent shared-repo protocol: one per verb of PROTOCOL.md §6, plus `project-init`. The protocol is `PROTOCOL.md`, which `ra init` copies from `template/PROTOCOL.md` into every project, and it is the single source of truth. A skill names the PROTOCOL.md section it implements, lists the `python protocol/ra.py` commands of that runbook in order, and says when to stop. It holds no rule of its own, so a rule cannot drift between Claude Code and Codex, and a session without the plugin, such as any Codex session, works from PROTOCOL.md alone. Where a skill and PROTOCOL.md differ, PROTOCOL.md wins.

## Skills

| Skill | Implements | Use it to |
|---|---|---|
| `project-init` | PROTOCOL.md §2 "Creating a project" | create a project repository with `ra init` |
| `session-start` | PROTOCOL.md §6 session-start | open a session: pull, digest, open questions, check |
| `session-end` | PROTOCOL.md §6 session-end, with update-status | close a session: log entry, status, push |
| `add-literature` | PROTOCOL.md §6 add-literature, with §7 | add a paper: dedup, full read, record and claims, or hand it to `reread-literature` |
| `reread-literature` | PROTOCOL.md §6 reread-literature, with §7 | re-read a recorded paper: verify or dispute its claims, append claims |

Seven more skills follow, one for each remaining verb of PROTOCOL.md §6: `propose-question`, `close-question`, `propose-knowledge`, `propose-decision`, `accept-decision`, `supersede-decision` and `update-status`.

Claude Code uses a skill on its own when a request matches the skill's description. You can also run one as `/ra-agent:<skill>`, for example `/ra-agent:session-start`.

## Install from a local checkout

Keep a clone of this framework repository: `project-init` needs it, because an installed plugin does not carry `template/`. The skill asks for the clone's path and runs `<clone>/template/protocol/ra.py init`.

1. Clone the framework repository, for example to `~/Research-Team-Agents`.
2. Validate the plugin:
   ```
   claude plugin validate ~/Research-Team-Agents/plugin
   ```
3. Load it for one session:
   ```
   claude --plugin-dir ~/Research-Team-Agents/plugin
   ```
   or for every session, by copying the plugin directory, with its `.claude-plugin/plugin.json`, under `~/.claude/skills/`:
   ```
   cp -R ~/Research-Team-Agents/plugin ~/.claude/skills/ra-agent
   ```
   A copy does not follow `git pull` in the clone; copy it again after an update.
4. In a running session, `/reload-plugins` loads edits made to the plugin's files.

## Documentation checked

The manifest, the layout and the install steps follow the Claude Code plugin documentation, read on 2026-10-26:

- https://code.claude.com/docs/en/plugins: a plugin is a directory of components, usually with a manifest at `.claude-plugin/plugin.json`.
- https://code.claude.com/docs/en/plugins/manifest-reference: `name` is the only required field; `version`, `description` and `author` (an object whose `name` is required) are optional metadata; skills load from `skills/<name>/SKILL.md` by default.
- https://code.claude.com/docs/en/plugins/components: every skill under `skills/` loads without being listed in the manifest and runs as `/<plugin>:<skill>`.
- https://code.claude.com/docs/en/skills: the `name` and `description` frontmatter of `SKILL.md`; a plugin skill's `name` sets the last part of its command.
- https://code.claude.com/docs/en/plugins/create: `claude plugin validate`, `claude --plugin-dir` and `/reload-plugins`.
- https://code.claude.com/docs/en/plugins/publish: "Share a plugin without a marketplace": `--plugin-dir` for one session, or the plugin directory under `~/.claude/skills/` for every session.
