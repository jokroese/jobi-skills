# Migrating existing installations to Skillshare

The supported local setup uses the repository's `skills/` directory as its
editable source and Skillshare in merge mode to manage selected links.
The example configuration lists committed skills only. A personal configuration
may also select local drafts without including them in a migration commit.

## Migration order

1. Inventory existing skill directories and installed jobi plugins. Record
   link destinations and compare real directories against the source. Keep
   rollback copies outside skill-discovery directories so agents cannot load
   the backup as another skill.
2. Configure the intended source and skill selections following `README.md`.
   Use stable absolute paths. On macOS, resolve directory aliases with
   `pwd -P` before using custom configuration or state locations.
3. Preview and sync. Verify that each selected skill links to the intended
   source and that bundled scripts and references are readable.
4. Verify direct skill discovery in a fresh agent session. Remove redundant
   jobi links from obsolete locations only when the replacement works. Never
   remove an entire provider directory: it may hold unrelated skills.
5. Uninstall the legacy jobi plugin through its native client, then remove its
   marketplace registration. This prevents a cached packaged version from
   competing with the linked source.

For the old `jobi-skills@jobi-skills` bundle, the native removal commands are:

```sh
codex plugin remove jobi-skills@jobi-skills
codex plugin marketplace remove jobi-skills
claude plugin uninstall jobi-skills@jobi-skills --scope user --keep-data
claude plugin marketplace remove jobi-skills --scope user
```

Run only commands matching the recorded installed identifiers and scope. A
client may remove a registration with its last plugin; verify absence rather
than treating an already-absent registration as failed cleanup. Use native
commands instead of deleting caches while their installed-state records remain.

The old installer placed identical links in several provider directories.
Codex, Copilot and OpenCode read `~/.agents/skills`, so their redundant jobi
links in `~/.codex/skills`, `~/.copilot/skills` and
`~/.config/opencode/skills` can be removed after shared discovery is verified.
Keep Claude Code's `~/.claude/skills` target. OpenCode also reads that directory;
if a skill is present in both locations, link both to the same source so their
contents cannot diverge. Per-target filters are not isolation between tools
that share discovery paths.

An old checkout may contain uncommitted `.agents/plugins/marketplace.json`
and `plugins/` wrappers. Archive those obsolete files outside the repository
before removing them. Keep draft `skills/` folders and their README catalogue
changes for subsequent skill commits.

## Verification performed

The isolated trial used Skillshare 0.26.3 on macOS arm64 and verified selective
linking, repeat-sync stability, adoption of existing installer links, cleanup
after deselection and deletion, live resource edits, and preservation of
independent folders and symlinks. A conflicting real directory was preserved
without `--force`.

The earlier plugin trial is historical evidence, not a supported setup path.
Its complete temporary package passed Codex CLI install, resource loading,
update and removal. External-link wrappers omitted skill contents during
packaging, and aliased temporary state paths caused an update failure. Direct
skill links avoid that extra packaging and cache lifecycle.

The live migration used Homebrew Skillshare 0.26.4. A fresh Codex CLI session
loaded the linked `pixel-art` skill and read its bundled script; the script
hash matched the repository source. Native commands removed the legacy Codex
and Claude Code jobi plugins and their marketplace registrations. The old
installed real directory was archived outside discovery paths, and redundant
provider links were removed. Source files and unrelated installations were
preserved. Desktop activation still needs a fresh chat. Verify
an application's loaded skill list separately from on-disk links: existing
chats may retain instructions already loaded earlier.

## Rollback

Retain the original real directories and link inventory until the new setup
has been used successfully. Restore only the affected entries from that
backup, after checking that no newer edits would be overwritten. Do not use
`skillshare uninstall` to undo target links: it removes source skills.

## References

- [Skillshare configuration](https://skillshare.runkids.cc/docs/reference/targets/configuration/)
- [Sync modes and conflict handling](https://skillshare.runkids.cc/docs/reference/commands/sync/)
- [Codex local skills](https://learn.chatgpt.com/docs/build-skills)
- [OpenCode skill discovery](https://opencode.ai/docs/skills/)
- [Copilot CLI reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference)
- [Claude Code skill locations](https://code.claude.com/docs/en/skills#choose-where-skills-load)
