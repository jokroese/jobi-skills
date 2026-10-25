# jobi-skills

Portable [Agent Skills](https://agentskills.io): reusable instructions and
supporting files that coding agents load when needed.

## Skills

| Skill | What it does |
| --- | --- |
| [`build123d`](skills/build123d) | Designs parametric 3D-printable parts in build123d, then measures, checks and renders them |
| [`git-commit`](skills/git-commit) | Writes Conventional Commit messages that follow the repository's conventions |
| [`normalise-to-markdown`](skills/normalise-to-markdown) | Reconstructs Markdown structure from OCR or pasted text without rewriting its content |

## Install with Skillshare

[Skillshare](https://github.com/runkids/skillshare) manages skill selection and
links. This repository stays the editable source; plugin packaging and the
previous custom installer are no longer supported.

```sh
brew install skillshare
git clone https://github.com/jokroese/jobi-skills.git
cd jobi-skills
```

Use a long-lived checkout as the source. Keep machine-specific installation
settings in `~/.config/skillshare/config.yaml`. The
[example configuration](examples/skillshare/config.yaml) selects the two
committed skills for the shared agent directory and Claude Code.

If you do not already have a Skillshare configuration:

```sh
mkdir -p ~/.config/skillshare
# Refuse to overwrite existing settings.
test ! -e ~/.config/skillshare/config.yaml &&
  cp examples/skillshare/config.yaml ~/.config/skillshare/config.yaml
```

Edit the copied configuration: replace `source` with the absolute path to this
checkout's `skills/` directory and choose the targets and `include` lists you
want. If you already use Skillshare, integrate this source and selection with
your existing setup instead of replacing its configuration.

Use **merge** mode: it links each selected skill separately and preserves
independent local folders. Skillshare's mode named `symlink` links the whole
directory and ignores selection filters.

```sh
skillshare sync -g --dry-run
skillshare sync -g
skillshare status -g
skillshare diff -g
```

`-g` selects your global configuration even inside a repository with a
project-level Skillshare configuration. Review the dry-run targets before
applying. A conflicting real directory is preserved; compare it with the
source and back it up before replacing it. Avoid `--force` as a shortcut.

Use `~/.agents/skills` as the shared default: it is the documented user location
for [Codex](https://learn.chatgpt.com/docs/build-skills) and is supported by
[Copilot CLI](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference#skill-locations)
and [OpenCode](https://opencode.ai/docs/skills/). This is a shared discovery
convention; the [Agent Skills specification](https://agentskills.io/specification)
defines the package format rather than a universal installation directory.
[Claude Code](https://code.claude.com/docs/en/skills#choose-where-skills-load)
documents `~/.claude/skills`, so retain that compatibility target, linked to
the same source files. Tools that read several
locations can still encounter overlaps; avoid adding redundant provider-specific
targets for the same skills. These settings cover local skill discovery, not
account-level uploads or plugin-only application surfaces.

For an existing installation, follow the
[migration notes](docs/skillshare-migration.md) before removing old links or
uninstalling plugins.

## Keeping skills current

- Edit existing skills in `skills/`. Linked files change immediately on disk;
  no sync is needed for content edits.
- After adding, renaming or removing skills, or changing target selection,
  update the intended `include` lists and run `skillshare sync -g --dry-run`,
  then `skillshare sync -g`.
- After pulling repository changes, sync to reconcile additions and removals.
- Start a fresh agent chat to verify changed instructions. An existing chat
  may already have loaded an earlier version.

Skillshare does not need to run in the background for linked content edits.
Use normal Git commands for this authoring repository. Skillshare's upstream
update commands are for imported skills with tracked upstream metadata.

## Adding a skill

```text
skills/<skill-name>/
├── SKILL.md          # frontmatter and instructions
├── references/       # detail loaded when needed
├── scripts/          # deterministic helpers
├── assets/           # templates and output resources
└── evals/evals.json  # test prompts and assertions
```

`SKILL.md` needs `name` and `description` in YAML frontmatter. Describe concrete
triggers in `description`, because agents use it to decide when to load the
skill. See [AGENTS.md](AGENTS.md) for the writing and synchronisation workflow.

Validate before committing:

```sh
python3 scripts/validate.py
```

CI validates the skills and checks bundled shell scripts. Skillshare itself is
maintained upstream; this repo does not implement another installation manager.

## Licence

MIT. See [LICENSE](LICENSE).
