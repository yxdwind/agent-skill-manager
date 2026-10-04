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


class TestAuditRegressions:
    """Regressions from the v0.14.0 audit (docs/audit-v0.14.0.md).

    P1: _print_sync ran sync_skill twice (double work, quiet defeated);
        ``askill install`` without <source> crashed in resolve_source(None).
    P2: ``status -q`` printed an orphan header; usage errors exited 0;
        --json was silently ignored on commands without JSON support;
        search --json --install out-of-range emitted two JSON documents.
    """

    def test_sync_runs_sync_skill_exactly_once(self):
        """P1: the duplicate ``sync_skill`` call must stay dead."""
        from agent_skill_manager.controllers import cli
        calls = []
        with patch.object(cli, "sync_skill", side_effect=lambda *a, **k: calls.append(k)):
            cli.main(["sync", "--quiet"])
        assert len(calls) == 1
        assert calls[0]["verbose"] is False

    def test_install_without_source_prints_help_and_exits_2(self, capsys):
        """P1: no traceback; the shorthand help block is shown; exit 2."""
        import pytest
        from agent_skill_manager.controllers import cli
        with pytest.raises(SystemExit) as ei:
            cli.main(["install"])
        assert ei.value.code == 2
        out = capsys.readouterr().out
        assert "Usage: askill install" in out
        assert "owner/repo@skill" in out

    def test_status_quiet_prints_rows_without_header(self, capsys):
        """P2: quiet strips decoration but keeps data rows - never an
        orphan header with zero rows."""
        from agent_skill_manager.controllers import cli
        entry = {"skill_name": "demo", "product_short": "t",
                 "product_name": "T", "status": "missing", "method": "symlink"}
        products = [{"name": "T", "short": "t", "macos_path": None,
                     "windows_path": None, "linux_path": None,
                     "sync_method": "symlink"}]
        with patch.object(cli, "get_status", return_value=[entry]), \
             patch.object(cli, "PRODUCTS", products):
            cli._print_status(quiet=True)
        out = capsys.readouterr().out
        assert "demo" in out                 # the data row
        assert "-----" not in out            # no separator line
        assert "score" not in out            # no header row

    def test_missing_required_positional_exits_2(self, capsys):
        """P2: usage errors surface as exit code 2, not 0."""
        import pytest
        from agent_skill_manager.controllers import cli
        with pytest.raises(SystemExit) as ei:
            cli.main(["remove"])
        assert ei.value.code == 2

    def test_unknown_command_exits_2(self, capsys):
        import pytest
        from agent_skill_manager.controllers import cli
        with pytest.raises(SystemExit) as ei:
            cli.main(["bogus-command"])
        assert ei.value.code == 2

    def test_json_flag_rejected_on_non_json_command(self):
        """P2: ``sync --json`` must fail loudly, not emit human text."""
        import pytest
        from agent_skill_manager.controllers import cli
        with pytest.raises(SystemExit) as ei:
            cli.main(["sync", "--json"])
        assert ei.value.code == 2

    def test_search_json_invalid_install_single_document(self, capsys):
        """P2: out-of-range --install emits ONE parseable JSON doc
        (error doc replaces the results doc, never concatenated)."""
        from agent_skill_manager.controllers import cli
        fake_results = [{"source": "owner/repo", "skill_id": "pdf",
                         "name": "PDF", "installs": 100}]
        with patch("agent_skill_manager.services.registry.search_skills",
                   return_value=fake_results):
            cli.main(["search", "pdf", "--json", "--install", "9"])
        parsed = json.loads(capsys.readouterr().out)   # raises if 2 docs
        assert "error" in parsed

    def test_search_json_valid_install_single_document(self, capsys):
        """Sanity: valid --install still yields one parseable JSON doc."""
        from agent_skill_manager.controllers import cli
        fake_results = [{"source": "owner/repo", "skill_id": "pdf",
                         "name": "PDF", "installs": 100}]
        with patch("agent_skill_manager.services.registry.search_skills",
                   return_value=fake_results), \
             patch.object(cli, "install_skill", return_value=True) as mock_inst:
            cli.main(["search", "pdf", "--json", "--install", "1"])
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["results"][0]["skill_id"] == "pdf"
        assert mock_inst.call_count == 1


class TestListJsonPublishFields:
    """v0.15.0 R3: list --json exposes publish-relevant frontmatter."""

    def test_version_and_description_zh_surface(self, tmp_path, capsys):
        from agent_skill_manager.controllers import cli
        d = tmp_path / "with-fields"
        d.mkdir()
        (d / "SKILL.md").write_text(
            "---\nname: with-fields\ndescription: x\nversion: 2.5.0\n"
            "description_zh: 测试\n---\nbody\n",
            encoding="utf-8",
        )
        bare = tmp_path / "bare"
        bare.mkdir()
        (bare / "SKILL.md").write_text(
            "---\nname: bare\ndescription: y\n---\nbody\n", encoding="utf-8",
        )
        with patch("agent_skill_manager.services.sync.CENTRAL_DIR", tmp_path), \
             patch("agent_skill_manager.controllers.cli.CENTRAL_DIR", tmp_path):
            cli._print_list(json_mode=True)
        entries = {e["skill"]: e for e in json.loads(capsys.readouterr().out)}
        assert entries["with-fields"]["version"] == "2.5.0"
        assert entries["with-fields"]["description_zh"] == "测试"
        assert entries["bare"]["version"] is None
        assert entries["bare"]["description_zh"] is None
