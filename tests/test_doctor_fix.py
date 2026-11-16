"""Tests for `askill doctor --fix` (P1-7)."""

import json
from unittest.mock import patch

import pytest
from agent_skill_manager.controllers import cli
from agent_skill_manager.services.remediation import build_fix_plan, render_plan


def _report(products=None, central=None, checks=None):
    base = {
        "ok": True,
        "checks": checks or [],
        "central": {
            "dir": "/nonexistent", "exists": True, "skills": 1,
            "tracked": 0, "orphan_sources": [],
        },
        "products": products if products is not None else [],
    }
    if central:
        base["central"].update(central)
    return base


def _product(short, broken=None, settings=True, forks=0):
    return {
        "short": short, "broken_names": broken or [],
        "settings_writable": settings, "fork_dirs": forks,
    }


def test_healthy_report_needs_no_automatic_repair():
    plan = build_fix_plan(_report(), {"alpha"})
    assert plan["noop"] is True
    assert plan["actions"] == []
    assert any(m["id"] == "rollbacks" for m in plan["manual"])
    assert "dry-run" in render_plan(plan)


def test_dead_links_split_into_relink_and_gc():
    report = _report(products=[_product("proda", ["alpha", "gone-skill"])])
    plan = build_fix_plan(report, {"alpha"})
    actions = {a["id"]: a for a in plan["actions"]}
    assert actions["relink"]["items"] == ["proda/alpha"]
    assert actions["relink"]["command"] == "askill sync"
    assert actions["gc"]["items"] == ["proda/gone-skill"]
    assert actions["gc"]["command"] == "askill sync --gc"
    assert plan["auto_count"] == 2


def test_manual_steps_cover_locked_settings_drift_orphans_and_env():
    report = _report(
        products=[_product("prodb", settings=False, forks=1)],
        central={"orphan_sources": ["old-skill"]},
        checks=[{"id": "proxy:x", "severity": "fail", "detail": "unreachable"}],
    )
    plan = build_fix_plan(report, set())
    ids = {m["id"] for m in plan["manual"]}
    assert {"settings-locked", "orphan-sources", "drift-candidates",
            "env:proxy:x", "rollbacks"} <= ids
    assert plan["noop"] is True  # manual-only plans never auto-execute
    assert "Manual steps" in render_plan(plan)


def test_cli_fix_dry_run_never_calls_sync(tmp_path, capsys):
    central = tmp_path / "central"
    central.mkdir()
    report = _report(
        products=[_product("proda", ["gone-skill"])],
        central={"dir": str(central), "exists": True},
    )
    with patch.object(cli, "doctor_report", return_value=report), \
         patch.object(cli, "sync_skill") as sync, \
         patch.object(cli, "gc_dead_links") as gc:
        cli.main(["doctor", "--fix", "--quiet"])
    out = capsys.readouterr().out
    assert "dry-run" in out
    assert "sync --gc" in out
    sync.assert_not_called()
    gc.assert_not_called()


def test_cli_apply_executes_both_auto_actions(tmp_path, capsys):
    central = tmp_path / "central"
    (central / "alpha").mkdir(parents=True)
    (central / "alpha" / "SKILL.md").write_text("---\nname: alpha\n---\n", encoding="utf-8")
    report = _report(
        products=[_product("proda", ["alpha", "gone-skill"])],
        central={"dir": str(central), "exists": True},
    )
    with patch.object(cli, "doctor_report", return_value=report), \
         patch.object(cli, "sync_skill") as sync, \
         patch.object(cli, "gc_dead_links") as gc:
        cli.main(["doctor", "--fix", "--apply", "--quiet"])
    out = capsys.readouterr().out
    assert "executed: askill sync, askill sync --gc" in out
    sync.assert_called_once()
    gc.assert_called_once()


def test_apply_without_fix_is_a_usage_error():
    with pytest.raises(SystemExit) as exc:
        cli.main(["doctor", "--apply", "--quiet"])
    assert exc.value.code == 2


def test_json_fix_output_is_machine_readable(tmp_path, capsys):
    central = tmp_path / "central"
    central.mkdir()
    report = _report(central={"dir": str(central), "exists": True})
    with patch.object(cli, "doctor_report", return_value=report):
        cli.main(["doctor", "--fix", "--json", "--quiet"])
    data = json.loads(capsys.readouterr().out)
    assert data["plan"]["noop"] is True
    assert data["applied"] == []
