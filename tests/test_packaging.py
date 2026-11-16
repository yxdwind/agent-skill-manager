"""Guard against shipping an incomplete wheel (P2-11).

v0.20.0 was unusable for fresh installs because the hand-maintained
``[tool.setuptools] packages`` whitelist missed the new ``services.sync``
subpackage. Repo-local tests could not catch it - the package is importable
from the source tree either way.

Automatic discovery is NOT a drop-in fix here: with
``package-dir = {agent_skill_manager = "src"}``, ``find_packages(where="src")``
yields bare names (``config``, ``services``, ...), which would break every
``agent_skill_manager.*`` import. Instead this test locks the declaration to
the actual on-disk package set: add a subpackage without adding it to
pyproject and this test goes red.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
PYPROJECT = REPO / "pyproject.toml"


def declared_packages(pyproject: Path = PYPROJECT) -> set[str]:
    """Read the explicit whitelist without a TOML parser (Python 3.10 safe)."""
    text = pyproject.read_text(encoding="utf-8")
    block = re.search(
        r"^\[tool\.setuptools\]\s*\n(.*?)(?=^\[|\Z)", text, re.MULTILINE | re.DOTALL,
    )
    assert block, "missing [tool.setuptools] section"
    packages = re.search(r"^packages\s*=\s*\[(.*?)\]", block.group(1), re.MULTILINE | re.DOTALL)
    assert packages, "missing packages = [...] in [tool.setuptools]"
    return set(re.findall(r'"([^"]+)"', packages.group(1)))


def actual_packages(src: Path = SRC) -> set[str]:
    """Derive the ``agent_skill_manager.*`` names from real __init__.py files."""
    found: set[str] = set()
    for init in src.rglob("__init__.py"):
        rel = init.parent.relative_to(src)
        parts = [p for p in rel.parts if p != "."]
        if any(p.startswith(".") or "egg-info" in p for p in parts):
            continue
        # src/agent_skill_manager/completion is already named with the prefix;
        # every other directory needs it prepended (package-dir mapping).
        if parts and parts[0] == "agent_skill_manager":
            dotted = ".".join(parts)
        else:
            dotted = ".".join(["agent_skill_manager", *parts]) if parts else "agent_skill_manager"
        found.add(dotted)
    return found


def test_every_on_disk_package_is_declared():
    assert actual_packages() == declared_packages(), (
        "pyproject packages whitelist drifted from src/ - a new subpackage "
        "would be missing from the wheel (v0.20.0 regression)"
    )


def test_sync_and_completion_subpackages_are_present():
    """The two packages that caused / could cause real shipping bugs."""
    declared = declared_packages()
    assert "agent_skill_manager.services.sync" in declared
    assert "agent_skill_manager.completion" in declared
    assert "agent_skill_manager" in declared


def test_a_new_undeclared_subpackage_would_fail(tmp_path):
    """Simulate adding a subpackage without updating pyproject -> red."""
    fake_src = tmp_path / "src"
    (fake_src / "brand_new").mkdir(parents=True)
    (fake_src / "brand_new" / "__init__.py").write_text("", encoding="utf-8")
    (fake_src / "__init__.py").write_text("", encoding="utf-8")
    fake_pyproject = tmp_path / "pyproject.toml"
    fake_pyproject.write_text(
        '[tool.setuptools]\npackages = [\n    "agent_skill_manager",\n]\n',
        encoding="utf-8",
    )
    assert actual_packages(fake_src) - declared_packages(fake_pyproject) == {
        "agent_skill_manager.brand_new",
    }
