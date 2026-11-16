"""Deterministic description-overlap audit (``askill audit --overlap``, P1-9).

Every installed skill's ``description`` sits in the agent's context whether
or not the skill is used. Two skills with near-identical descriptions both
cost tokens *and* make activation ambiguous. This module ranks such pairs.

It is deliberately **lexical, not semantic**: word tokens plus CJK character
bigrams, Jaccard similarity, stable sort. No embeddings, no LLM, no network,
no third-party dependency. Results are a triage hint, never a verdict.
"""

from __future__ import annotations

import re
from pathlib import Path

from .inventory import list_skills
from .spec import parse_frontmatter

__all__ = ["overlap_rows", "render_overlap"]

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "use",
    "used", "using", "when", "with", "you", "your", "skill", "skills",
    "agent", "agents", "should", "can", "help", "helps",
}

_WORD = re.compile(r"[a-z0-9][a-z0-9_-]{2,}")
_CJK = re.compile(r"[\u4e00-\u9fff]")


def _tokens(text: str) -> set[str]:
    """English word tokens + CJK character bigrams (no tokenizer dependency)."""
    lowered = text.lower()
    words = {w for w in _WORD.findall(lowered) if w not in STOPWORDS}
    chars = _CJK.findall(lowered)
    bigrams = {chars[i] + chars[i + 1] for i in range(len(chars) - 1)}
    return words | bigrams


def overlap_rows(central: Path, threshold: float = 0.6) -> list[dict]:
    """Return description-overlap pairs, sorted by score then name (stable).

    ``shared`` lists the common tokens so a human can judge whether the pair
    is a real duplicate or just shares domain vocabulary.
    """
    descriptions: dict[str, str] = {}
    for skill_dir in list_skills(central):
        try:
            text = (skill_dir / "SKILL.md").read_text(
                encoding="utf-8", errors="replace",
            )
            frontmatter, _ = parse_frontmatter(text)
        except OSError:
            continue
        desc = str(frontmatter.get("description") or "").strip()
        if desc:
            descriptions[skill_dir.name] = desc

    names = sorted(descriptions)
    tokens = {name: _tokens(descriptions[name]) for name in names}
    rows: list[dict] = []
    for i, first in enumerate(names):
        for second in names[i + 1:]:
            a, b = tokens[first], tokens[second]
            if not a or not b:
                continue
            shared = a & b
            score = len(shared) / len(a | b)
            if score < threshold:
                continue
            rows.append({
                "skill_a": first,
                "skill_b": second,
                "score": round(score, 3),
                "shared": sorted(shared)[:8],
                "suggestion": (
                    "likely duplicate - consider merging or removing one"
                    if score >= 0.85 else
                    "overlapping descriptions - differentiate or consolidate"
                ),
            })
    rows.sort(key=lambda r: (-r["score"], r["skill_a"], r["skill_b"]))
    return rows


def render_overlap(rows: list[dict], threshold: float) -> str:
    """Human-readable, bounded-width report."""
    lines = [
        f"askill audit --overlap - deterministic description overlap (Jaccard >= {threshold})",
        "",
        "Lexical similarity only (word tokens + CJK bigrams); verify each pair by reading the SKILL.md files. Not a semantic judgement.",
        "",
    ]
    if not rows:
        lines.append("  No description pairs above the threshold.")
        return "\n".join(lines) + "\n"
    lines += [
        f"  {len(rows)} pair(s) found:",
        "",
        f"  {'skill A':<26} {'skill B':<26} {'score':>6}  shared tokens",
        "  " + "-" * 78,
    ]
    for row in rows:
        shared = ", ".join(row["shared"][:5]) or "—"
        lines.append(
            f"  {row['skill_a'][:25]:<26} {row['skill_b'][:25]:<26} "
            f"{row['score']:>6.3f}  {shared}"
        )
        lines.append(f"      -> {row['suggestion']}")
    return "\n".join(lines) + "\n"
