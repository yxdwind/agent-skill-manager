# -*- coding: utf-8 -*-
"""Manual bump 0.26.1 -> 0.26.2 (watch backend correctness fix)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

p = ROOT / "pyproject.toml"
t = p.read_text(encoding="utf-8")
assert t.count('version = "0.26.1"') == 2, "unexpected pyproject version occurrences"
p.write_text(
    t.replace('version = "0.26.1"', 'version = "0.26.2"'),
    encoding="utf-8", newline="",
)

i = ROOT / "src" / "__init__.py"
t = i.read_text(encoding="utf-8")
assert '__version__ = "0.26.1"' in t, "src/__init__ version not found"
i.write_text(
    t.replace('__version__ = "0.26.1"', '__version__ = "0.26.2"'),
    encoding="utf-8", newline="",
)

c = ROOT / "CHANGELOG.md"
t = c.read_text(encoding="utf-8")
anchor = "## v0.26.1 (2026-11-28)"
assert anchor in t, "changelog anchor missing"
section = (
    "## v0.26.2 (2026-11-28)\n\n### Fix\n\n"
    "- **watch**: rewrite the Windows backend as OVERLAPPED ReadDirectoryChangesW - "
    "events were lost in the startup window and inside the debounce absorb "
    "(stress loop: 11/60 lost -> 0/60)\n\n"
)
c.write_text(
    t.replace(anchor, section + anchor, 1), encoding="utf-8", newline="",
)
print("bumped to 0.26.2")
