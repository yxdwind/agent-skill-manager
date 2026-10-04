"""Skill scaffolding for ``askill new`` (v0.15.0, docs/v0.15.0-plan.md R1).

Creates a spec-compliant skill skeleton in the central repository.  The
SKILL.md frontmatter is generated from the declarative product registry
(``products.py`` → ``required_frontmatter``), so scaffolding automatically
tracks per-product requirements: declare a new field on a product and the
scaffold picks it up without any change here.
"""
from __future__ import annotations

from pathlib import Path

from ..config.products import CENTRAL_DIR, PRODUCTS
from .spec import _NAME_RE, NAME_MAX, check_spec, product_frontmatter_issues

_DESC_PLACEHOLDER = "(TODO) One line: what does {name} do and when should the agent use it?"
_DESC_ZH_PLACEHOLDER = "（TODO）一句话说明 {name} 的用途与适用场景。"  # noqa: RUF001 - intentional Chinese fullwidth punctuation

_BODY_TEMPLATE = """\


# {name}

{description}

## What it does

(TODO) Describe when the agent should load this skill and what problem it solves.

## How to use

(TODO) Step-by-step instructions the agent should follow.

## Files

- `references/` - detailed documentation, loaded on demand (keeps SKILL.md
  under the ~500-line progressive-disclosure recommendation)
- `scripts/` - optional helper scripts. The security audit scans every file
  here: avoid `curl | sh`, hardcoded secrets and prompt-injection phrasing.
"""

_REFERENCES_README = """\
# references/

(TODO) Move detailed documentation here - reference files the agent reads
on demand. Keeping SKILL.md lean (~500 lines max) follows the progressive
disclosure recommendation of the Agent Skills spec.
"""


def validate_skill_name(name: str) -> str | None:
    """Return an error message for an invalid skill name, else None.

    Mirrors the agentskills.io rules that ``askill verify`` enforces, so a
    name accepted here is never rejected there.
    """
    if not name:
        return "Skill name must not be empty."
    if len(name) > NAME_MAX:
        return f"Skill name is {len(name)} chars (max {NAME_MAX})."
    if not _NAME_RE.match(name):
        return (
            f"Skill name {name!r} must be lowercase letters/digits with "
            "single hyphens between segments (no leading/trailing/double hyphens)."
        )
    return None


def collect_required_frontmatter(
    targets: list[str] | None,
) -> tuple[list[str], str | None]:
    """Union of extra frontmatter fields declared by the given targets.

    ``targets=None`` means every declaring product (superset - the default
    so a scaffold loads in any product without edits). ``targets=[]`` means
    explicitly no product requirements (base spec fields only). The raw
    declaration order is preserved; note a product may declare ``name`` or
    ``description`` (e.g. QwenWork documents all four fields) -
    :func:`create_skill` skips those because the base frontmatter always
    provides them.

    Returns:
        (fields, error) - error names an unknown target short, if any.
    """
    if targets is not None:
        known = sorted(p["short"] for p in PRODUCTS)
        unknown = [t for t in targets if t not in known]
        if unknown:
            return [], (
                f"Unknown product short(s): {', '.join(unknown)} "
                f"(available: {', '.join(known)})"
            )
    fields: list[str] = []
    for p in PRODUCTS:
        if targets is not None and p["short"] not in targets:
            continue
        for f in p.get("required_frontmatter", []):
            if f not in fields:
                fields.append(f)
    return fields, None


def create_skill(
    name: str,
    *,
    targets: list[str] | None = None,
    description: str | None = None,
    description_zh: str | None = None,
    version: str = "0.1.0",
    minimal: bool = False,
    central_dir: Path | None = None,
) -> dict:
    """Create a new skill skeleton in the central repository.

    Args:
        name: Skill name; must satisfy the agentskills.io name rules and
            match the directory name (verify enforces both).
        targets: Product shorts whose ``required_frontmatter`` to prefill.
            None = superset of all declaring products; [] = base fields only.
        description: Frontmatter description (TODO placeholder if omitted).
        description_zh: Chinese description (only written when some target
            requires it; TODO placeholder if omitted).
        version: Value for a required ``version`` field (default 0.1.0).
        minimal: Only SKILL.md, no references/ or scripts/ subdirs.
        central_dir: Override the central repository (tests); defaults to
            the module-level ``CENTRAL_DIR``.

    Returns:
        Report dict ``{"name", "path", "created", "error", "frontmatter",
        "spec", "product_issues"}``. On validation failure ``created`` is
        False and ``error`` explains why; nothing touches the filesystem.
    """
    report: dict = {
        "name": name, "path": None, "created": False, "error": None,
        "frontmatter": {}, "spec": None, "product_issues": [],
    }
    if err := validate_skill_name(name):
        report["error"] = err
        return report
    fields, err = collect_required_frontmatter(targets)
    if err:
        report["error"] = err
        return report

    central = Path(central_dir) if central_dir is not None else CENTRAL_DIR
    skill_dir = central / name
    report["path"] = str(skill_dir)
    if skill_dir.exists():
        report["error"] = (
            f"Skill already exists: {skill_dir} "
            f"(remove first with 'askill remove {name}', or pick another name)"
        )
        return report

    desc = description or _DESC_PLACEHOLDER.format(name=name)
    values: dict[str, str] = {
        "version": version,
        "description_zh": description_zh or _DESC_ZH_PLACEHOLDER.format(name=name),
    }
    fm: dict[str, str] = {"name": name, "description": desc}
    lines = ["---", f"name: {name}", f"description: {desc}"]
    for f in fields:
        if f in fm:
            # base frontmatter already covers it (e.g. QwenWork declares
            # name/description on top of the universal spec) - a duplicate
            # key would shadow the real value when the flat parser reads it
            continue
        value = values.get(f, "TODO")
        lines.append(f"{f}: {value}")
        fm[f] = value
    lines.append("---")
    if not minimal:
        lines.append(_BODY_TEMPLATE.format(name=name, description=desc))

    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not minimal:
        refs = skill_dir / "references"
        refs.mkdir()
        (refs / "README.md").write_text(_REFERENCES_README, encoding="utf-8")
        scripts = skill_dir / "scripts"
        scripts.mkdir()
        # keep the empty dir visible to git
        (scripts / ".gitkeep").write_text("", encoding="utf-8")

    report["created"] = True
    report["frontmatter"] = fm
    # prove compliance on the spot: the scaffold must pass verify untouched
    report["spec"] = check_spec(skill_dir)
    report["product_issues"] = product_frontmatter_issues(skill_dir)
    return report
