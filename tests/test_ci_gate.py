"""Tests for CI gate output (P1-8)."""

from unittest.mock import patch

import pytest
from agent_skill_manager.controllers import cli
from agent_skill_manager.services.ci_format import (
    audit_annotations,
    grades_failed,
    parse_fail_on,
    verify_annotations,
)


def test_parse_fail_on():
    assert parse_fail_on("D,F") == {"D", "F"}
    assert parse_fail_on("d f") == {"D", "F"}
    assert parse_fail_on(None) == set()
    with pytest.raises(ValueError):
        parse_fail_on("D,Z")


def test_verify_annotations_escape_and_point_at_skill_md(tmp_path):
    results = [{
        "skill": "bad", "ok": False,
        "errors": ["missing description"], "warnings": ["body too long"],
    }]
    lines = verify_annotations(
        results, [("bad", ["needs description_zh"])], central=tmp_path,
    )
    assert len(lines) == 3
    assert all(line.startswith(("::error ", "::warning ")) for line in lines)
    assert "file=" + str(tmp_path / "bad" / "SKILL.md") in lines[0]
    assert "%0A" not in lines[0]  # no raw newlines leaking into the command


def test_audit_annotations_and_grade_gate():
    reports = [{
        "skill": "risky", "path": "/tmp/risky", "grade": "D", "verdict": "risky",
        "findings": [
            {"severity": "high", "file": "SKILL.md", "line": 3, "message": "shell=True"},
            {"severity": "low", "file": "README.md", "line": 1, "message": "url"},
        ],
    }]
    lines = audit_annotations(reports, fail_on={"D", "F"})
    assert any("shell=True" in line and "line=3" in line for line in lines)
    assert not any("url" in line for line in lines)  # low severity not annotated
    assert any("grade D" in line for line in lines)
    assert grades_failed(reports, {"D", "F"}) == ["risky"]
    assert grades_failed(reports, {"F"}) == []


def test_verify_github_format_emits_annotations(tmp_path, capsys):
    skill = tmp_path / "bad"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: bad\n---\nbody", encoding="utf-8")
    spec_result = [{
        "skill": "bad", "ok": False,
        "errors": ["missing description"], "warnings": [],
    }]
    with patch.object(cli, "CENTRAL_DIR", tmp_path), \
         patch.object(cli, "list_skills", return_value=[skill]), \
         patch("agent_skill_manager.services.spec.check_all_specs",
               return_value=spec_result), \
         patch("agent_skill_manager.services.spec.product_frontmatter_issues",
               return_value=[]):
        rc = cli._cmd_verify(None, quiet=True, fmt="github")
    out = capsys.readouterr().out
    assert rc == 1
    assert "::error file=" in out
    assert "missing description" in out


def test_audit_fail_on_drives_exit_code(capsys):
    reports = [{
        "skill": "risky", "path": "/tmp/risky", "grade": "D", "verdict": "risky",
        "findings": [],
    }]
    with patch.object(cli, "audit_all", return_value=reports):
        failed = cli._print_audit(None, quiet=False, fail_on={"D", "F"})
        passed = cli._print_audit(None, quiet=True, fail_on={"F"})
    assert failed == 1
    assert passed == 0
    assert "gate failed" in capsys.readouterr().out


def test_cli_rejects_conflicting_modes_and_bad_grades():
    with pytest.raises(SystemExit) as exc:
        cli.main(["audit", "--residency", "--overlap", "--quiet"])
    assert exc.value.code == 2
    with pytest.raises(SystemExit) as exc:
        cli.main(["audit", "--fail-on", "Z", "--quiet"])
    assert exc.value.code == 2
