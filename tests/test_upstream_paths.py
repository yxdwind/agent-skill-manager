"""Tests for the read-only upstream path drift check (P1-6)."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from agent_skill_manager.config.products import LOCALAPPDATA, PRODUCTS
from agent_skill_manager.services import paths_export as helpers
from agent_skill_manager.services.paths_export import build_path_records

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "check_upstream_paths.py"

AGENTS_FIXTURE = """# Supported agents

| Agent | `--agent` | Project Path | Global Path |
|---|---|---|---|
| CodeBuddy | `codebuddy` | `.codebuddy/skills/` | `~/.codebuddy/skills/` |
| MiniMax Code | `minimax-code` | `.minimax/skills/` | `~/.minimax/skills/` |
| Qwen Code | `qwen-code` | `.qwen/skills/` | `~/.qwen/skills/` |
| Trae | `trae` | `.trae/skills/` | `~/.trae/skills/` |
| Trae CN | `trae-cn` | `.trae/skills/` | `~/.trae-cn/skills/` |
| ZCode | `zcode` | `.zcode/skills/` | `~/.zcode/skills/` |
"""

DSH_FIXTURE = """## 产品路径

| 产品 | 用户级路径 | 环境变量 | 项目级路径 |
|---|---|---|---|
| <img alt="Qoder CN"> Qoder CN | `~/.lingma/skills` | `DSH_LINGMA_HOME` | `<project>/.lingma/skills` |
| <img alt="WorkBuddy"> WorkBuddy | `~/.workbuddy/skills` | `DSH_WORKBUDDY_HOME` | `<project>/.workbuddy/skills` |
"""


def load_script():
    spec = importlib.util.spec_from_file_location("askill_upstream_check", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def records():
    return build_path_records(
        PRODUCTS, home=Path.home(), localappdata=LOCALAPPDATA,
    )


def test_parse_agents_and_dsh_tables():
    mod = load_script()
    agents = mod.parse_table(AGENTS_FIXTURE, "agents")
    dsh = mod.parse_table(DSH_FIXTURE, "dsh")
    assert len(agents) == 6
    assert {"label": "MiniMax Code", "path": "~/.minimax/skills/"} in agents
    assert len(dsh) == 2
    # DSH brand labels come from the <img alt="..."> attribute.
    assert {"label": "Qoder CN", "path": "~/.lingma/skills"} in dsh


def test_name_matching_is_conservative():
    """`Qwen Code` upstream must not silently cover `QwenWork`."""
    mod = load_script()
    entries = mod.parse_table(AGENTS_FIXTURE, "agents")
    by_short = {r["short"]: r for r in records()}
    assert mod.match_entries(by_short["minimax"], entries, helpers)
    assert mod.match_entries(by_short["codebuddy"], entries, helpers)
    assert not mod.match_entries(by_short["qwenwork"], entries, helpers)
    assert not mod.match_entries(by_short["workbuddy"], entries, helpers)


def test_comparison_finds_divergent_paths_only(tmp_path):
    mod = load_script()
    agents_file = tmp_path / "agents.md"
    agents_file.write_text(AGENTS_FIXTURE, encoding="utf-8")
    dsh_file = tmp_path / "dsh.md"
    dsh_file.write_text(DSH_FIXTURE, encoding="utf-8")

    report = mod.build_report(
        records(),
        [
            ("npx-skills", str(agents_file), "agents"),
            ("dsh", str(dsh_file), "dsh"),
        ],
        helpers=helpers, day="2026-11-15", timeout=1.0,
    )
    assert all(s["state"] == "ok" and s["entries"] > 0 for s in report["sources"])
    shorts = {d["short"] for d in report["drifts"]}
    # Known disagreements from the 2026-11-15 analysis.
    assert "minimax" in shorts          # ~/.agents/skills vs ~/.minimax/skills
    assert "qodercn" in shorts          # ~/.qoder-cn vs ~/.lingma
    assert "qodercnide" in shorts       # same shared-directory alias
    # Identical paths must not be reported.
    assert "codebuddy" not in shorts
    assert "zcode" not in shorts
    assert "workbuddy" not in shorts
    assert report["date"] == "2026-11-15"
    markdown = mod.render_markdown(report)
    assert "路径分歧" in markdown
    assert "MiniMax Code" in markdown


def test_unreachable_sources_are_unknown_and_exit_zero(tmp_path):
    paths = tmp_path / "paths.json"
    paths.write_text(json.dumps(records()), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable, str(SCRIPT),
            "--input", str(paths),
            "--agents", "http://127.0.0.1:1/none",
            "--dsh", "http://127.0.0.1:1/none",
            "--timeout", "1",
            "--date", "2026-11-15",
            "--json",
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert {s["state"] for s in report["sources"]} == {"unknown"}
    assert report["drifts"] == []
    assert "read-only" in report["note"].lower()


def test_cli_writes_markdown_report(tmp_path):
    paths = tmp_path / "paths.json"
    paths.write_text(json.dumps(records()), encoding="utf-8")
    agents_file = tmp_path / "agents.md"
    agents_file.write_text(AGENTS_FIXTURE, encoding="utf-8")
    dsh_file = tmp_path / "dsh.md"
    dsh_file.write_text(DSH_FIXTURE, encoding="utf-8")
    out = tmp_path / "report.md"

    result = subprocess.run(
        [
            sys.executable, str(SCRIPT),
            "--input", str(paths),
            "--agents", str(agents_file),
            "--dsh", str(dsh_file),
            "--date", "2026-11-15",
            "--output", str(out),
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    text = out.read_text(encoding="utf-8")
    assert "上游路径漂移复核（2026-11-15）" in text
    assert "MiniMax Code" in text
    assert "Qoder CN" in text
    assert "只读检查" in text
