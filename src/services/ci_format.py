"""GitHub Actions annotation formatters (P1-8).

Pure functions: no filesystem or network access. The CLI gathers the reports
and prints the returned lines, so the existing human-readable output and the
0/1/2 exit-code contract stay untouched.

Workflow command syntax:
https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

__all__ = ["audit_annotations", "grades_failed", "parse_fail_on", "verify_annotations"]

VALID_GRADES = {"A", "B", "C", "D", "F"}


def _escape(value: Any) -> str:
    """Escape data for a workflow command (%, CR, LF are special)."""
    return (
        str(value)
        .replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
    )


def parse_fail_on(value: str | None) -> set[str]:
    """Parse ``--fail-on D,F`` into a grade set; raise ValueError on junk."""
    if not value:
        return set()
    grades = {part.strip().upper() for part in re.split(r"[,\s]+", value) if part.strip()}
    bad = grades - VALID_GRADES
    if bad:
        raise ValueError(
            f"invalid grade(s): {', '.join(sorted(bad))} "
            f"(expected any of {', '.join(sorted(VALID_GRADES))})"
        )
    return grades


def grades_failed(reports: Iterable[Mapping[str, Any]], fail_on: set[str]) -> list[str]:
    """Skill names whose audit grade is in ``fail_on`` (stable order)."""
    return sorted(r["skill"] for r in reports if r.get("grade") in fail_on)


def verify_annotations(
    results: list[dict],
    product_issues: list[tuple[str, list[str]]],
    *,
    central: Path,
) -> list[str]:
    """Emit one annotation per spec error / warning / frontmatter gap."""
    lines: list[str] = []
    for r in results:
        path = central / r["skill"] / "SKILL.md"
        for error in r.get("errors", []):
            lines.append(f"::error file={_escape(path)},line=1::{_escape(error)}")
        for warning in r.get("warnings", []):
            lines.append(f"::warning file={_escape(path)},line=1::{_escape(warning)}")
    for name, issues in product_issues:
        path = central / name / "SKILL.md"
        for issue in issues:
            lines.append(f"::warning file={_escape(path)},line=1::{_escape(issue)}")
    return lines


def audit_annotations(
    reports: Iterable[Mapping[str, Any]],
    *,
    fail_on: set[str] | None = None,
) -> list[str]:
    """Emit annotations for high-severity findings and failed grade gates."""
    failed = set(grades_failed(reports, fail_on or set()))
    lines: list[str] = []
    for report in reports:
        root = str(report.get("path") or report.get("skill", ""))
        for finding in report.get("findings", []):
            severity = finding.get("severity")
            if severity not in {"critical", "high"}:
                continue
            file = f"{root}/{finding.get('file', 'SKILL.md')}"
            line = finding.get("line") or 1
            lines.append(
                f"::error file={_escape(file)},line={_escape(line)}::"
                f"{_escape(finding.get('message', ''))}"
            )
        if report["skill"] in failed:
            file = f"{root}/SKILL.md"
            lines.append(
                f"::error file={_escape(file)},line=1::"
                f"audit grade {report['grade']} ({report.get('verdict', '')}) "
                f"is in --fail-on"
            )
    return lines
