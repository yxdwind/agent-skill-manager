"""Tests for drift detection (v0.16.0) and the exit-code contract."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from agent_skill_manager.services.drift import find_drift
from agent_skill_manager.services.scaffold import create_skill


def _central_skill(central: Path, name: str = "demo-skill") -> None:
    r = create_skill(name, central_dir=central)
    assert r["created"], r["error"]


def _real_dir(parent: Path, name: str, marker: str = "v1") -> Path:
    d = parent / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: x\n---\nbody {marker}\n", encoding="utf-8"
    )
    return d


def _linked_dir(parent: Path, target: Path, name: str) -> None:
    """Create a directory junction (Windows) / symlink (POSIX)."""
    parent.mkdir(parents=True, exist_ok=True)
    link = parent / name
    if hasattr(__import__("os"), "symlink"):
        import os
        import platform
        if platform.system() == "Windows":
            subprocess_run(["cmd", "/c", "mklink", "/J", str(link), str(target)])
        else:
            os.symlink(str(target), str(link))


def subprocess_run(args):
    import subprocess
    # mklink prints localized (GBK on zh-CN Windows) text - never let
    # output decoding crash the helper; only the return code matters
    r = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr


def _fake(short, primary, method="symlink"):
    return {
        "name": short.title(), "short": short,
        "macos_path": primary, "windows_path": primary, "linux_path": primary,
        "sync_method": method, "note": "",
        "extra_dirs_macos": [], "extra_dirs_windows": [], "extra_dirs_linux": [],
    }


class TestFindDrift:
    def test_new_differs_and_clean(self, tmp_path):
        central = tmp_path / "central"
        _central_skill(central, "linked-skill")
        _central_skill(central, "edited-skill")

        prod = tmp_path / "prod-skills"
        _linked_dir(prod, central / "linked-skill", "linked-skill")  # link: no drift
        _real_dir(prod, "edited-skill", marker="product-edit")       # differs
        _real_dir(prod, "fresh-skill")                               # new

        products = [_fake("prod", prod)]
        with patch("agent_skill_manager.services.drift.CENTRAL_DIR", central), \
             patch("agent_skill_manager.services.drift.PRODUCTS", products):
            r = find_drift()

        entry = r["products"]["prod"]
        assert entry["new"] == ["fresh-skill"]
        assert entry["differs"] == ["edited-skill"]
        assert "linked-skill" not in entry["new"] + entry["differs"]

    def test_identical_real_dir_is_not_drift(self, tmp_path):
        """A real dir whose content matches central is a stale copy-back
        candidate, not drift - sync already reproduces it."""
        central = tmp_path / "central"
        _central_skill(central, "same-skill")
        prod = tmp_path / "prod-skills"
        shutil.copytree(central / "same-skill", prod / "same-skill")  # identical
        products = [_fake("prod", prod)]
        with patch("agent_skill_manager.services.drift.CENTRAL_DIR", central), \
             patch("agent_skill_manager.services.drift.PRODUCTS", products):
            r = find_drift()
        assert r["products"]["prod"] == {"new": [], "differs": []}

    def test_single_product_scope_and_unknown(self, tmp_path):
        central = tmp_path / "central"; central.mkdir()
        a, b = _fake("prod-a", tmp_path / "a"), _fake("prod-b", tmp_path / "b")
        (tmp_path / "b").mkdir()
        _real_dir(tmp_path / "b", "only-in-b")
        with patch("agent_skill_manager.services.drift.CENTRAL_DIR", central), \
             patch("agent_skill_manager.services.drift.PRODUCTS", [a, b]):
            r = find_drift("prod-b")
        assert r["scanned"] == ["prod-b"]
        assert r["products"]["prod-b"]["new"] == ["only-in-b"]
        assert "prod-a" not in r["products"]

        r2 = find_drift("nope")
        assert r2["error"] and "nope" in r2["error"]

    def test_native_pack_and_missing_dirs_skipped(self, tmp_path):
        central = tmp_path / "central"; central.mkdir()
        products = [
            _fake("native-prod", tmp_path, method="native"),
            _fake("pack-prod", None, method="pack"),
            _fake("absent-prod", tmp_path / "does-not-exist"),
        ]
        with patch("agent_skill_manager.services.drift.CENTRAL_DIR", central), \
             patch("agent_skill_manager.services.drift.PRODUCTS", products):
            r = find_drift()
        assert r["scanned"] == []


class TestDriftCli:
    def test_human_output_and_json(self, tmp_path, capsys):
        from agent_skill_manager.controllers import cli
        central = tmp_path / "central"
        _central_skill(central, "edited-skill")
        prod = tmp_path / "prod-skills"
        _real_dir(prod, "edited-skill", marker="product-edit")
        _real_dir(prod, "fresh-skill")
        products = [_fake("prod", prod)]

        with patch("agent_skill_manager.services.drift.CENTRAL_DIR", central), \
             patch("agent_skill_manager.services.drift.PRODUCTS", products):
            cli.main(["drift", "prod", "--json"])
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["products"]["prod"]["new"] == ["fresh-skill"]

        with patch("agent_skill_manager.services.drift.CENTRAL_DIR", central), \
             patch("agent_skill_manager.services.drift.PRODUCTS", products):
            cli.main(["drift", "prod"])
        out = capsys.readouterr().out
        assert "fresh-skill" in out and "edited-skill" in out
        assert "askill adopt" in out

    def test_unknown_product_exits_1(self, capsys):
        from agent_skill_manager.controllers import cli
        with pytest.raises(SystemExit) as ei:
            cli.main(["drift", "bogus"])
        assert ei.value.code == 1


class TestExitCodeContract:
    """0 success / 1 operational failure / 2 usage error (v0.16.0)."""

    def test_verify_fail_exits_1(self, tmp_path):
        from agent_skill_manager.controllers import cli
        central = tmp_path / "central"; central.mkdir()
        d = central / "broken"
        d.mkdir()
        (d / "SKILL.md").write_text("---\nname: other\n---\n", encoding="utf-8")
        with patch("agent_skill_manager.controllers.cli.CENTRAL_DIR", central), \
             patch("agent_skill_manager.services.sync.CENTRAL_DIR", central), \
             pytest.raises(SystemExit) as ei:
            cli.main(["verify"])
        assert ei.value.code == 1

    def test_verify_pass_exits_0(self, tmp_path, capsys):
        from agent_skill_manager.controllers import cli
        central = tmp_path / "central"
        r = create_skill("ok-skill", central_dir=central)
        assert r["created"]
        with patch("agent_skill_manager.controllers.cli.CENTRAL_DIR", central), \
             patch("agent_skill_manager.services.sync.CENTRAL_DIR", central):
            cli.main(["verify"])  # no SystemExit -> exit 0
        assert "ready for the skills.sh ecosystem" in capsys.readouterr().out

    def test_pack_missing_skill_exits_1(self, tmp_path):
        from agent_skill_manager.controllers import cli
        central = tmp_path / "central"; central.mkdir()
        with patch("agent_skill_manager.services.sync.CENTRAL_DIR", central), \
             pytest.raises(SystemExit) as ei:
            cli.main(["pack", "ghost"])
        assert ei.value.code == 1

    def test_sync_named_skill_missing_exits_1(self, tmp_path):
        from agent_skill_manager.controllers import cli
        central = tmp_path / "central"; central.mkdir()
        with patch("agent_skill_manager.services.sync.CENTRAL_DIR", central), \
             pytest.raises(SystemExit) as ei:
            cli.main(["sync", "ghost"])
        assert ei.value.code == 1

    def test_adopt_unknown_platform_exits_1(self, capsys):
        from agent_skill_manager.controllers import cli
        with pytest.raises(SystemExit) as ei:
            cli.main(["adopt", "bogus-platform"])
        assert ei.value.code == 1

    def test_list_empty_exits_0(self, tmp_path):
        from agent_skill_manager.controllers import cli
        central = tmp_path / "central"; central.mkdir()
        with patch("agent_skill_manager.services.sync.CENTRAL_DIR", central), \
             patch("agent_skill_manager.controllers.cli.CENTRAL_DIR", central):
            cli.main(["list"])  # empty repo is success, not failure
