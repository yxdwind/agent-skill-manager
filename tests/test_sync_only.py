"""Tests for --only product targeting (sync/install) and rollback snapshots."""

import json
from unittest.mock import patch

import agent_skill_manager.services.sync as sync_pkg
from agent_skill_manager.services import sources as sources_mod
from agent_skill_manager.services.sync.engine import sync_skill
from agent_skill_manager.services.sync.install import install_skill

# ---------------------------------------------------------------- fixtures

def _fake_products():
    return [
        {"name": "Fake A", "short": "fa", "sync_method": "symlink",
         "windows_path": "X:/fa", "macos_path": "X:/fa", "linux_path": "X:/fa"},
        {"name": "Fake B", "short": "fb", "sync_method": "symlink",
         "windows_path": "X:/fb", "macos_path": "X:/fb", "linux_path": "X:/fb"},
    ]


def _mk_skill(central, name):
    d = central / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: d\n---\nbody", encoding="utf-8")


# ---------------------------------------------------------------- --only

def test_sync_only_targets_matching_products(tmp_path, capsys):
    central = tmp_path / "central"
    _mk_skill(central, "s1")
    called = []
    with patch.object(sync_pkg, "CENTRAL_DIR", central), \
         patch.object(sync_pkg, "PRODUCTS", _fake_products()), \
         patch.object(sync_pkg, "_sync_one_product",
                      side_effect=lambda skill_dir, p, *a, **k: called.append(p["short"]) or (p["short"], True, "ok")):
        results = sync_skill("s1", verbose=False, only=["fa"])
    assert called == ["fa"]
    assert list(results["s1"]) == [("fa", True, "ok")]


def test_sync_only_rejects_unknown_short(tmp_path, capsys):
    central = tmp_path / "central"
    _mk_skill(central, "s1")
    with patch.object(sync_pkg, "CENTRAL_DIR", central), \
         patch.object(sync_pkg, "PRODUCTS", _fake_products()):
        results = sync_skill("s1", verbose=True, only=["nope"])
    assert results == {}
    out = capsys.readouterr().out
    assert "nope" in out and "fa" in out and "fb" in out  # names the valid list


def test_sync_only_empty_result(tmp_path):
    central = tmp_path / "central"
    _mk_skill(central, "s1")
    with patch.object(sync_pkg, "CENTRAL_DIR", central), \
         patch.object(sync_pkg, "PRODUCTS", []):
        results = sync_skill("s1", verbose=False, only=["fa"])
    assert results == {}


def test_install_passes_only_to_sync(tmp_path):
    central = tmp_path / "central"
    src = tmp_path / "skill-src"
    _mk_skill(src, "inst")
    sync_calls = []
    with patch.object(sync_pkg, "CENTRAL_DIR", central), \
         patch.object(sync_pkg, "sync_skill",
                      side_effect=lambda name, **kw: sync_calls.append(kw) or None):
        ok = install_skill(str(src / "inst"), sync=True, no_audit=True,
                           verbose=False, only=["fa"])
    assert ok is True
    assert sync_calls and sync_calls[0]["only"] == ["fa"]


# ---------------------------------------------------------------- rollback

def _fake_env(tmp_path):
    """central + sources file patched onto the sources module seam."""
    central = tmp_path / "central"
    _mk_skill(central, "s1")
    (central / "s1" / "old-file.txt").write_text("old", encoding="utf-8")
    sf = tmp_path / "sources.json"
    sf.write_text(json.dumps({"s1": {
        "repo_url": "https://github.com/acme/skills", "sub_path": "s1",
        "branch": "main", "commit": "aaaaaaaa",
    }}), encoding="utf-8")
    return central, sf


def test_update_snapshots_and_rollback_restores(tmp_path):
    central, sf = _fake_env(tmp_path)
    new_install = central / "s1"

    def fake_install(url, verbose=True, skill_hint=None):
        # simulate the update: the old dir was already moved away, so just
        # create the new version at the central path
        new_install.mkdir(parents=True)
        (new_install / "SKILL.md").write_text(
            "---\nname: s1\ndescription: new\n---\nnew body", encoding="utf-8")
        return "s1", True

    with patch.object(sources_mod, "CENTRAL_DIR", central), \
         patch.object(sources_mod, "SOURCES_FILE", sf), \
         patch.object(sources_mod, "_latest_commit", return_value=("bbbbbbbb", "main")), \
         patch("agent_skill_manager.services.sync._install_from_url", side_effect=fake_install), \
         patch("agent_skill_manager.services.sync.sync_skill", return_value={}):
        ok = sources_mod.update_skill("s1", verbose=False)
        assert ok is True
        # new version live, old version snapshotted outside central
        assert "new body" in (central / "s1" / "SKILL.md").read_text(encoding="utf-8")
        assert (central.parent / ".askill-versions" / "s1" / "last" / "old-file.txt").exists()

        snap_list = sources_mod.list_rollbackable()
        assert [n for n, _ in snap_list] == ["s1"]

        rolled = sources_mod.rollback_skill("s1", verbose=False)
        assert rolled is True
        # old content restored, snapshot consumed
        assert "old" in (central / "s1" / "old-file.txt").read_text(encoding="utf-8")
        assert not (central.parent / ".askill-versions" / "s1").exists()


def test_rollback_without_snapshot_fails(tmp_path, capsys):
    central, sf = _fake_env(tmp_path)
    with patch.object(sources_mod, "CENTRAL_DIR", central), \
         patch.object(sources_mod, "SOURCES_FILE", sf), \
         patch("agent_skill_manager.services.sync.sync_skill", return_value={}):
        ok = sources_mod.rollback_skill("s1", verbose=True)
    assert ok is False
    assert "No rollback snapshot" in capsys.readouterr().out


def test_snapshot_missing_skill_is_none(tmp_path):
    central = tmp_path / "central"
    central.mkdir()
    with patch.object(sources_mod, "CENTRAL_DIR", central):
        assert sources_mod.snapshot_skill("ghost") is None
