"""Tests for ``askill new`` scaffolding (v0.15.0, docs/v0.15.0-plan.md R1)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from agent_skill_manager.services.scaffold import (
    collect_required_frontmatter,
    create_skill,
    validate_skill_name,
)
from agent_skill_manager.services.spec import check_spec, product_frontmatter_issues

# ------------------------------------------------------- name validation

class TestNameValidation:
    def test_valid_names(self):
        for n in ("my-skill", "pdf-tools", "a", "a1-b2", "x" * 64):
            assert validate_skill_name(n) is None, n

    def test_rejects_uppercase(self):
        assert validate_skill_name("My-Skill")

    def test_rejects_double_hyphen(self):
        assert validate_skill_name("my--skill")

    def test_rejects_edge_hyphens(self):
        assert validate_skill_name("-skill")
        assert validate_skill_name("skill-")

    def test_rejects_too_long(self):
        assert validate_skill_name("a" * 65)

    def test_rejects_empty(self):
        assert validate_skill_name("")


# ------------------------------------------------- frontmatter collection

class TestCollectRequiredFields:
    def test_none_targets_yields_superset(self):
        fields, err = collect_required_frontmatter(None)
        assert err is None
        # qwenwork documents all four fields; create_skill subtracts the
        # base-covered name/description when writing the file
        assert fields == ["name", "version", "description", "description_zh"]

    def test_target_qwenwork(self):
        fields, err = collect_required_frontmatter(["qwenwork"])
        assert err is None
        assert fields == ["name", "version", "description", "description_zh"]

    def test_target_without_requirements(self):
        fields, err = collect_required_frontmatter(["traecn"])
        assert err is None
        assert fields == []

    def test_unknown_target(self):
        fields, err = collect_required_frontmatter(["nope"])
        assert err and "nope" in err and "qwenwork" in err  # available list included


# ----------------------------------------------------------- create_skill

class TestCreateSkill:
    def _create(self, tmp_path: Path, name="demo-skill", **kw):
        return create_skill(name, central_dir=tmp_path, **kw)

    def test_full_skeleton(self, tmp_path):
        r = self._create(tmp_path)
        assert r["created"] and r["error"] is None
        d = Path(r["path"])
        assert (d / "SKILL.md").exists()
        assert (d / "references" / "README.md").exists()
        assert (d / "scripts" / ".gitkeep").exists()

    def test_minimal_skeleton(self, tmp_path):
        r = self._create(tmp_path, minimal=True)
        d = Path(r["path"])
        assert (d / "SKILL.md").exists()
        assert not (d / "references").exists()
        assert not (d / "scripts").exists()

    def test_passes_verify_unchanged(self, tmp_path):
        """R1 acceptance: the scaffold passes verify with zero edits."""
        r = self._create(tmp_path)
        d = Path(r["path"])
        assert check_spec(d)["ok"]
        assert product_frontmatter_issues(d) == []

    def test_default_is_superset_frontmatter(self, tmp_path):
        text = (Path(self._create(tmp_path)["path"]) / "SKILL.md").read_text(encoding="utf-8")
        assert "name: demo-skill" in text
        assert "description: (TODO)" in text
        assert "version: 0.1.0" in text
        assert "description_zh: （TODO）" in text  # noqa: RUF001 - intentional Chinese punctuation
        # qwenwork also declares name/description - they must NOT be
        # duplicated (a dup key would shadow the real value on parse)
        assert text.count("name:") == 1
        assert text.count("description:") == 1

    def test_explicit_no_targets_is_base_only(self, tmp_path):
        text = (Path(self._create(tmp_path, targets=[])["path"]) / "SKILL.md").read_text(encoding="utf-8")
        assert "version:" not in text
        assert "description_zh:" not in text

    def test_target_qwenwork_frontmatter(self, tmp_path):
        text = (Path(self._create(tmp_path, targets=["qwenwork"])["path"]) / "SKILL.md").read_text(encoding="utf-8")
        assert "version: 0.1.0" in text
        assert "description_zh:" in text

    def test_explicit_values_win(self, tmp_path):
        text = (Path(self._create(
            tmp_path, description="Does X well", description_zh="做X", version="1.2.3",
        )["path"]) / "SKILL.md").read_text(encoding="utf-8")
        assert "description: Does X well" in text
        assert "description_zh: 做X" in text
        assert "version: 1.2.3" in text

    def test_existing_dir_rejected(self, tmp_path):
        assert self._create(tmp_path)["created"]
        r2 = self._create(tmp_path)
        assert not r2["created"]
        assert "already exists" in r2["error"]

    def test_invalid_name_rejected(self, tmp_path):
        r = self._create(tmp_path, name="Bad--Name")
        assert not r["created"]
        assert not (tmp_path / "Bad--Name").exists()  # nothing touched

    def test_unknown_target_rejected(self, tmp_path):
        r = self._create(tmp_path, targets=["nope"])
        assert not r["created"]
        assert not any(tmp_path.iterdir())  # nothing touched


# ------------------------------------------------------------- cli wiring

class TestNewCli:
    def test_creates_in_central(self, tmp_path, capsys):
        from agent_skill_manager.controllers import cli
        with patch("agent_skill_manager.services.scaffold.CENTRAL_DIR", tmp_path), \
             patch("agent_skill_manager.services.sync.CENTRAL_DIR", tmp_path), \
             patch("agent_skill_manager.controllers.cli.CENTRAL_DIR", tmp_path):
            cli.main(["new", "cli-made", "--minimal"])
        out = capsys.readouterr().out
        assert "Created skill skeleton" in out
        assert (tmp_path / "cli-made" / "SKILL.md").exists()

    def test_json_output_parseable(self, tmp_path, capsys):
        from agent_skill_manager.controllers import cli
        with patch("agent_skill_manager.services.scaffold.CENTRAL_DIR", tmp_path), \
             patch("agent_skill_manager.services.sync.CENTRAL_DIR", tmp_path), \
             patch("agent_skill_manager.controllers.cli.CENTRAL_DIR", tmp_path):
            cli.main(["new", "json-made", "--minimal", "--json"])
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["created"] is True
        assert parsed["spec"]["ok"] is True
        assert parsed["product_issues"] == []

    def test_conflict_prints_error(self, tmp_path, capsys):
        from agent_skill_manager.controllers import cli
        with patch("agent_skill_manager.services.scaffold.CENTRAL_DIR", tmp_path):
            cli.main(["new", "twice", "--minimal"])
            with pytest.raises(SystemExit) as ei:
                cli.main(["new", "twice", "--minimal"])
            assert ei.value.code == 1
        out = capsys.readouterr().out
        assert "already exists" in out

    def test_quiet_still_prints_path(self, tmp_path, capsys):
        from agent_skill_manager.controllers import cli
        with patch("agent_skill_manager.services.scaffold.CENTRAL_DIR", tmp_path), \
             patch("agent_skill_manager.services.sync.CENTRAL_DIR", tmp_path), \
             patch("agent_skill_manager.controllers.cli.CENTRAL_DIR", tmp_path):
            cli.main(["new", "quiet-one", "--minimal", "--quiet"])
        out = capsys.readouterr().out
        assert "quiet-one" in out          # the data (path) survives quiet
        assert "Next steps" not in out     # guidance suppressed
