"""Tests for the skills.sh registry integration (v0.11.0)."""
from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

from agent_skill_manager.services import registry as reg


# ---------------------------------------------------------------- resolve

class TestResolveSource:
    def test_shorthand(self):
        r = reg.resolve_source("anthropics/skills")
        assert r["repo_url"] == "https://github.com/anthropics/skills"
        assert r["skill"] is None
        assert r["original"] == "anthropics/skills"

    def test_shorthand_with_skill(self):
        r = reg.resolve_source("anthropics/skills@pdf")
        assert r["repo_url"] == "https://github.com/anthropics/skills"
        assert r["skill"] == "pdf"

    def test_shorthand_trailing_slash(self):
        assert reg.resolve_source("owner/repo/")["repo_url"] == "https://github.com/owner/repo"

    def test_skillssh_url_full(self):
        r = reg.resolve_source("https://skills.sh/owner/repo/my-skill")
        assert r["repo_url"] == "https://github.com/owner/repo"
        assert r["skill"] == "my-skill"

    def test_skillssh_url_repo_only(self):
        r = reg.resolve_source("https://skills.sh/owner/repo")
        assert r["skill"] is None

    def test_github_url_passthrough(self):
        assert reg.resolve_source("https://github.com/u/r") is None

    def test_local_relative_path_not_shorthand(self):
        # 3+ segments and dotted prefixes are never ecosystem shorthand
        assert reg.resolve_source("./some/local/path") is None
        assert reg.resolve_source("a/b/c") is None
        assert reg.resolve_source("just-a-name") is None

    def test_windows_drive_path_not_shorthand(self):
        assert reg.resolve_source("C:/Users/me/my-skill") is None

    def test_unix_absolute_path_not_shorthand(self):
        assert reg.resolve_source("/tmp/skills/x") is None


# ---------------------------------------------------------------- find

class TestFindSkillDir:
    def test_root_level(self, tmp_path):
        d = tmp_path / "pdf"; d.mkdir(); (d / "SKILL.md").write_text("x")
        assert reg.find_skill_dir(tmp_path, "pdf") == d

    def test_skills_subdir(self, tmp_path):
        d = tmp_path / "skills" / "pdf"; d.mkdir(parents=True)
        (d / "SKILL.md").write_text("x")
        assert reg.find_skill_dir(tmp_path, "pdf") == d

    def test_nested_scan(self, tmp_path):
        d = tmp_path / "plugins" / "office" / "pdf"; d.mkdir(parents=True)
        (d / "SKILL.md").write_text("x")
        assert reg.find_skill_dir(tmp_path, "pdf") == d

    def test_missing_returns_none(self, tmp_path):
        (tmp_path / "other").mkdir(); (tmp_path / "other" / "SKILL.md").write_text("x")
        assert reg.find_skill_dir(tmp_path, "pdf") is None

    def test_ignores_skill_without_skillmd(self, tmp_path):
        d = tmp_path / "pdf"; d.mkdir()          # no SKILL.md inside
        (d / "README.md").write_text("x")
        assert reg.find_skill_dir(tmp_path, "pdf") is None


# ---------------------------------------------------------------- search

class _FakeResponse:
    def __init__(self, payload: bytes):
        self._buf = io.BytesIO(payload)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._buf.read()


