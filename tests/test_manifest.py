"""Tests for team manifest sync (bundle / install --manifest)."""

import json
from pathlib import Path
from unittest.mock import patch

from agent_skill_manager.services import manifest as manifest_mod
from agent_skill_manager.services.manifest import bundle_manifest, install_manifest


def _mk_skill(central: Path, name: str):
    d = central / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: %s\n---\n# body\n" % name, encoding="utf-8")
    return d


def test_bundle_writes_manifest_with_sources(tmp_path):
    central = tmp_path / "central"
    _mk_skill(central, "git-skill")
    _mk_skill(central, "local-skill")
    sources = tmp_path / "sources.json"
    sources.write_text(
        json.dumps({"git-skill": {
            "repo_url": "https://github.com/acme/skills",
            "sub_path": "git-skill", "branch": "main", "commit": "abc",
        }}),
        encoding="utf-8",
    )
    with patch.object(manifest_mod, "CENTRAL_DIR", central), \
         patch.object(manifest_mod, "load_sources",
                      lambda: json.loads(sources.read_text(encoding="utf-8"))):
        out = bundle_manifest(verbose=False)

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["version"] == manifest_mod.MANIFEST_VERSION
    by_name = {s["name"]: s for s in data["skills"]}
    assert by_name["git-skill"]["source"]["kind"] == "git"
    assert by_name["git-skill"]["source"]["repo_url"] == "https://github.com/acme/skills"
    assert by_name["local-skill"]["source"] is None


def test_bundle_default_output_path_is_alongside_central(tmp_path):
    central = tmp_path / "central"
    _mk_skill(central, "s1")
    with patch.object(manifest_mod, "CENTRAL_DIR", central), \
         patch.object(manifest_mod, "load_sources", dict):
        out = bundle_manifest(verbose=False)
    assert out == tmp_path / "askill-manifest.json"


def test_install_manifest_installs_missing_from_git_source(tmp_path):
    central = tmp_path / "central"
    central.mkdir()
    manifest = tmp_path / "askill-manifest.json"
    manifest.write_text(json.dumps({
        "version": 1,
        "skills": [
            {"name": "from-git", "source": {
                "kind": "git", "repo_url": "https://github.com/acme/skills",
                "sub_path": "from-git", "branch": "main"}},
            {"name": "no-source", "source": None},
        ],
    }), encoding="utf-8")

    calls = []

    def fake_url(url, verbose=True, skill_hint=None):
        calls.append(url)
        d = central / "from-git"
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text("---\nname: from-git\n---\n", encoding="utf-8")
        return "from-git", True

    with patch.object(manifest_mod, "CENTRAL_DIR", central), \
         patch.object(manifest_mod, "_install_from_url", side_effect=fake_url):
        report = install_manifest(manifest, central=central, verbose=False)

    assert report["ok"] is True
    assert report["installed"] == ["from-git"]
    assert [n for n, _ in report["manual"]] == ["no-source"]
    assert report["failed"] == []
    assert calls == ["https://github.com/acme/skills/tree/main/from-git"]


def test_install_manifest_reports_present_skills(tmp_path):
    central = tmp_path / "central"
    _mk_skill(central, "already-here")
    manifest = tmp_path / "askill-manifest.json"
    manifest.write_text(json.dumps({
        "version": 1,
        "skills": [{"name": "already-here", "source": None}],
    }), encoding="utf-8")
    report = install_manifest(manifest, central=central, verbose=False)
    assert report["present"] == ["already-here"]
    assert report["installed"] == []


def test_install_manifest_rejects_unsupported_version(tmp_path):
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({"version": 99, "skills": []}), encoding="utf-8")
    report = install_manifest(manifest, central=tmp_path, verbose=False)
    assert report["ok"] is False
    assert "unsupported manifest version" in report["error"]


def test_install_manifest_missing_file(tmp_path):
    report = install_manifest(tmp_path / "nope.json", central=tmp_path, verbose=False)
    assert report["ok"] is False
    assert "cannot read manifest" in report["error"]
