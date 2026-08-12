# Conventional Commits — full reference

Consolidated from the [Conventional Commits 1.0.0 spec](https://www.conventionalcommits.org/en/v1.0.0/).
Read this when SKILL.md does not cover the case in hand.

## Contents

- [Grammar](#grammar)
- [Rules from the specification](#rules-from-the-specification)
- [Breaking changes](#breaking-changes)
- [Footers](#footers)
- [Revert commits](#revert-commits)
- [Semantic versioning mapping](#semantic-versioning-mapping)
- [Merge and fixup commits](#merge-and-fixup-commits)
- [Edge cases](#edge-cases)

## Grammar

```
<type>[optional scope][optional !]: <description>

[optional body]

[optional footer(s)]
```

Concretely:

```
feat(parser): add ability to parse arrays

The previous tokeniser bailed on '[' because array support was
deferred in the original design.

Reviewed-by: Z
Refs: #123
```

## Rules from the specification

1. Commits MUST be prefixed with a type, followed by an optional scope, an
   optional `!`, and a required terminal colon and space.
2. `feat` MUST be used when a commit adds a new feature.
3. `fix` MUST be used when a commit patches a bug.
4. A scope MAY be provided after a type, and MUST consist of a noun describing
   a section of the codebase, surrounded by parentheses: `fix(parser):`.
5. A description MUST immediately follow the colon and space, and is a short
   summary of the code changes.
6. A longer body MAY be provided after the description, beginning one blank
   line after it. The body is free-form and may consist of multiple
   newline-separated paragraphs.
7. One or more footers MAY be provided one blank line after the body.
8. Types other than `feat` and `fix` MAY be used.
9. The units of information in a commit MUST NOT be treated as case sensitive
   by implementers, with the exception of `BREAKING CHANGE`, which MUST be
   uppercase.
10. `BREAKING-CHANGE` MUST be synonymous with `BREAKING CHANGE` when used as a
    footer token.

## Breaking changes

A breaking change can be signalled two ways, and using both is common:

**`!` in the subject** — immediately before the colon, after any scope.

```
feat(api)!: send an email when a product ships
refactor!: drop support for Node 14
```

**`BREAKING CHANGE:` footer** — uppercase, followed by a description of what
broke and what to do instead.

```
refactor: drop support for Node 14

BREAKING CHANGE: Node 14 reached end of life in April 2023. The minimum
supported version is now Node 18.
```

If the `!` is used, the `BREAKING CHANGE:` footer is optional per the spec —
but writing it anyway is better practice, because the `!` alone tells a reader
that something broke without telling them what.

A breaking change is valid with any type, not just `feat` and `fix`.

## Footers

Footers follow the [git trailer](https://git-scm.com/docs/git-interpret-trailers)
convention: a token, then either `: ` or ` #`, then a value.

```
Reviewed-by: Alice Chen <alice@example.com>
Co-authored-by: Bob Singh <bob@example.com>
Refs: #133
Closes #42
Fixes #17, #18
```

Tokens MUST use `-` in place of whitespace (`Acked-by`, not `Acked by`), so
that footers stay distinguishable from body paragraphs. The one exception is
`BREAKING CHANGE`.

A footer value MAY span multiple lines; parsing stops at the next valid footer
token or the end of the message.

GitHub, GitLab and similar close issues automatically on the keywords `close`,
`closes`, `closed`, `fix`, `fixes`, `fixed`, `resolve`, `resolves`, `resolved`
— case-insensitive, and only when the commit lands on the default branch.

## Revert commits

The spec does not mandate a format for reverts, but recommends the `revert`
type with a footer referencing the reverted SHAs:

```
revert: let us never again speak of the noodle incident

Refs: 676104e, a215868
```

`git revert` generates its own message (`Revert "<original subject>"`), which
is fine to keep — it is machine-readable in a different way and tools generally
understand it.

## Semantic versioning mapping

| Commit                                     | Version bump  |
| ------------------------------------------ | ------------- |
| `fix:`                                     | PATCH (0.0.x) |
| `feat:`                                    | MINOR (0.x.0) |
| any type with `!` or `BREAKING CHANGE:`    | MAJOR (x.0.0) |
| everything else (`docs`, `chore`, `ci`, …) | none          |

This is the practical reason the type field matters: release tooling
(semantic-release, changesets, release-please) derives version numbers and
changelogs from it. Mislabelling a `feat` as a `chore` means it silently
disappears from the changelog.

During `0.x` releases, many projects map breaking changes to MINOR rather than
MAJOR. Check the project's release config before assuming.

## Merge and fixup commits

- **Merge commits**: leave the default `Merge branch 'x' into y`. Conventional
  Commits parsers skip them.
- **`fixup!` / `squash!`**: keep the autosquash prefix intact so
  `git rebase --autosquash` works. The conventional message belongs on the
  commit being fixed up, not the fixup itself.
- **Squash merges**: the PR title becomes the commit subject, so it is the PR
  title that needs to be conventional. Many repos enforce this in CI.

## Edge cases

**The change does not fit one type.** Almost always a signal it should be more
than one commit. If it truly cannot be split — a rename that unavoidably
touches source, tests and docs together — pick the type matching the _intent_
and mention the rest in the body.

**Wrong type on a commit already pushed.** Do not rewrite shared history to fix
a label. If release tooling depends on it, fix it forward or amend the
changelog directly.

**Reverting a breaking change.** The revert is itself breaking, and needs its
own `!` and `BREAKING CHANGE:` footer.

**Very large mechanical changes** (a formatter run, a codemod). Use `style` or
`refactor`, note the tool and exact command in the body so the change can be
reproduced, and keep it in its own commit — mixing a codemod with hand-written
changes makes review nearly impossible. Consider adding the SHA to
`.git-blame-ignore-revs`.
