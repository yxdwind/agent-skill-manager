"""Real-Windows junction regression (P2-13).

Most sync/GC tests use mocks. These use actual ``mklink /J`` junctions so the
three Windows-only failure modes in the README are exercised for real:
junction creation, dead junctions, and the rule that real directories are
never treated as links. Collected automatically by the existing
``windows-latest`` job in .github/workflows/ci.yml; skipped elsewhere.

Creating a junction needs no admin rights, and the target must live on a
local volume (a non-existent drive letter fails with "Local volumes required").
"""

import platform
import subprocess
from pathlib import Path

import pytest
from agent_skill_manager.services.doctor import _scan_product_dir
from agent_skill_manager.utils.filesystem import is_symlink_or_junction

pytestmark = pytest.mark.skipif(
    platform.system() != "Windows", reason="Windows junction only",
)


def _mklink(link: Path, target: Path) -> None:
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_real_junction_is_detected_as_a_link(tmp_path):
    target = tmp_path / "central" / "alpha"
    target.mkdir(parents=True)
    pdir = tmp_path / "product"
    pdir.mkdir()
    _mklink(pdir / "alpha", target)
    link = pdir / "alpha"
    assert is_symlink_or_junction(link)
    assert link.exists()
    scan = _scan_product_dir(pdir, {"alpha"})
    assert scan["links"] == 1
    assert scan["broken_links"] == 0
    assert scan["real_dirs"] == 0


def test_dead_junction_is_named_by_doctor(tmp_path):
    # Target does not exist but stays on the local volume - this is the only
    # way to construct a dangling junction on Windows.
    missing = tmp_path / "deleted-skill"
    pdir = tmp_path / "product"
    pdir.mkdir()
    _mklink(pdir / "stale", missing)
    link = pdir / "stale"
    assert is_symlink_or_junction(link)
    assert not link.exists()
    scan = _scan_product_dir(pdir, set())
    assert scan["broken_links"] == 1
    assert scan["broken_names"] == ["stale"]


def test_real_directory_is_never_a_link_or_gc_candidate(tmp_path):
    pdir = tmp_path / "product"
    (pdir / "handmade").mkdir(parents=True)
    scan = _scan_product_dir(pdir, set())
    assert scan["links"] == 0
    assert scan["broken_links"] == 0
    assert scan["real_dirs"] == 1
    assert scan["fork_dirs"] == 0  # not a central skill name
