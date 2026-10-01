"""Agent Skills specification (agentskills.io) compliance checks (v0.11.0).

``askill verify [skill]`` validates skills in the central repository
against the published Agent Skills specification so they can be indexed by
skills.sh and read by every spec-compliant agent.

Stdlib only: a tiny frontmatter parser covering the flat ``key: value``
layout the spec uses (nested ``metadata:`` maps and lists are skipped
without error).
"""
from __future__ import annotations

import re
from pathlib import Path

from .sync import list_skills

# Spec constraints (https://agentskills.io/specification)
NAME_MAX = 64
DESC_MAX = 1024
COMPAT_MAX = 500
BODY_LINES_SOFT = 500     # recommendation, not a hard rule -> warning

# lowercase letters/digits, single hyphens between segments; the regex
# rejects uppercase, leading/trailing hyphens and consecutive hyphens.
_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_frontmatter(text: str) -> tuple[dict, list[str]]:
    """Extract flat ``key: value`` pairs from the YAML frontmatter block.

    Returns (fields, warnings).  Nested maps (``metadata:`` children) and
    list items are ignored - they are legal in the spec but irrelevant to
    the checks below.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, ["SKILL.md does not start with a '---' frontmatter block"]

    fields: dict[str, str] = {}
    warnings: list[str] = []
    terminated = False
    for lineno, line in enumerate(lines[1:], start=2):
        stripped = line.strip()
        if stripped == "---":
            terminated = True
            break
        if not stripped or line[:1] in (" ", "\t") or stripped.startswith("- "):
            continue    # blank, nested map/list entry - skip quietly
        if ":" not in line:
            warnings.append(f"frontmatter line {lineno} has no ':' and was ignored")
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"').strip("'")

    if not terminated:
        warnings.append("frontmatter block is never closed with '---'")
    return fields, warnings


def check_spec(skill_dir: Path) -> dict:
    """Validate one skill directory against the Agent Skills spec.

    Returns ``{"skill", "ok", "errors", "warnings"}`` where ``ok`` is False
    only for spec violations (errors), never for advisory warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []
    skill_dir = Path(skill_dir)

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return {
            "skill": skill_dir.name, "ok": False,
            "errors": ["SKILL.md missing"], "warnings": [],
        }

    text = skill_md.read_text(encoding="utf-8", errors="replace")
    fields, fm_warnings = parse_frontmatter(text)
    warnings.extend(fm_warnings)

    name = fields.get("name")
    if not name:
        errors.append("frontmatter missing required 'name'")
    else:
        if len(name) > NAME_MAX:
            errors.append(f"'name' is {len(name)} chars (max {NAME_MAX})")
        if not _NAME_RE.match(name):
            errors.append(
                f"'name' {name!r} must be lowercase letters/digits with single "
                "hyphens between segments (no leading/trailing/double hyphens)"
            )
        if name != skill_dir.name:
            errors.append(
                f"'name' {name!r} does not match directory name {skill_dir.name!r}"
            )

    description = fields.get("description")
    if not description:
        errors.append("frontmatter missing required 'description'")
    elif len(description) > DESC_MAX:
        errors.append(f"'description' is {len(description)} chars (max {DESC_MAX})")

    compatibility = fields.get("compatibility")
    if compatibility and len(compatibility) > COMPAT_MAX:
        errors.append(f"'compatibility' is {len(compatibility)} chars (max {COMPAT_MAX})")

    # body size is a recommendation (progressive disclosure), advisory only
    terminated = text.split("\n")
    body_start = None
    for i, line in enumerate(terminated[1:], start=2):
        if line.strip() == "---":
            body_start = i
            break
    if body_start is not None:
        body_lines = len([l for l in terminated[body_start:] if l.strip()])
        if body_lines > BODY_LINES_SOFT:
            warnings.append(
                f"SKILL.md body has {body_lines} lines "
                f"({BODY_LINES_SOFT} recommended); consider moving detail "
                "into references/ files"
            )

    return {
        "skill": skill_dir.name,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def check_all_specs() -> list[dict]:
    """Validate every skill in the central repository."""
    return [check_spec(d) for d in list_skills()]


def product_frontmatter_issues(skill_dir: Path) -> list[str]:
    """Check a skill against products that mandate extra frontmatter fields.

    v0.13.0: per-product requirements are declared in products.py
    (``required_frontmatter``), e.g. QwenWork requires ``name``, ``version``,
    ``description`` and ``description_zh``.  Without this check users only
    find out when the product silently fails to load the skill.

    Returns:
        List of human-readable issues, e.g.
        ``"qwenwork: missing frontmatter field(s): version, description_zh"``.
        Empty list when every declaring product is satisfied.
    """
    from ..config.products import PRODUCTS

    skill_md = Path(skill_dir) / "SKILL.md"
    if not skill_md.is_file():
        return []
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    fields, _ = parse_frontmatter(text)

    issues: list[str] = []
    for p in PRODUCTS:
        required = p.get("required_frontmatter")
        if not required:
            continue
        missing = [f for f in required if not fields.get(f)]
        if missing:
            issues.append(
                f"{p['short']}: missing frontmatter field(s) "
                f"{', '.join(missing)} in SKILL.md"
            )
    return issues
