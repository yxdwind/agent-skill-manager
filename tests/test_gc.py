"""Tests for sync --gc (dead link removal) and doctor's broken-link naming."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import agent_skill_manager.services.doctor as doctor_mod
import agent_skill_manager.services.sync as sync_pkg
from agent_skill_manager.services.doctor import doctor_report
from agent_skill_manager.services.sync.engine import gc_dead_links
from agent_skill_manager.utils.filesystem import is_symlink_or_junction


def _prod(short, pdir):
    return {"name": short.title(), "short": short, "sync_method": "symlink",
            "windows_path": str(pdir), "macos_path": str(pdir), "linux_path": str(pdir)}


def _mk_skill(central, name):
    d = central / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: d\n---\nbody", encoding="utf-8")


def _dead_junction(dst: Path) -> bool:
    """Create a junction whose local-volume target does not exist.

    mklink /J only requires a LOCAL volume (it does not validate target
    existence), so a guaranteed-missing path on C: works everywhere.
    """
    r = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(dst), r"C:\__askill_missing__\nope"],
        capture_output=True, text=True,
    )
    return r.returncode == 0 and is_symlink_or_junction(dst)


def test_gc_removes_stale_keeps_relinkable_and_real_dirs(tmp_path):
    central = tmp_path / "central"
    _mk_skill(central, "s1")
    _mk_skill(central, "s2")
    pdir = tmp_path / "prodA"
    pdir.mkdir()

    # stale: dead link whose name is NOT a central skill -> removed
    assert _dead_junction(pdir / "old-probe")
    # dead but relinkable: name matches a central skill -> sync fixes it, gc keeps
    assert _dead_junction(pdir / "s1")
    # live link: junction to an existing central skill dir -> untouched
    r = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(pdir / "s2-live"), str(central / "s2")],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    # real dir: never touched by gc
    (pdir / "manual-dir").mkdir()

    with patch.object(sync_pkg, "CENTRAL_DIR", central), \
         patch.object(sync_pkg, "PRODUCTS", [_prod("proda", pdir)]):
        removed = gc_dead_links(verbose=False)

    assert removed == {"proda": ["old-probe"]}
    assert not (pdir / "old-probe").exists()
    assert is_symlink_or_junction(pdir / "s1")          # kept for sync to relink
    assert is_symlink_or_junction(pdir / "s2-live")     # live link untouched
    assert (pdir / "manual-dir").is_dir()               # real dir untouched


def test_gc_skips_missing_product_dirs(tmp_path):
    central = tmp_path / "central"
    _mk_skill(central, "s1")
    with patch.object(sync_pkg, "CENTRAL_DIR", central), \
         patch.object(sync_pkg, "PRODUCTS", [_prod("gone", tmp_path / "nope")]):
        assert gc_dead_links(verbose=False) == {}


def test_gc_reports_names_in_verbose_mode(tmp_path, capsys):
    central = tmp_path / "central"
    _mk_skill(central, "s1")
    pdir = tmp_path / "prodA"
    pdir.mkdir()
    assert _dead_junction(pdir / "stale-thing")
    with patch.object(sync_pkg, "CENTRAL_DIR", central), \
         patch.object(sync_pkg, "PRODUCTS", [_prod("proda", pdir)]):
        gc_dead_links(verbose=True)
    out = capsys.readouterr().out
    assert "stale-thing" in out and "proda" in out


def test_doctor_scan_names_broken_links(tmp_path):
    central = tmp_path / "central"
    _mk_skill(central, "s1")
    pdir = tmp_path / "prodA"
    pdir.mkdir()
    assert _dead_junction(pdir / "dead-one")
    scan = doctor_mod._scan_product_dir(pdir, {"s1"})
    assert scan["broken_links"] == 1
    assert scan["broken_names"] == ["dead-one"]


def test_doctor_human_output_names_dead_links(tmp_path, capsys):
    central = tmp_path / "central"
    _mk_skill(central, "s1")
    pdir = tmp_path / "prodA"
    pdir.mkdir()
    assert _dead_junction(pdir / "dead-one")
    with patch.object(doctor_mod, "PRODUCTS", [_prod("proda", pdir)]), \
         patch.object(doctor_mod, "_configured_proxies", list):
        report = doctor_report(central=central, verbose=True)
    out = capsys.readouterr().out
    assert "dead-one" in out
    detail = next(c["detail"] for c in report["checks"] if c["id"] == "broken-links")
    assert "sync --gc" in detail and "askill sync" in detail
