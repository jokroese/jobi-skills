# Working in this repository

This repo is a library of Agent Skills. Everything in `skills/` is read by
other agents at runtime, so the writing _is_ the product — treat a change to a
`SKILL.md` with the same care as a change to source code.

## Layout

```
skills/<name>/
├── SKILL.md          required
├── references/       loaded on demand
├── scripts/          executable, deterministic steps
├── assets/           templates and files used in output
└── evals/evals.json  test prompts and assertions
```

Nothing outside `skills/` is read by agents at runtime. `scripts/` at the repo
root is for maintaining the repo itself; the per-skill `scripts/` directories
are what skills invoke.

## Frontmatter

```yaml
---
name: skill-name # lowercase, hyphenated, matches the directory name
description: ... # see below
---
```

`name` and `description` are the only required fields, and the only two that
every agent implementation reads. Adding vendor-specific keys is fine but they
will be ignored elsewhere, so don't build behaviour on them.

## Writing the description

The description is the entire basis on which an agent decides whether to load
the skill. It sits in context permanently, competing with every other skill's
description, and the body is never seen unless the description wins.

Two things to get right:

- **Name concrete triggers.** The phrases a user would actually type, the file
  types involved, the situations where it applies. "Helps with documentation"
  triggers on nothing. "Use when the user asks for a README, changelog, or API
  reference, or mentions .md files in docs/" triggers reliably.
- **Lean towards over-triggering.** Models systematically under-use skills.
  Adding "even if they don't use the word X" or "also use when Y" costs a few
  tokens and materially improves recall.

All "when to use this" information belongs in the description, not the body —
by the time the body is loaded, the decision has already been made.

## Writing the body

**Explain why, not just what.** A model that understands the reason behind an
instruction handles the cases you didn't anticipate. A model following a rule
it doesn't understand fails the moment reality diverges from your example.
Every constraint should carry its rationale.

**Prefer explanation to shouting.** Rows of `MUST` and `NEVER` in caps are a
sign the instruction hasn't been made convincing. Reserve emphasis for genuine
safety boundaries — destructive commands, credentials, irreversible actions.

**Use the imperative.** "Read the config file", not "you should read" or "the
agent will read".

**Keep it general.** Skills get used thousands of times across contexts you
will never see. Instructions overfitted to the examples in front of you are
worse than slightly vaguer instructions that generalise.

**Stay under ~500 lines.** Past that, move detail into `references/` and point
at it from the body with a note on when to read it. Reference files over 300
lines need a table of contents.

**Bundle repeated work as a script.** If every invocation would have the model
write the same helper, write it once in `scripts/` and have the skill call it.
Deterministic steps — exact CLI invocations, SQL, output templates — belong in
scripts and assets, not in prose the model reinterprets each time.

**Show, don't describe, output formats.** Models pattern-match from examples
far better than they follow descriptions of structure. Put a template in
`assets/` and say "follow this shape".

## Progressive disclosure

Three levels, and knowing which is which keeps context lean:

1. `name` + `description` — always loaded, for every skill in the library
2. `SKILL.md` body — loaded when the skill triggers
3. `references/`, `scripts/`, `assets/` — loaded or executed only when needed

Anything that isn't needed on every invocation belongs at level 3.

## Before committing

```bash
python3 scripts/validate.py
```

Checks frontmatter parses, required fields are present, `name` matches the
directory, and referenced files exist. CI runs the same script.

Commit messages follow the `git-commit` skill in this repo. Scope by skill
name where it applies: `feat(git-commit): add breaking-change guidance`.

## Testing a skill

`skills/<name>/evals/evals.json` holds test prompts and assertions. The
`skill-creator` skill runs them against agents with and without the skill and
reports the difference — worth doing before merging a substantive change, since
a skill that doesn't beat the baseline is just context tax.
