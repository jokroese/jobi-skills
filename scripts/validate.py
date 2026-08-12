#!/usr/bin/env python3
"""Validate every SKILL.md in this repo against the Agent Skills format.

Checks the things that silently break a skill at runtime: unparseable
frontmatter, missing required fields, a name that disagrees with its
directory, references to files that do not exist, scripts without the
executable bit.

Warnings are advisory (they will not fail CI); errors will.

Usage:
    python3 scripts/validate.py [--strict]

    --strict    treat warnings as errors
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# Markdown links and bare backticked paths pointing at bundled resources.
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#:]+)\)")
BACKTICK_PATH_RE = re.compile(r"`((?:references|scripts|assets)/[\w./-]+)`")

DESCRIPTION_MIN = 40
DESCRIPTION_MAX = 1024
BODY_MAX_LINES = 500
REFERENCE_TOC_LINES = 300

errors: list[str] = []
warnings: list[str] = []


def error(skill: str, msg: str) -> None:
    errors.append(f"{skill}: {msg}")


def warn(skill: str, msg: str) -> None:
    warnings.append(f"{skill}: {msg}")


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter, body). Frontmatter is None if absent."""
    if not text.startswith("---"):
        return None, text
    parts = text.split("\n---", 2)
    if len(parts) < 2:
        return None, text
    fm = parts[0][3:]
    body = parts[1].lstrip("\n")
    return fm, body


def parse_frontmatter(fm: str) -> dict[str, str]:
    """Minimal YAML: flat `key: value` pairs, which is all the spec needs.

    Deliberately not importing PyYAML so this runs anywhere with a bare
    Python 3.
    """
    data: dict[str, str] = {}
    key = None
    for raw in fm.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[:1] in (" ", "\t") and key:
            data[key] += " " + raw.strip()
            continue
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        key = key.strip()
        value = value.strip()
        if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        data[key] = value
    return data


def check_skill(directory: Path) -> None:
    name = directory.name
    skill_md = directory / "SKILL.md"

    if not skill_md.is_file():
        error(name, "no SKILL.md")
        return

    text = skill_md.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)

    if fm is None:
        error(name, "SKILL.md has no YAML frontmatter (must open with ---)")
        return

    meta = parse_frontmatter(fm)

    # -- required fields -------------------------------------------------
    for field in ("name", "description"):
        if not meta.get(field):
            error(name, f"frontmatter missing required field '{field}'")

    declared = meta.get("name", "")
    if declared and declared != name:
        error(name, f"frontmatter name '{declared}' does not match directory")
    if declared and not NAME_RE.match(declared):
        error(name, f"name '{declared}' must be lowercase and hyphenated")

    desc = meta.get("description", "")
    if desc:
        if len(desc) > DESCRIPTION_MAX:
            error(
                name,
                f"description is {len(desc)} chars, over the {DESCRIPTION_MAX} limit",
            )
        elif len(desc) < DESCRIPTION_MIN:
            warn(
                name,
                f"description is only {len(desc)} chars — likely too vague to trigger reliably",
            )
        if not re.search(r"\b(use|when|whenever|trigger|ask)\b", desc, re.I):
            warn(
                name,
                "description does not say when to use the skill, which is what drives triggering",
            )

    # -- body ------------------------------------------------------------
    body_lines = body.splitlines()
    if len(body_lines) > BODY_MAX_LINES:
        warn(
            name,
            f"SKILL.md body is {len(body_lines)} lines — move detail into references/",
        )
    if not body.strip():
        error(name, "SKILL.md has no body")

    # -- referenced files exist ------------------------------------------
    referenced = set(LINK_RE.findall(body)) | set(BACKTICK_PATH_RE.findall(body))
    for ref in referenced:
        ref = ref.strip()
        if ref.startswith(("http://", "https://", "mailto:", "#", "/")):
            continue
        if not (directory / ref).exists():
            error(name, f"references '{ref}' which does not exist")

    # -- bundled resources -----------------------------------------------
    for script in (directory / "scripts").glob("*"):
        if script.suffix in (".sh", ".py") and not os.access(script, os.X_OK):
            warn(name, f"scripts/{script.name} is not executable (chmod +x)")

    for ref_file in (directory / "references").glob("*.md"):
        content = ref_file.read_text(encoding="utf-8")
        if len(content.splitlines()) > REFERENCE_TOC_LINES:
            if not re.search(
                r"^##+ (contents|table of contents)", content, re.I | re.M
            ):
                warn(
                    name,
                    f"references/{ref_file.name} is long and has no table of contents",
                )

    for unexpected in directory.iterdir():
        if unexpected.name in ("SKILL.md", "references", "scripts", "assets", "evals"):
            continue
        if unexpected.name.startswith("."):
            continue
        warn(
            name,
            f"unexpected entry '{unexpected.name}' — agents only read the standard directories",
        )


def main() -> int:
    strict = "--strict" in sys.argv

    if not SKILLS.is_dir():
        print(f"error: no skills/ directory at {SKILLS}", file=sys.stderr)
        return 1

    directories = sorted(
        d for d in SKILLS.iterdir() if d.is_dir() and not d.name.startswith(".")
    )
    if not directories:
        print(f"error: no skills found in {SKILLS}", file=sys.stderr)
        return 1

    for directory in directories:
        check_skill(directory)

    for w in warnings:
        print(f"warning  {w}")
    for e in errors:
        print(f"error    {e}")

    checked = f"Checked {len(directories)} skill(s)"
    if errors:
        print(f"\n{checked}: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    if warnings and strict:
        print(f"\n{checked}: {len(warnings)} warning(s), failing because --strict")
        return 1
    print(f"\n{checked}: OK" + (f" ({len(warnings)} warning(s))" if warnings else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
