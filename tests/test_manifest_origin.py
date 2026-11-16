"""Tests for manifest origin tagging and --external-only (P1-10)."""

import json
from unittest.mock import patch

from agent_skill_manager.services import manifest as mod


def _skill(root, name):
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: d\n---\nbody", encoding="utf-8",
    )


def _bundle(tmp_path, **kwargs):
    central = tmp_path / "central"
    _skill(central, "tracked")
    _skill(central, "handmade")
    out = tmp_path / "manifest.json"
    sources = {
        "tracked": {"repo_url": "https://github.com/o/r", "branch": "main"},
    }
    with patch.object(mod, "load_sources", return_value=sources):
        mod.bundle_manifest(output=out, central=central, verbose=False, **kwargs)
    return json.loads(out.read_text(encoding="utf-8"))


def test_bundle_tags_origin(tmp_path):
    data = _bundle(tmp_path)
    by_name = {e["name"]: e for e in data["skills"]}
    assert by_name["tracked"]["origin"] == "git"
    assert by_name["tracked"]["source"]["kind"] == "git"
    assert by_name["handmade"]["origin"] == "local"
    assert by_name["handmade"]["source"] is None


def test_external_only_drops_locally_authored(tmp_path):
    data = _bundle(tmp_path, external_only=True)
    assert [e["name"] for e in data["skills"]] == ["tracked"]


def test_install_never_fetches_local_skills(tmp_path):
    data = _bundle(tmp_path)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    target = tmp_path / "other-central"
    with patch.object(mod, "_install_from_url", return_value=("tracked", True)) as install:
        report = mod.install_manifest(path, central=target, verbose=False)
    assert report["ok"] is True
    assert any(name == "handmade" and "locally authored" in why
               for name, why in report["manual"])
    assert install.call_count == 1  # only the git-sourced skill
    assert report["failed"] == []


def test_legacy_manifest_without_origin_still_works(tmp_path):
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps({
        "version": mod.MANIFEST_VERSION,
        "skills": [{"name": "old", "source": None}],
    }), encoding="utf-8")
    with patch.object(mod, "_install_from_url") as install:
        report = mod.install_manifest(path, central=tmp_path / "empty", verbose=False)
    assert report["manual"][0][0] == "old"
    install.assert_not_called()
