# -*- coding: utf-8 -*-
"""Manual bump 0.26.0 -> 0.26.1 (inline python -c shreds quotes; file script only)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

p = ROOT / "pyproject.toml"
t = p.read_text(encoding="utf-8")
assert t.count('version = "0.26.0"') == 2, "unexpected pyproject version occurrences"
p.write_text(
    t.replace('version = "0.26.0"', 'version = "0.26.1"'),
    encoding="utf-8", newline="",
)

i = ROOT / "src" / "__init__.py"
t = i.read_text(encoding="utf-8")
assert '__version__ = "0.26.0"' in t, "src/__init__ version not found"
i.write_text(
    t.replace('__version__ = "0.26.0"', '__version__ = "0.26.1"'),
    encoding="utf-8", newline="",
)

c = ROOT / "CHANGELOG.md"
t = c.read_text(encoding="utf-8")
anchor = "## v0.26.0"
assert anchor in t, "changelog anchor missing"
section = (
    "## v0.26.1 (2026-11-28)\n\n### Fix\n\n"
    "- **status**: grouped vertical layout when the product table can not fit\n\n"
)
c.write_text(
    t.replace(anchor, section + anchor, 1), encoding="utf-8", newline="",
)
print("pyproject / src/__init__ / CHANGELOG bumped to 0.26.1")
