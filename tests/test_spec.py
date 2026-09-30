"""Tests for the agentskills.io spec compliance checker (v0.11.0)."""
from __future__ import annotations

from pathlib import Path

from agent_skill_manager.services.spec import (
    check_spec, check_all_specs, parse_frontmatter,
)


def _mk_skill(parent: Path, name: str = "demo-skill", frontmatter: str | None = None,
              body: str = "hello") -> Path:
    d = parent / name
    d.mkdir(parents=True, exist_ok=True)
    if frontmatter is None:
        frontmatter = (
            f"---\nname: {name}\n"
            f"description: Does demo things. Use when demoing.\n---\n"
        )
    (d / "SKILL.md").write_text(frontmatter + body + "\n", encoding="utf-8")
    return d


class TestParseFrontmatter:
    def test_flat_fields(self):
        fields, warns = parse_frontmatter(
            "---\nname: pdf\ndescription: \"Extract text\"\nlicense: MIT\n---\nbody"
        )
        assert fields == {"name": "pdf", "description": "Extract text", "license": "MIT"}
        assert warns == []

    def test_nested_metadata_skipped(self):
        fields, warns = parse_frontmatter(
            "---\nname: pdf\nmetadata:\n  author: me\n  version: \"1.0\"\n---\n"
        )
        assert fields["name"] == "pdf"
        assert "author" not in fields
        assert warns == []

    def test_missing_block(self):
        fields, warns = parse_frontmatter("no frontmatter here")
        assert fields == {} and len(warns) == 1

    def test_unclosed_block(self):
        fields, warns = parse_frontmatter("---\nname: x\nbody never closed")
        assert any("never closed" in w for w in warns)


class TestCheckSpec:
    def test_valid_skill_passes(self, tmp_path):
        d = _mk_skill(tmp_path)
        r = check_spec(d)
        assert r["ok"] is True and r["errors"] == [] and r["warnings"] == []

    def test_missing_skillmd(self, tmp_path):
        d = tmp_path / "empty"; d.mkdir()
        r = check_spec(d)
        assert r["ok"] is False and "SKILL.md missing" in r["errors"]

    def test_missing_name(self, tmp_path):
        d = _mk_skill(tmp_path, frontmatter="---\ndescription: x\n---\n")
        assert any("'name'" in e for e in check_spec(d)["errors"])

    def test_missing_description(self, tmp_path):
        d = _mk_skill(tmp_path, frontmatter="---\nname: demo-skill\n---\n")
        assert any("'description'" in e for e in check_spec(d)["errors"])

    def test_name_must_match_dir(self, tmp_path):
        d = _mk_skill(tmp_path, name="demo-skill",
                      frontmatter="---\nname: other-name\ndescription: x\n---\n")
        assert any("does not match directory" in e for e in check_spec(d)["errors"])

    def test_uppercase_name_rejected(self, tmp_path):
        d = _mk_skill(tmp_path, frontmatter="---\nname: Demo-Skill\ndescription: x\n---\n")
        assert check_spec(d)["ok"] is False

    def test_double_hyphen_name_rejected(self, tmp_path):
        d = _mk_skill(tmp_path, frontmatter="---\nname: demo--skill\ndescription: x\n---\n")
        assert check_spec(d)["ok"] is False

    def test_leading_hyphen_name_rejected(self, tmp_path):
        d = _mk_skill(tmp_path, frontmatter="---\nname: -demo\ndescription: x\n---\n")
        assert check_spec(d)["ok"] is False

    def test_trailing_hyphen_name_rejected(self, tmp_path):
        d = _mk_skill(tmp_path, frontmatter="---\nname: demo-\ndescription: x\n---\n")
        assert check_spec(d)["ok"] is False

    def test_oversized_description_rejected(self, tmp_path):
        fm = f"---\nname: demo-skill\ndescription: {'x' * 1025}\n---\n"
        d = _mk_skill(tmp_path, frontmatter=fm)
        assert any("max 1024" in e for e in check_spec(d)["errors"])

    def test_oversized_compatibility_rejected(self, tmp_path):
        fm = f"---\nname: demo-skill\ndescription: x\ncompatibility: {'y' * 501}\n---\n"
        d = _mk_skill(tmp_path, frontmatter=fm)
        assert any("max 500" in e for e in check_spec(d)["errors"])

    def test_long_body_is_warning_only(self, tmp_path):
        d = _mk_skill(tmp_path, body="line\n" * 600)
        r = check_spec(d)
        assert r["ok"] is True
        assert any("500" in w for w in r["warnings"])

    def test_no_frontmatter_fails(self, tmp_path):
        d = tmp_path / "plain"; d.mkdir()
        (d / "SKILL.md").write_text("just markdown, no yaml\n", encoding="utf-8")
        r = check_spec(d)
        assert r["ok"] is False
        assert any("frontmatter" in e for e in r["errors"])


class TestCheckAllSpecs:
    def test_all_specs_uses_central_listing(self, tmp_path, monkeypatch):
        from agent_skill_manager.services import spec as spec_mod
        good = _mk_skill(tmp_path, "good-skill")
        bad = _mk_skill(tmp_path, "bad-skill", frontmatter="---\nname: mismatch\n---\n")
        monkeypatch.setattr(spec_mod, "list_skills", lambda: [good, bad])
        reports = check_all_specs()
        assert [r["skill"] for r in reports] == ["good-skill", "bad-skill"]
        assert reports[0]["ok"] and not reports[1]["ok"]
