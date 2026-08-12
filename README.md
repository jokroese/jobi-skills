# jobi-skills

Portable [Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
— reusable instructions that any AI coding agent can load on demand.

A skill is a folder with a `SKILL.md` in it. That is the whole format. Claude
Code, Codex CLI, Gemini CLI, Cursor, Copilot and around thirty other tools read
it unchanged, so nothing here is tied to a single vendor.

## Skills

| Skill                             | What it does                                                                                          |
| --------------------------------- | ----------------------------------------------------------------------------------------------------- |
| [`git-commit`](skills/git-commit) | Writes a Conventional Commits message for staged work, matching the conventions the repo already uses |

## Using these skills

Every agent looks for skills in its own directory — `~/.claude/skills`,
`~/.codex/skills`, and so on. Same files, different lookup path. The install
script symlinks each skill into every agent it finds, so there is one copy on
disk and nothing to keep in sync:

```bash
git clone https://github.com/<you>/jobi-skills.git
cd jobi-skills
./scripts/install.sh
```

It detects which agents you have installed, links skills one by one so anything
already in those directories is left alone, backs up real directories rather
than overwriting them, and is safe to run again after you pull.

```bash
./scripts/install.sh --dry-run                 # show what would happen
./scripts/install.sh --target ~/proj/.claude/skills   # somewhere specific
./scripts/install.sh --uninstall               # remove links to this repo
```

Because the links point at the repo, `git pull` updates every agent at once.

Most agents scan their skills directories at startup, so **restart anything
that was already running**.

### Where each agent looks

| Agent | Personal skills | Notes |
|-------|-----------------|-------|
| Claude Code | `~/.claude/skills` | |
| Codex CLI | `~/.codex/skills` | also reads `.codex/skills` per project |
| Gemini CLI | `~/.gemini/skills` | |
| GitHub Copilot | `~/.copilot/skills` | |
| OpenCode | `~/.config/opencode/skills` | also reads `~/.claude/skills` and `~/.agents/skills` |
| Cursor | — | project only: `.cursor/skills` |

For anything not listed, or for project-scoped installs:

```bash
./scripts/install.sh --target ~/my-project/.cursor/skills
```

`~/.agents/skills` is the vendor-neutral location some tools read. The script
links there if `~/.agents` exists.

### Claude Desktop and Cowork

These do **not** read `~/.claude/skills` — that path is Claude Code (the CLI).
The desktop app loads skills from installed plugins and from skills saved to
your account, so install this repo as a plugin instead:

```
/plugin marketplace add <you>/jobi-skills
/plugin install jobi-skills
```

### Without the script

Nothing depends on the installer. Copy `skills/git-commit/` wherever your agent
looks for skills and it will work — you just take on keeping the copy current.

### As a plugin

`.claude-plugin/` holds the metadata that lets Claude Code and Cowork install
this repo with `/plugin marketplace add` (see above). Other agents ignore those
files — additive metadata, not a dependency.

## Adding a skill

```
skills/<skill-name>/
├── SKILL.md          # required — frontmatter + instructions
├── references/       # detail loaded only when needed
├── scripts/          # deterministic steps, so the model doesn't improvise them
├── assets/           # templates and files that end up in the output
└── evals/evals.json  # test prompts and assertions
```

`SKILL.md` needs YAML frontmatter with `name` and `description`. The
description is the only thing an agent sees before deciding whether to load the
skill, so it should name concrete triggers rather than describe the skill in
the abstract.

`AGENTS.md` has the full house style — read it before writing one, or point
your agent at it.

Validate before committing:

```bash
python3 scripts/validate.py
```

CI runs the same check on every push.

## Licence

MIT. See [LICENSE](LICENSE).
