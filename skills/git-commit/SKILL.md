---
name: git-commit
description: Write a Conventional Commits message for work that is staged or in progress, matching the conventions the repository already uses. Use this whenever the user asks for a commit message, says "commit this", "what should I call this commit", asks you to write up or describe changes for git, or when you have just finished a chunk of work and are about to commit it — even if they do not say the words "conventional commits". Also use it when splitting a messy working tree into several coherent commits.
---

# Writing a commit message

A commit message is read far more often than it is written — during `git log`
archaeology, in release notes, in a bisect session at 2am. The job is to leave
whoever reads it next (often the author, months later) able to answer "why did
this change?" without opening the diff.

The default format here is [Conventional Commits](https://www.conventionalcommits.org),
because it is machine-parseable and widely understood. But a repository's own
established habits beat any external standard. Read the room first.

## Step 1: Gather the actual changes

Never write a commit message from memory of what you just did — the working
tree is the source of truth, and it usually contains something you forgot.

```bash
git status --short
git diff --staged
git diff                      # unstaged, so you can spot what is missing
git log --oneline -20         # calibrate to house style
```

If nothing is staged, say so and ask what should go in the commit rather than
staging things yourself. Staging is a judgement call about what belongs
together, and getting it wrong on someone's behalf is annoying to undo.

`scripts/collect-context.sh` runs these four commands in one go if you want the
whole picture in a single tool call.

## Step 2: Match the repository's existing style

Look at the twenty commits you just read and answer three questions:

- **Do they use type prefixes at all?** If the log is full of
  `Fix login redirect` and `Add rate limiting`, this repo writes plain
  imperative subjects. Follow that. Imposing `fix:` on a repo that has never
  used it makes the log inconsistent, which is worse than either convention
  alone.
- **Do they use scopes, and which ones?** Scopes are only useful if they are
  drawn from a stable vocabulary. Reuse the ones already in the log rather than
  inventing `(misc)` or `(various)`.
- **Do they reference issues, and how?** `Closes #123`, `PROJ-456`, or nothing
  at all.

When the log is genuinely mixed or the repo is brand new, use Conventional
Commits as described below.

## Step 3: Choose the type

| Type       | Use when                                       |
| ---------- | ---------------------------------------------- |
| `feat`     | Adds capability a user can observe             |
| `fix`      | Corrects broken behaviour                      |
| `refactor` | Changes structure, not behaviour               |
| `perf`     | Changes performance characteristics            |
| `docs`     | Documentation only                             |
| `test`     | Tests only                                     |
| `build`    | Build system, dependencies, packaging          |
| `ci`       | CI configuration and pipelines                 |
| `chore`    | Housekeeping with no src or test change        |
| `style`    | Formatting, whitespace, no code meaning change |

The common mistake is labelling by _file touched_ rather than _intent_. Editing
a test file to cover a bug you just fixed is part of the `fix`, not a separate
`test`. Adding a dependency in order to build a feature is part of the `feat`.
Ask what the change is _for_, not where it landed.

If the change is user-visible and you are torn between `feat` and `fix`, ask
whether it makes something work that was meant to work (`fix`) or work in a way
it was never meant to before (`feat`).

## Step 4: Write the subject line

```
<type>(<optional scope>): <description>
```

- Imperative mood: "add", not "added" or "adds". The test is that it completes
  the sentence "If applied, this commit will \_\_\_". This is the git convention
  and it keeps subjects short.
- Lowercase after the colon, no full stop at the end.
- Aim for 50 characters, hard limit 72. `git log --oneline` and most UIs
  truncate past that, and a truncated subject is a useless subject.
- Describe the change, not the mechanics. `fix(auth): reject expired refresh
tokens` tells you something; `fix(auth): update if statement` does not.

If you cannot get the subject under 72 characters without losing meaning, that
is usually the commit telling you it should be two commits. See Step 6.

## Step 5: Write the body, when it earns its place

Skip the body when the subject is genuinely self-explanatory — `docs: fix typo
in README` needs nothing more, and padding it with filler makes the log noisier.

Include a body when there is a _why_ that the diff cannot express: the
constraint that forced this approach, the alternative you rejected, the
non-obvious consequence. Wrap at 72 characters, blank line after the subject.

The body is for reasoning, not a restatement of the diff. If a reader can get
it from `git show`, leave it out.

Footers go last, after a blank line:

```
BREAKING CHANGE: <what breaks and what to do instead>
Closes #123
Co-authored-by: Name <email>
```

A breaking change also takes a `!` before the colon in the subject:
`feat(api)!: drop v1 endpoints`. Both markers are conventional; tooling reads
the footer, humans read the `!`.

## Step 6: Consider whether this is really one commit

If the diff spans unrelated concerns — a bug fix plus a dependency bump plus
some drive-by renaming — propose splitting it. Suggest the split with the files
that belong in each part, and let the user decide; do not restage on your own
initiative.

The reason to care is `git bisect` and `git revert`. A commit that does one
thing can be reverted cleanly. A commit that does three things cannot.

## Step 7: Hand it over

Print the message and stop there. Do not run `git commit` unless the user asked
you to commit, and never run `git add -A` or `git commit -a` — both sweep up
files the user may have deliberately left out, including local config and
secrets.

If the repo has a commit hook or a `.gitmessage` template, mention it rather
than working around it.

## Examples

**A fix with a non-obvious cause**

```
fix(auth): reject refresh tokens issued before a password change

Tokens minted before a reset stayed valid until natural expiry, so
changing a password did not actually lock out a session an attacker
already held.

Compares token iat against the user's password_changed_at instead of
maintaining a revocation list, which would need shared state across
the API workers.

Closes #482
```

**A feature that needs no body**

```
feat(export): add CSV output to the reports endpoint
```

**A breaking change**

```
feat(api)!: return ISO 8601 timestamps from all endpoints

BREAKING CHANGE: Timestamps were Unix epoch integers and are now ISO
8601 strings. Clients parsing them as numbers need updating.
```

**A repo that does not use type prefixes** — matching the house style from
Step 2 rather than the table in Step 3:

```
Reject refresh tokens issued before a password change

Closes #482
```

## Reference

`references/conventional-commits.md` has the full specification, including
revert commits, multi-paragraph footers, and the semantic versioning mapping.
Read it when a case is not covered above.
