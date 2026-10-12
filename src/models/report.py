"""Typed shapes of the static security-audit report."""

from __future__ import annotations

from typing import TypedDict


class _FindingCore(TypedDict):
    """Keys every audit finding carries."""

    severity: str  # critical | high | medium | low | info
    category: str
    file: str
    line: int | None
    pattern: str
    message: str


class Finding(_FindingCore, total=False):
    """One static-audit hit.

    ``dev_context`` is set only on findings raised from a development / test
    path (see ``services.audit._is_dev_context``): those keep their message
    but get a down-weighted severity, so benign dev tooling cannot sink a
    skill's score. The key is optional (``total=False`` applies to the keys
    declared here, not the inherited ones) so all other construction sites
    stay plain six-key dicts.
    """

    dev_context: bool


class SkillReport(TypedDict):
    skill: str
    path: str
    files: int
    total_bytes: int
    score: int
    grade: str  # A | B | C | D | F
    verdict: str  # safe | caution | risky | dangerous
    summary: dict  # {critical, high, medium, low, info}
    findings: list[Finding]


class StatusEntry(TypedDict):
    skill_name: str
    product_short: str
    product_name: str
    status: str  # ok | missing | manual | n/a
    method: str  # symlink | junction | copy | native | pack
