"""Regression tests for the global --quiet / --json flags.

Each subcommand inherits these from a parent argparse parser, so a single
test exercising one path per command is enough to lock the wiring.

The tests don't introspect actual skill / product data - they just verify
the output mode dispatches the right way (formatted text vs JSON, verbose
vs suppressed).
"""
import json
from pathlib import Path
from unittest.mock import patch


def _ok_skill(tmp_path: Path, name: str = "demo-skill"):
    d = tmp_path / name
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: x\n---\n# body\n", encoding="utf-8",
    )
    return d


class TestQuietFlag:
    """``--quiet / -q`` suppresses non-essential text. Errors always print."""

    def test_quiet_in_askill_help(self, capsys):
        """The flag is registered on every subparser (smoke check via status)."""
        from agent_skill_manager.controllers import cli
        with patch("sys.argv", ["askill", "status", "--quiet"]), \
             patch.object(cli, "_print_status") as mock_status:
            cli.main()
        # ``--quiet`` should have been delivered to ``_print_status``.
        args, kwargs = mock_status.call_args
        assert kwargs.get("quiet") is True

    def test_short_flag_alias(self, capsys):
        from agent_skill_manager.controllers import cli
        with patch("sys.argv", ["askill", "status", "-q"]), \
             patch.object(cli, "_print_status") as mock_status:
            cli.main()
        _, kwargs = mock_status.call_args
        assert kwargs.get("quiet") is True

    def test_quiet_skips_onboarding_when_central_empty(self, tmp_path, capsys):
        """No central repo -> no onboarding tips when quiet."""
        from agent_skill_manager.controllers import cli
        with patch("agent_skill_manager.services.sync.CENTRAL_DIR", tmp_path), \
             patch("agent_skill_manager.controllers.cli.CENTRAL_DIR", tmp_path):
            cli._print_list(quiet=True)
        out = capsys.readouterr().out
        assert "Get started in 3 steps" not in out

    def test_non_quiet_shows_onboarding_when_central_empty(self, tmp_path, capsys):
        """Sanity: the same call WITHOUT --quiet still prints onboarding."""
        from agent_skill_manager.controllers import cli
        with patch("agent_skill_manager.services.sync.CENTRAL_DIR", tmp_path), \
             patch("agent_skill_manager.controllers.cli.CENTRAL_DIR", tmp_path):
            cli._print_list(quiet=False)
        out = capsys.readouterr().out
        assert "Get started in 3 steps" in out


class TestJsonFlag:
    """``--json`` emits structured JSON to stdout."""

    def test_status_json_shape(self, tmp_path, capsys):
        from agent_skill_manager.controllers import cli
        _ok_skill(tmp_path, "demo")
        with patch("agent_skill_manager.services.sync.CENTRAL_DIR", tmp_path), \
             patch("agent_skill_manager.controllers.cli.CENTRAL_DIR", tmp_path), \
             patch("agent_skill_manager.config.products.PRODUCTS", [{"name": "T", "short": "t",
                 "macos_path": tmp_path, "windows_path": tmp_path,
                 "linux_path": tmp_path, "sync_method": "symlink"}]), \
             patch("agent_skill_manager.services.sync.PRODUCTS",
                 [{"name": "T", "short": "t", "macos_path": tmp_path,
                   "windows_path": tmp_path, "linux_path": tmp_path,
                   "sync_method": "symlink"}]), \
             patch("agent_skill_manager.services.sync.get_product_path",
                   return_value=tmp_path):
            cli._print_status(json_mode=True)
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert isinstance(parsed, list)
        assert parsed and "skill_name" in parsed[0]
        # Clean fixture → high score; the JSON emits the audit verdict too.
        assert parsed[0]["audit_grade"] in ("A", "B")

    def test_list_json_shape(self, tmp_path, capsys):
        from agent_skill_manager.controllers import cli
        _ok_skill(tmp_path, "demo")
        with patch("agent_skill_manager.services.sync.CENTRAL_DIR", tmp_path), \
             patch("agent_skill_manager.controllers.cli.CENTRAL_DIR", tmp_path):
            cli._print_list(json_mode=True)
        parsed = json.loads(capsys.readouterr().out)
        assert isinstance(parsed, list)
        # ``skill`` is the directory name (audit keys off the dir).
        assert parsed[0]["skill"] == "demo"
        assert parsed[0]["audit_grade"] in ("A", "B")

    def test_products_json_shape(self, capsys):
        from agent_skill_manager.config.products import PRODUCTS
        from agent_skill_manager.controllers import cli
        with patch("agent_skill_manager.controllers.cli.PRODUCTS", PRODUCTS):
            cli._print_products(json_mode=True)
        parsed = json.loads(capsys.readouterr().out)
        assert isinstance(parsed, list)
        assert {p["short"] for p in parsed} == {p["short"] for p in PRODUCTS}

    def test_audit_json_emits_skill_report(self, tmp_path, capsys):
        from agent_skill_manager.controllers import cli
        _ok_skill(tmp_path, "demo")
        with patch("agent_skill_manager.services.sync.CENTRAL_DIR", tmp_path), \
             patch("agent_skill_manager.controllers.cli.CENTRAL_DIR", tmp_path):
            cli._print_audit(json_mode=True)
        parsed = json.loads(capsys.readouterr().out)
        assert isinstance(parsed, list)
        assert parsed[0]["skill"] == "demo"
        assert parsed[0]["verdict"] in ("safe", "caution", "risky", "dangerous")

    def test_search_json_no_query(self, capsys):
        from agent_skill_manager.controllers import cli
        with patch("sys.argv", ["askill", "search", "--json"]):
            cli.main()
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["error"] == "missing query"

    def test_json_flag_dispatches_to_helper(self, capsys):
        """Sanity: --json is routed to the helper that supports it."""
        from agent_skill_manager.controllers import cli
        with patch("sys.argv", ["askill", "status", "--json"]), \
             patch.object(cli, "_print_status") as mock_status:
            cli.main()
        _, kwargs = mock_status.call_args
        assert kwargs.get("json_mode") is True


class TestFlagsDontConflict:
    """Quiet + JSON coexist cleanly: JSON wins for output shape, quiet
    suppresses headers / onboarding."""

    def test_quiet_and_json_together(self, tmp_path, capsys):
        from agent_skill_manager.controllers import cli
        with patch("agent_skill_manager.services.sync.CENTRAL_DIR", tmp_path), \
             patch("agent_skill_manager.controllers.cli.CENTRAL_DIR", tmp_path):
            cli._print_list(quiet=True, json_mode=True)
        # Empty central -> [] not {} since list mode is JSON
        out = capsys.readouterr().out
        assert out.strip() == "[]"