class TestSearchSkills:
    def _patch_urlopen(self, monkeypatch, payload: bytes):
        monkeypatch.setattr(
            reg.urllib.request, "urlopen",
            lambda req, timeout=None: _FakeResponse(payload),
        )

    def test_parses_results(self, monkeypatch):
        payload = json.dumps({
            "query": "pdf", "skills": [
                {"id": "a/skills/pdf", "source": "a/skills", "skillId": "pdf",
                 "name": "pdf", "installs": 1234},
                {"id": "b/repo/pdftool", "source": "b/repo", "skillId": "pdftool",
                 "name": "PDF Tool", "installs": "42"},   # string installs too
            ],
        }).encode("utf-8")
        self._patch_urlopen(monkeypatch, payload)
        results = reg.search_skills("pdf")
        assert results[0] == {
            "source": "a/skills", "skill_id": "pdf", "name": "pdf", "installs": 1234,
        }
        assert results[1]["installs"] == 42

    def test_limit(self, monkeypatch):
        payload = json.dumps({
            "skills": [{"source": f"s{i}", "skillId": f"k{i}", "name": f"n{i}",
                        "installs": i} for i in range(20)],
        }).encode("utf-8")
        self._patch_urlopen(monkeypatch, payload)
        assert len(reg.search_skills("x", limit=5)) == 5

    def test_query_is_url_encoded(self, monkeypatch):
        seen = {}
        def fake_urlopen(req, timeout=None):
            seen["url"] = req.full_url
            return _FakeResponse(b'{"skills": []}')
        monkeypatch.setattr(reg.urllib.request, "urlopen", fake_urlopen)
        reg.search_skills("code review")
        assert "q=code%20review" in seen["url"]

    def test_network_error_raises_registry_error(self, monkeypatch):
        def boom(req, timeout=None):
            raise urllib.error.URLError("connection refused")
        monkeypatch.setattr(reg.urllib.request, "urlopen", boom)
        with pytest.raises(reg.RegistryError):
            reg.search_skills("pdf")

    def test_bad_json_raises_registry_error(self, monkeypatch):
        self._patch_urlopen(monkeypatch, b"<html>not json</html>")
        with pytest.raises(reg.RegistryError):
            reg.search_skills("pdf")


# ---------------------------------------------------------------- install

class TestInstallShorthand:
    def _mk_skill(self, parent: Path, name: str = "demo-skill") -> Path:
        d = parent / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: demo\n---\nbody", encoding="utf-8",
        )
        return d

    def test_shorthand_routed_to_github(self, tmp_path):
        from agent_skill_manager.services import sync as sync_mod
        calls = {}
        def fake_url(source, verbose=True, skill_hint=None):
            calls["source"], calls["hint"] = source, skill_hint
            return "demo-skill", True
        with patch.object(sync_mod, "CENTRAL_DIR", tmp_path), \
             patch.object(sync_mod, "_install_from_url", side_effect=fake_url) as m:
            ok = sync_mod.install_skill("owner/repo@my-skill", verbose=False)
        assert ok is True
        assert calls["source"] == "https://github.com/owner/repo"
        assert calls["hint"] == "my-skill"

    def test_skillssh_url_routed(self, tmp_path):
        from agent_skill_manager.services import sync as sync_mod
        with patch.object(sync_mod, "CENTRAL_DIR", tmp_path), \
             patch.object(sync_mod, "_install_from_url", return_value=("x", True)) as m:
            sync_mod.install_skill("https://skills.sh/a/b/c", verbose=False)
        args, kwargs = m.call_args
        assert args[0] == "https://github.com/a/b"
        assert kwargs.get("skill_hint") == "c"

    def test_github_url_unchanged(self, tmp_path):
        from agent_skill_manager.services import sync as sync_mod
        with patch.object(sync_mod, "CENTRAL_DIR", tmp_path), \
             patch.object(sync_mod, "_install_from_url", return_value=("x", True)) as m:
            sync_mod.install_skill("https://github.com/u/r/tree/main/sk", verbose=False)
        args, kwargs = m.call_args
        assert args[0] == "https://github.com/u/r/tree/main/sk"
        assert not kwargs.get("skill_hint")

    def test_local_path_still_local(self, tmp_path):
        from agent_skill_manager.services import sync as sync_mod
        skill = self._mk_skill(tmp_path, "local-skill")
        central = tmp_path / "central"; central.mkdir()
        with patch.object(sync_mod, "CENTRAL_DIR", central), \
             patch.object(sync_mod, "_install_from_url") as m:
            ok = sync_mod.install_skill(str(skill), verbose=False)
        assert ok is True
        assert (central / "local-skill" / "SKILL.md").exists()
        m.assert_not_called()
