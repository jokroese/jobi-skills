#!/usr/bin/env sh
# Collect everything needed to write a commit message, in one call.
#
# Usage: sh collect-context.sh [repo-path]
#
# Read-only: inspects the working tree and never stages, commits or
# modifies anything.

set -eu

cd "${1:-.}"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
	echo "Not a git repository: $(pwd)" >&2
	exit 1
fi

section() {
	printf '\n===== %s =====\n' "$1"
}

section "STATUS"
git status --short --branch

section "STAGED DIFF"
if git diff --staged --quiet; then
	echo "(nothing staged)"
else
	git diff --staged --stat
	printf '\n'
	git diff --staged
fi

section "UNSTAGED DIFF (stat only)"
if git diff --quiet; then
	echo "(no unstaged changes)"
else
	git diff --stat
fi

section "UNTRACKED FILES"
untracked=$(git ls-files --others --exclude-standard)
if [ -z "$untracked" ]; then
	echo "(none)"
else
	echo "$untracked"
fi

section "RECENT COMMITS (house style)"
git log --oneline -20 2>/dev/null || echo "(no commits yet)"

section "COMMIT TEMPLATE"
template=$(git config --get commit.template 2>/dev/null || true)
if [ -n "$template" ]; then
	echo "commit.template = $template"
	[ -f "$template" ] && cat "$template"
else
	echo "(none configured)"
fi

section "COMMIT HOOKS"
hooks_dir=$(git rev-parse --git-path hooks)
found=0
for hook in commit-msg pre-commit prepare-commit-msg; do
	if [ -x "$hooks_dir/$hook" ]; then
		echo "$hook (active)"
		found=1
	fi
done
[ -f .pre-commit-config.yaml ] && { echo ".pre-commit-config.yaml present"; found=1; }
[ -f commitlint.config.js ] && { echo "commitlint.config.js present"; found=1; }
[ "$found" -eq 0 ] && echo "(none)"

exit 0
