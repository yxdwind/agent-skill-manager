"""Tests for the one-time first-run welcome banner (services.welcome)."""

from pathlib import Path
from unittest.mock import patch

from agent_skill_manager.services import welcome


def test_welcome_prints_once(tmp_path, capsys):
    """First call prints the banner, second call is silent."""
    assert welcome.maybe_print_welcome(central=tmp_path) is True
    out = capsys.readouterr().out
    assert "agent-skill-manager" in out
    assert "askill status" in out
    assert "github.com/yxdwind/agent-skill-manager" in out

    assert welcome.maybe_print_welcome(central=tmp_path) is False
    assert capsys.readouterr().out == ""


def test_welcome_silent_in_quiet_and_json(tmp_path):
    """quiet / json_mode calls never print and never create the marker."""
    assert welcome.maybe_print_welcome(quiet=True, central=tmp_path) is False
    assert welcome.maybe_print_welcome(json_mode=True, central=tmp_path) is False
    assert not (tmp_path / welcome.WELCOME_FILE).exists()


def test_welcome_tolerant_to_fs_errors(tmp_path, capsys, monkeypatch):
    """A failing filesystem must suppress the banner, not raise."""
    marker = tmp_path / welcome.WELCOME_FILE
    monkeypatch.setattr(
        Path, "exists",
        lambda self: (_ for _ in ()).throw(OSError("locked")) if self == marker
        else Path.exists_original(self),  # type: ignore[attr-defined]
    )
    assert welcome.maybe_print_welcome(central=tmp_path) is False
    assert capsys.readouterr().out == ""


def test_welcome_marker_in_central_repo(tmp_path):
    """Marker file lands inside the central dir, not somewhere global."""
    central = tmp_path / "central"
    welcome.maybe_print_welcome(central=central)
    assert (central / welcome.WELCOME_FILE).exists()


def test_cli_main_shows_welcome_once(tmp_path, capsys):
    """End-to-end: running a real command via main() prints the banner
    once across invocations, and quiet mode suppresses it."""
    central = tmp_path / "central"
    central.mkdir()
    from agent_skill_manager.controllers import cli

    def _fake_products(quiet=False, json_mode=False):
        return 0

    with patch("agent_skill_manager.controllers.cli.CENTRAL_DIR", central), \
         patch("agent_skill_manager.services.welcome.CENTRAL_DIR", central), \
         patch.object(cli, "_print_products", _fake_products):
        cli.main(["products"])
        first = capsys.readouterr().out
        assert "github.com/yxdwind/agent-skill-manager" in first

        cli.main(["products"])
        second = capsys.readouterr().out
        assert "github.com/yxdwind/agent-skill-manager" not in second

        cli.main(["products", "--quiet"])
        third = capsys.readouterr().out
        assert "github.com/yxdwind/agent-skill-manager" not in third
