"""Tests for askill doctor (environment & repository health diagnostics)."""

import json
from pathlib import Path
from unittest.mock import patch

import agent_skill_manager.services.doctor as doctor_mod
import pytest
from agent_skill_manager.services.doctor import doctor_report


@pytest.fixture(autouse=True)
def _no_real_proxies(monkeypatch):
    """Isolate from the machine's real git/env proxy config (probe timeouts)."""
    monkeypatch.setattr(doctor_mod, "_configured_proxies", list)


def _prod(short, pdir, method="symlink", settings_file=None):
    d = {
        "name": short.title(), "short": short, "sync_method": method,
        "windows_path": str(pdir), "macos_path": str(pdir), "linux_path": str(pdir),
    }
    if settings_file is not None:
        d["settings_file"] = settings_file
    return d


def _mk_skill(central, name):
    d = central / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: d\n---\nbody", encoding="utf-8")


def _healthy_env(tmp_path):
    central = tmp_path / "central"
    _mk_skill(central, "alpha")
    pdir = tmp_path / "prodA"
    pdir.mkdir()
    return central, [_prod("proda", pdir)]


def test_healthy_machine_reports_ok(tmp_path):
    central, products = _healthy_env(tmp_path)
    with patch.object(doctor_mod, "PRODUCTS", products):
        report = doctor_report(central=central, verbose=False)
    assert report["ok"] is True
    assert report["central"]["skills"] == 1
    assert report["products"][0]["dir_exists"] is True
    assert report["products"][0]["broken_links"] == 0


def test_broken_links_and_drift_raise_warnings(tmp_path):
    central, products = _healthy_env(tmp_path)
    with patch.object(doctor_mod, "PRODUCTS", products), \
         patch.object(doctor_mod, "_scan_product_dir",
                      return_value={"links": 2, "broken_links": 1,
                                    "real_dirs": 1, "fork_dirs": 1}):
        report = doctor_report(central=central, verbose=False)
    ids = {c["id"]: c for c in report["checks"]}
    assert ids["broken-links"]["severity"] == "warn"
    assert ids["drift-candidates"]["severity"] == "warn"
    assert "Proda" in ids["drift-candidates"]["detail"]
    assert report["ok"] is True  # warnings do not fail the report


def test_unreachable_proxy_is_a_fail(tmp_path):
    central, products = _healthy_env(tmp_path)
    with patch.object(doctor_mod, "PRODUCTS", products), \
         patch.object(doctor_mod, "_configured_proxies",
                      return_value=[{"source": "git config http.proxy",
                                     "url": "http://127.0.0.1:7897"}]), \
         patch.object(doctor_mod, "_probe_tcp", return_value=False):
        report = doctor_report(central=central, verbose=False)
    assert report["ok"] is False
    proxy = [c for c in report["checks"] if c["id"].startswith("proxy")]
    assert proxy and proxy[0]["severity"] == "fail"
    assert "--unset http.proxy" in proxy[0]["detail"]


def test_reachable_proxy_is_ok(tmp_path):
    central, products = _healthy_env(tmp_path)
    with patch.object(doctor_mod, "PRODUCTS", products), \
         patch.object(doctor_mod, "_configured_proxies",
                      return_value=[{"source": "git config http.proxy",
                                     "url": "http://127.0.0.1:7897"}]), \
         patch.object(doctor_mod, "_probe_tcp", return_value=True):
        report = doctor_report(central=central, verbose=False)
    proxy = [c for c in report["checks"] if c["id"].startswith("proxy")]
    assert proxy[0]["severity"] == "ok"
    assert report["ok"] is True


def test_missing_git_is_a_fail(tmp_path):
    central, products = _healthy_env(tmp_path)
    with patch.object(doctor_mod, "PRODUCTS", products), \
         patch.object(doctor_mod, "_git_version", return_value=None):
        report = doctor_report(central=central, verbose=False)
    git = [c for c in report["checks"] if c["id"] == "git"]
    assert git[0]["severity"] == "fail"
    assert report["ok"] is False


def test_orphan_sources_warned(tmp_path):
    central, products = _healthy_env(tmp_path)
    (central / ".askill-sources.json").write_text(
        json.dumps({"ghost": {"repo_url": "https://github.com/a/b"}}), encoding="utf-8"
    )
    with patch.object(doctor_mod, "PRODUCTS", products):
        report = doctor_report(central=central, verbose=False)
    assert report["central"]["orphan_sources"] == ["ghost"]
    orphan = [c for c in report["checks"] if c["id"] == "orphan-sources"]
    assert orphan and orphan[0]["severity"] == "warn"


def test_settings_lock_detected(tmp_path, capsys):
    central, products = _healthy_env(tmp_path)
    sf = tmp_path / "settings.json"
    sf.write_text("{}", encoding="utf-8")
    (tmp_path / "prodB").mkdir()
    products.append(_prod("prodb", tmp_path / "prodB", settings_file=sf))
    with patch.object(doctor_mod, "PRODUCTS", products), \
         patch.object(doctor_mod, "_settings_writable", return_value=False):
        doctor_report(central=central, verbose=True)
    out = capsys.readouterr().out
    assert "Prodb" in out and "LOCKED" in out


def test_product_path_none_is_handled(tmp_path):
    central, products = _healthy_env(tmp_path)
    with patch.object(doctor_mod, "PRODUCTS", products), \
         patch.object(doctor_mod, "get_product_path", return_value=None):
        report = doctor_report(central=central, verbose=False)
    assert report["products"][0]["dir_exists"] is False


def test_real_dir_counted_without_links(tmp_path):
    central, products = _healthy_env(tmp_path)
    pdir = Path(products[0]["windows_path"])
    (pdir / "manual-skill").mkdir()
    (pdir / "notes.txt").write_text("x", encoding="utf-8")
    with patch.object(doctor_mod, "PRODUCTS", products):
        report = doctor_report(central=central, verbose=False)
    assert report["products"][0]["real_dirs"] == 1
    assert report["products"][0]["links"] == 0


def test_report_is_json_serializable(tmp_path):
    central, products = _healthy_env(tmp_path)
    with patch.object(doctor_mod, "PRODUCTS", products):
        report = doctor_report(central=central, verbose=False)
    payload = json.dumps(report, ensure_ascii=False)
    assert '"ok": true' in payload


def test_cli_exit_code_mapping(tmp_path):
    from agent_skill_manager.controllers import cli

    ns = type("NS", (), {"json_mode": False})()
    with patch.object(cli, "doctor_report",
                      return_value={"ok": True, "checks": [], "central": {}, "products": []}):
        assert cli._cmd_doctor(ns) == 0
    with patch.object(cli, "doctor_report",
                      return_value={"ok": False, "checks": [], "central": {}, "products": []}):
        assert cli._cmd_doctor(ns) == 1
