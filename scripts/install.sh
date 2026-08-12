#!/usr/bin/env sh
# Link the skills in this repo into every agent that is installed locally.
#
# Each skill is linked individually, so other skills already present in an
# agent's directory are left alone and several skill repos can coexist.
#
# Usage:
#   ./scripts/install.sh              link into every detected agent
#   ./scripts/install.sh --dry-run    show what would happen, change nothing
#   ./scripts/install.sh --target DIR link into DIR as well
#   ./scripts/install.sh --uninstall  remove links that point at this repo
#
# Safe to run repeatedly. Existing real directories are backed up, never
# overwritten; links already pointing at this repo are left as they are.

# Word splitting on the space-separated lists below is deliberate: this is
# POSIX sh, so there are no arrays to reach for instead.
# shellcheck disable=SC2086

set -eu

REPO_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
SKILLS_DIR="$REPO_DIR/skills"

DRY_RUN=0
UNINSTALL=0
EXTRA_TARGETS=""

while [ $# -gt 0 ]; do
	case "$1" in
	--dry-run | -n) DRY_RUN=1 ;;
	--uninstall) UNINSTALL=1 ;;
	--target)
		[ $# -ge 2 ] || { echo "--target needs a directory" >&2; exit 2; }
		EXTRA_TARGETS="$EXTRA_TARGETS $2"
		shift
		;;
	-h | --help)
		sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
		exit 0
		;;
	*)
		echo "Unknown option: $1" >&2
		exit 2
		;;
	esac
	shift
done

# Where each agent looks for personal skills. One "Label:path" per line; the
# agent counts as installed if the parent of that path exists.
#
# Only global directories belong here. Some tools (Cursor, for one) support
# skills per project but have no personal location — link those with --target.
AGENTS="Claude Code:$HOME/.claude/skills
Codex CLI:$HOME/.codex/skills
Gemini CLI:$HOME/.gemini/skills
GitHub Copilot:$HOME/.copilot/skills
OpenCode:$HOME/.config/opencode/skills
Neutral (.agents):$HOME/.agents/skills"

say() { printf '%s\n' "$*"; }
run() { if [ "$DRY_RUN" -eq 1 ]; then say "    would: $*"; else "$@"; fi; }

# Resolve a symlink one hop; portable in a way `readlink -f` is not on macOS.
link_target() { readlink "$1" 2>/dev/null || true; }

[ -d "$SKILLS_DIR" ] || { echo "No skills/ directory in $REPO_DIR" >&2; exit 1; }

SKILL_NAMES=""
for skill in "$SKILLS_DIR"/*/; do
	[ -d "$skill" ] || continue
	[ -f "$skill/SKILL.md" ] || continue
	SKILL_NAMES="$SKILL_NAMES $(basename "$skill")"
done

[ -n "$SKILL_NAMES" ] || { echo "No skills found in $SKILLS_DIR" >&2; exit 1; }

say "Repo:   $REPO_DIR"
say "Skills:$SKILL_NAMES"
[ "$DRY_RUN" -eq 1 ] && say "Mode:   dry run (nothing will change)"
say ""

# Build the list of skill directories to install into. Agent labels contain
# spaces, so split on newlines only — the default IFS would turn
# "Claude Code:/Users/x/.claude/skills" into two useless fields.
TARGETS=""
OLD_IFS=$IFS
IFS='
'
for entry in $AGENTS; do
	name=${entry%%:*}
	dir=${entry#*:}
	# The agent is installed if its config directory exists; the skills
	# directory underneath is ours to create.
	parent=$(dirname "$dir")
	if [ -d "$parent" ]; then
		TARGETS="$TARGETS $dir"
		say "Found $name -> $dir"
	fi
done
IFS=$OLD_IFS
for extra in $EXTRA_TARGETS; do
	TARGETS="$TARGETS $extra"
	say "Additional target: $extra"
done

if [ -z "$TARGETS" ]; then
	say ""
	say "No agents detected. Nothing to do."
	say "Pass --target /path/to/skills to link somewhere specific."
	exit 0
fi

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LINKED=0
SKIPPED=0
BACKED_UP=0
REMOVED=0

for target in $TARGETS; do
	say ""
	say "$target"

	if [ "$UNINSTALL" -eq 0 ]; then
		[ -d "$target" ] || run mkdir -p "$target"
	elif [ ! -d "$target" ]; then
		say "    (does not exist, skipping)"
		continue
	fi

	for skill in $SKILL_NAMES; do
		src="$SKILLS_DIR/$skill"
		dest="$target/$skill"
		current=$(link_target "$dest")

		if [ "$UNINSTALL" -eq 1 ]; then
			if [ "$current" = "$src" ]; then
				run rm "$dest"
				say "    removed $skill"
				REMOVED=$((REMOVED + 1))
			fi
			continue
		fi

		if [ "$current" = "$src" ]; then
			say "    $skill (already linked)"
			SKIPPED=$((SKIPPED + 1))
			continue
		fi

		# Something else is there. A stale symlink can go; a real
		# directory is someone's work and gets moved aside instead.
		if [ -L "$dest" ]; then
			run rm "$dest"
		elif [ -e "$dest" ]; then
			backup="$dest.backup-$TIMESTAMP"
			run mv "$dest" "$backup"
			say "    backed up existing $skill -> $(basename "$backup")"
			BACKED_UP=$((BACKED_UP + 1))
		fi

		run ln -s "$src" "$dest"
		say "    linked $skill"
		LINKED=$((LINKED + 1))
	done
done

say ""
if [ "$UNINSTALL" -eq 1 ]; then
	say "Removed $REMOVED link(s)."
else
	say "Linked $LINKED, already current $SKIPPED, backed up $BACKED_UP."
	say "Pull this repo and the agents pick up changes with no further steps."
	say ""
	say "Most agents scan for skills at startup, so restart any that are running."
	say "Tools with no personal skills directory (Cursor, and IDE extensions that"
	say "keep skills per workspace) need a per-project link instead:"
	say "  $0 --target /path/to/project/.cursor/skills"
fi
[ "$DRY_RUN" -eq 1 ] && say "(dry run — nothing was actually changed)"

exit 0
