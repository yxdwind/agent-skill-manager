"""Tests for agent_skill_manager.core module."""

import json
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from agent_skill_manager.core import (
    list_skills,
    get_status,
    sync_skill,
    pack_skill,
    _update_workbuddy_settings,
)


class TestListSkills:
    def test_empty_when_no_central_dir(self, tmp_path):
        with patch("agent_skill_manager.core.CENTRAL_DIR", tmp_path / "nonexistent"):
            assert list_skills() == []

    def test_lists_skill_dirs(self, tmp_path):
        skill1 = tmp_path / "skill1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("---\nname: skill1\n---\n")

        skill2 = tmp_path / "skill2"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("---\nname: skill2\n---\n")

        not_skill = tmp_path / "not-skill"
        not_skill.mkdir()

        with patch("agent_skill_manager.core.CENTRAL_DIR", tmp_path):
            skills = list_skills()
            assert len(skills) == 2
            assert skill1 in skills
            assert skill2 in skills

    def test_sorted_results(self, tmp_path):
        for name in ["zebra", "alpha", "mango"]:
            d = tmp_path / name
            d.mkdir()
            (d / "SKILL.md").write_text("---\nname: %s\n---\n" % name)

        with patch("agent_skill_manager.core.CENTRAL_DIR", tmp_path):
            skills = list_skills()
            names = [s.name for s in skills]
            assert names == sorted(names)


class TestGetStatus:
    def test_returns_results_for_all_products(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n")

        with patch("agent_skill_manager.core.CENTRAL_DIR", tmp_path):
            results = get_status("my-skill")
            assert len(results) > 0
            shorts = {r["product_short"] for r in results}
            assert "dumate" in shorts
            assert "minimax" in shorts

    def test_empty_for_nonexistent_skill(self, tmp_path):
        with patch("agent_skill_manager.core.CENTRAL_DIR", tmp_path):
            assert get_status("nonexistent") == []


class TestPackSkill:
    def test_creates_zip(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n# Body")
        (skill_dir / "scripts").mkdir()
        (skill_dir / "scripts" / "run.py").write_text("# script")

        with patch("agent_skill_manager.core.CENTRAL_DIR", tmp_path):
            result = pack_skill("my-skill", verbose=False)
            assert result is not None
            assert result.suffix == ".zip"
            assert result.exists()

    def test_returns_none_for_missing_skill(self, tmp_path):
        with patch("agent_skill_manager.core.CENTRAL_DIR", tmp_path):
            assert pack_skill("nonexistent", verbose=False) is None

    def test_returns_none_without_skill_md(self, tmp_path):
        d = tmp_path / "no-md"
        d.mkdir()

        with patch("agent_skill_manager.core.CENTRAL_DIR", tmp_path):
            assert pack_skill("no-md", verbose=False) is None


class TestWorkBuddySettings:
    def test_creates_settings_file(self, tmp_path):
        settings_path = tmp_path / "settings.json"
        _update_workbuddy_settings(settings_path, "my-skill", verbose=False)
        assert settings_path.exists()
        data = json.loads(settings_path.read_text())
        assert data["skills"]["my-skill"] is True

    def test_updates_existing_settings(self, tmp_path):
        settings_path = tmp_path / "settings.json"
        settings_path.write_text(json.dumps({"skills": {"existing": True}}))
        _update_workbuddy_settings(settings_path, "new-skill", verbose=False)
        data = json.loads(settings_path.read_text())
        assert data["skills"]["existing"] is True
        assert data["skills"]["new-skill"] is True
