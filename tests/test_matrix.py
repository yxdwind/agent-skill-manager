"""Cross-product consistency regression tests (v0.13.0, docs/product-matrix.md).

Locks the guarantees the capability matrix audit promised:

- every product declaration is complete and internally consistent
- sync/status produce an entry for EVERY product, with no silent skips
- shared skill dirs are synced once and reported, not duplicated
- differing real directories are protected from sync (conflict, not clobber)
- per-product frontmatter requirements are surfaced (QwenWork)
- ``adopt all`` works on the verbose path the CLI actually uses (A7 crash)
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from agent_skill_manager.config.products import PRODUCTS
from agent_skill_manager.services import sync as core
from agent_skill_manager.services.spec import product_frontmatter_issues

# declarative facts the docs promise (docs/product-matrix.md §1)
EXPECTED_TOTAL = 15
NO_LINUX = {
    "workbuddy", "trae", "traecn", "traesolo",
    "qodercn", "qodercnide", "qwenwork", "doubaowork",
}
SHARED_PAIRS = [("traesolo", "traecn"), ("qodercnide", "qodercn")]
SETTINGS_PRODUCTS = {"workbuddy", "codebuddy"}
QWENWORK_FIELDS = ["name", "version", "description", "description_zh"]


def _short(p):
    return p["short"]


def _by_short(short):
    return next(p for p in PRODUCTS if p["short"] == short)


# ------------------------------------------------------- declarations

class TestDeclarations:
    def test_fifteen_products(self):
        assert len(PRODUCTS) == EXPECTED_TOTAL

    def test_shorts_unique(self):
        shorts = [_short(p) for p in PRODUCTS]
        assert len(shorts) == len(set(shorts))

    def test_symlink_products_have_macos_and_windows(self):
        for p in PRODUCTS:
            if p["sync_method"] == "symlink":
                assert p["macos_path"], f"{p['short']} missing macos_path"
                assert p["windows_path"], f"{p['short']} missing windows_path"

    def test_no_linux_build_set_matches_docs(self):
        none_linux = {_short(p) for p in PRODUCTS if p.get("linux_path") is None}
        # pack-mode DuMate has no paths at all; exclude it from the symlink gap set
        symlink_no_linux = {
            _short(p) for p in PRODUCTS
            if p["sync_method"] == "symlink" and p.get("linux_path") is None
        }
        assert symlink_no_linux == NO_LINUX
        assert "dumate" in none_linux  # pack mode: no paths anywhere

    def test_shared_dir_declarations(self):
        for secondary, primary in SHARED_PAIRS:
            sec, pri = _by_short(secondary), _by_short(primary)
            assert sec.get("shares_dir_with") == primary
            for platform in ("macos", "windows", "linux"):
                assert sec.get(f"{platform}_path") == pri.get(f"{platform}_path"), (
                    f"{secondary} and {primary} must share {platform}_path"
                )

    def test_settings_mode_on_settings_products(self):
        for p in PRODUCTS:
            if _short(p) in SETTINGS_PRODUCTS:
                assert p.get("settings_file"), f"{p['short']} missing settings_file"
                assert p.get("settings_mode") == "skills-switch"
            else:
                assert not p.get("settings_file"), (
                    f"{p['short']} has settings_file but no declared settings mode"
                )

    def test_required_frontmatter_only_qwenwork(self):
        declaring = {p["short"]: p["required_frontmatter"] for p in PRODUCTS
                     if p.get("required_frontmatter")}
        assert declaring == {"qwenwork": QWENWORK_FIELDS}


# ------------------------------------------------------- sync contract

def _mk_skill(central: Path, name: str = "demo-skill") -> Path:
    d = central / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: demo-skill\ndescription: demo\n---\n")
    return d


def _fake(short, primary, method="symlink", extra=None, settings=None, shared=None):
    p = {
        "name": short.title(), "short": short,
        "macos_path": primary, "windows_path": primary, "linux_path": primary,
        "sync_method": method, "note": "",
        "extra_dirs_macos": extra or [], "extra_dirs_windows": extra or [],
        "extra_dirs_linux": extra or [],
    }
    if settings:
        p["settings_file"] = settings
        p["settings_mode"] = "skills-switch"
    if shared:
        p["shares_dir_with"] = shared
    return p


class TestSyncCoversEveryProduct:
    """No silent skips: every product yields exactly one result tuple."""

    def _run(self, tmp_path, products, force=False):
        central = tmp_path / "central"
        central.mkdir()
        _mk_skill(central)
        with patch.object(core, "CENTRAL_DIR", central), \
             patch.object(core, "PRODUCTS", products):
            return core.sync_skill("demo-skill", verbose=False, force=force)

    def test_every_product_gets_a_result(self, tmp_path):
        d = tmp_path / "d"; d.mkdir()
        products = [
            _fake("native-prod", d, method="native"),
            _fake("pack-prod", None, method="pack"),
            _fake("linked-prod", tmp_path / "l1"),
            _fake("nopath-prod", None),           # e.g. no linux build
        ]
        results = self._run(tmp_path, products)["demo-skill"]
        assert {s for s, ok, m in results} == {_short(p) for p in products}

    def test_methods_use_known_vocabulary(self, tmp_path):
        d = tmp_path / "d"; d.mkdir()
        products = [
            _fake("native-prod", d, method="native"),
            _fake("pack-prod", None, method="pack"),
            _fake("linked-prod", tmp_path / "l1"),
            _fake("nopath-prod", None),
        ]
        results = dict((s, (ok, m)) for s, ok, m in self._run(tmp_path, products)["demo-skill"])
        assert results["native-prod"][1] == "native"
        assert results["pack-prod"][1] == "pack"
        assert results["linked-prod"][1] in ("junction", "symlink", "copy")
        assert results["nopath-prod"][1] == "n/a"

    def test_shared_dir_synced_once(self, tmp_path):
        shared_target = tmp_path / "shared"
        products = [
            _fake("primary-prod", shared_target),
            _fake("shadow-prod", shared_target, shared="primary-prod"),
        ]
        results = self._run(tmp_path, products)["demo-skill"]
        by_short = {s: (ok, m) for s, ok, m in results}
        assert by_short["shadow-prod"] == (True, "shared->primary-prod")
        assert (shared_target / "demo-skill").exists()   # created exactly once

    def test_conflicting_real_dir_protected(self, tmp_path):
        target = tmp_path / "prod"
        target.mkdir()
        user_dir = target / "demo-skill"
        user_dir.mkdir()
        (user_dir / "local-edit.md").write_text("user work")

        products = [_fake("prod", target)]
        results = self._run(tmp_path, products)["demo-skill"]
        assert results == [("prod", False, "conflict")]
        assert (user_dir / "local-edit.md").exists()     # user data intact

    def test_force_overrides_conflict(self, tmp_path):
        target = tmp_path / "prod"
        target.mkdir()
        user_dir = target / "demo-skill"
        user_dir.mkdir()
        (user_dir / "local-edit.md").write_text("user work")

        products = [_fake("prod", target)]
        results = self._run(tmp_path, products, force=True)["demo-skill"]
        assert results[0][1] is True
        assert results[0][2] in ("junction", "symlink", "copy")
        assert not (user_dir / "local-edit.md").exists()

    def test_settings_not_written_for_uninstalled_product(self, tmp_path):
        """A9: no settings.json litter for products absent from the machine."""
        target = tmp_path / "prod"           # product root does not exist
        settings = tmp_path / "prod-root" / "settings.json"
        products = [_fake("prod", target, settings=settings)]
        self._run(tmp_path, products)
        assert not settings.exists()

    def test_settings_written_for_installed_product(self, tmp_path):
        target = tmp_path / "prod"
        target.mkdir()                        # installed: product root exists
        settings = tmp_path / "prod-root" / "settings.json"
        settings.parent.mkdir()
        products = [_fake("prod", target, settings=settings)]
        self._run(tmp_path, products)
        data = json.loads(settings.read_text(encoding="utf-8"))
        assert data["skills"]["demo-skill"] is True


# ------------------------------------------------------- status contract

class TestStatusContract:
    def test_every_product_listed_with_known_status(self, tmp_path):
        central = tmp_path / "central"
        central.mkdir()
        _mk_skill(central)
        d = tmp_path / "linked"; d.mkdir()
        products = [
            _fake("native-prod", d, method="native"),
            _fake("pack-prod", None, method="pack"),
            _fake("linked-prod", d),
            _fake("shadow-prod", d, shared="linked-prod"),
            _fake("nopath-prod", None),
        ]
        with patch.object(core, "CENTRAL_DIR", central), \
             patch.object(core, "PRODUCTS", products):
            entries = core.get_status("demo-skill")

        by_short = {e["product_short"]: e["status"] for e in entries}
        assert set(by_short) == {_short(p) for p in products}
        known = {"ok", "missing", "manual", "packed", "stale", "n/a"}
        assert all(s in known for s in by_short.values())
        assert by_short["native-prod"] == "ok"
        assert by_short["pack-prod"] == "manual"
        assert by_short["nopath-prod"] == "n/a"
        # shadow shares the dir -> same verdict as primary, no second lookup
        assert by_short["shadow-prod"] == by_short["linked-prod"] == "missing"

    def test_pack_status_transitions(self, tmp_path):
        central = tmp_path / "central"
        central.mkdir()
        skill = _mk_skill(central)
        with patch.object(core, "CENTRAL_DIR", central):
            assert core._pack_status(skill) == "manual"

            zip_path = central / "demo-skill.zip"
            zip_path.write_bytes(b"zip")
            assert core._pack_status(skill) == "packed"

            time.sleep(0.01)
            (skill / "SKILL.md").write_text("---\nname: demo-skill\ndescription: changed\n---\n")
            assert core._pack_status(skill) == "stale"


# ------------------------------------------------------- frontmatter (A4)

class TestProductFrontmatter:
    def test_missing_qwenwork_fields_flagged(self, tmp_path):
        d = tmp_path / "demo-skill"
        d.mkdir()
        (d / "SKILL.md").write_text(
            "---\nname: demo-skill\ndescription: demo\n---\n"
        )
        issues = product_frontmatter_issues(d)
        assert any("qwenwork" in i and "version" in i and "description_zh" in i
                   for i in issues)

    def test_complete_skill_passes(self, tmp_path):
        d = tmp_path / "demo-skill"
        d.mkdir()
        # encoding="utf-8" is mandatory on Windows (default cp1252 can't
        # encode 演示); harmless everywhere else.
        (d / "SKILL.md").write_text(
            "---\nname: demo-skill\nversion: 1.0.0\n"
            "description: demo\ndescription_zh: 演示\n---\n",
            encoding="utf-8",
        )
        assert product_frontmatter_issues(d) == []


# ------------------------------------------------------- adopt all (A7)

class TestAdoptAllVerbosePath:
    def test_adopt_all_does_not_crash_with_skills_found(self, tmp_path):
        """Regression: the CLI runs verbose=True; a stale duplicate block
        dereferenced product=None there (TypeError)."""
        central = tmp_path / "central"
        central.mkdir()
        prod_dir = tmp_path / "prod-skills"
        prod_dir.mkdir()
        _mk_skill_central_style(prod_dir, "found-skill")
        products = [_fake("prod", prod_dir)]
        with patch.object(core, "CENTRAL_DIR", central), \
             patch.object(core, "PRODUCTS", products), \
             patch.object(core, "get_product_path", return_value=prod_dir), \
             patch.object(core, "_is_junction", return_value=False):
            result = core.adopt_from_platform("all", verbose=True)
        assert {name for name, ok, _ in result["adopted"]} == {"found-skill"}


def _mk_skill_central_style(parent: Path, name: str) -> Path:
    d = parent / name
    d.mkdir()
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n---\n")
    return d


# ------------------------------------------------------- cli surface (A1)

class TestUsageSurface:
    def test_usage_lists_every_product(self):
        from agent_skill_manager.controllers.cli import USAGE
        for p in PRODUCTS:
            assert p["name"] in USAGE, f"USAGE missing {p['name']}"
