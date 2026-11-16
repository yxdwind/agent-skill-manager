"""Tests for the portable product-path export (P1-5)."""

import json
import subprocess
import sys
from pathlib import Path

from agent_skill_manager.config.products import LOCALAPPDATA, PRODUCTS
from agent_skill_manager.controllers.cli import main
from agent_skill_manager.services.paths_export import (
    _portable,
    build_path_records,
    match_upstream,
    parse_upstream_agents,
    render_agents_md,
)

REPO = Path(__file__).resolve().parents[1]

# A trimmed, real-shaped snapshot of vercel-labs/skills docs/agents.md
# (2026-11-15). Kept local so the suite never touches the network.
UPSTREAM_SNIPPET = """# Supported agents

| Agent | `--agent` | Project Path | Global Path |
|-------|-----------|--------------|-------------|
| CodeBuddy | `codebuddy` | `.codebuddy/skills/` | `~/.codebuddy/skills/` |
| Qwen Code | `qwen-code` | `.qwen/skills/` | `~/.qwen/skills/` |
| Trae CN | `trae-cn` | `.trae/skills/` | `~/.trae-cn/skills/` |
| Cline, Kimi Code CLI, Zed | `kimi-code-cli` | `.agents/skills/` | `~/.agents/skills/` |
| ZCode | `zcode` | `.zcode/skills/` | `~/.zcode/skills/` |
"""


def test_portable_renders_home_and_localappdata(tmp_path):
    home = tmp_path / "home"
    local = home / "AppData" / "Local"
    assert _portable(home / ".workbuddy" / "skills", home=home, localappdata=local) == (
        "~/.workbuddy/skills"
    )
    assert _portable(local / "DoubaoWork" / "x", home=home, localappdata=local) == (
        "%LOCALAPPDATA%/DoubaoWork/x"
    )
    assert _portable(None, home=home, localappdata=local) is None
    # Unknown roots must not be silently rewritten.
    assert _portable(Path("/opt/skills"), home=home, localappdata=local) == "/opt/skills"


def test_records_are_complete_and_portable():
    records = build_path_records(
        PRODUCTS, home=Path.home(), localappdata=LOCALAPPDATA,
    )
    assert len(records) == len(PRODUCTS) == 15
    expected = {
        "name", "short", "sync_method", "macos_path", "windows_path",
        "linux_path", "extra_dirs", "settings_file", "settings_mode",
        "required_frontmatter", "note", "shared_with",
    }
    home_posix = str(Path.home()).replace("\\", "/")
    for rec in records:
        assert expected.issubset(rec.keys())
        for key in ("macos_path", "windows_path", "linux_path", "settings_file"):
            value = rec[key]
            assert value is None or home_posix not in value, (rec["short"], key, value)
            assert value is None or "\\" not in value, (rec["short"], key, value)
        assert set(rec["extra_dirs"]) == {"macos", "windows", "linux"}


def test_shared_with_is_derived_not_declared():
    by_short = {
        r["short"]: r for r in build_path_records(
            PRODUCTS, home=Path.home(), localappdata=LOCALAPPDATA,
        )
    }
    assert "traesolo" in by_short["traecn"]["shared_with"]
    assert "traecn" in by_short["traesolo"]["shared_with"]
    assert "qodercnide" in by_short["qodercn"]["shared_with"]
    assert "qodercn" in by_short["qodercnide"]["shared_with"]
    assert by_short["dumate"]["shared_with"] == []
    assert by_short["workbuddy"]["shared_with"] == []
    assert by_short["qwenwork"]["required_frontmatter"] == [
        "name", "version", "description", "description_zh",
    ]


def test_upstream_matching_is_conservative():
    records = build_path_records(
        PRODUCTS, home=Path.home(), localappdata=LOCALAPPDATA,
    )
    by_short = {r["short"]: r for r in records}
    tokens = parse_upstream_agents(UPSTREAM_SNIPPET)
    assert match_upstream(by_short["codebuddy"], tokens) is not None
    assert match_upstream(by_short["traecn"], tokens) is not None
    assert match_upstream(by_short["kimi"], tokens) is not None  # kimi -> kimi-code-cli
    assert match_upstream(by_short["zcode"], tokens) is not None
    # A similarly named but different product must NOT be marked covered.
    assert match_upstream(by_short["qwenwork"], tokens) is None
    assert match_upstream(by_short["workbuddy"], tokens) is None
    assert match_upstream(by_short["dumate"], tokens) is None


def test_render_emits_table_and_gap_report():
    records = build_path_records(
        PRODUCTS, home=Path.home(), localappdata=LOCALAPPDATA,
    )
    text = render_agents_md(
        records, upstream_text=UPSTREAM_SNIPPET, generated_on="2026-11-15",
    )
    assert "exported 2026-11-15" in text
    assert "~/.workbuddy/skills" in text
    assert "%LOCALAPPDATA%/DoubaoWork" in text
    assert "Not covered upstream" in text
    assert "WorkBuddy" in text
    assert text.count("\n| ") >= len(PRODUCTS)  # one row per product


def test_cli_paths_flag_emits_full_records(capsys):
    main(["products", "--json", "--paths", "--quiet"])
    data = json.loads(capsys.readouterr().out)
    assert len(data) == len(PRODUCTS)
    assert "macos_path" in data[0]
    assert "shared_with" in data[0]
    assert "primary_path" not in data[0]


def test_cli_default_json_shape_unchanged(capsys):
    """Existing consumers (shell completion) rely on the flat shape."""
    main(["products", "--json", "--quiet"])
    data = json.loads(capsys.readouterr().out)
    assert len(data) == len(PRODUCTS)
    assert "primary_path" in data[0]
    assert "macos_path" not in data[0]


def test_export_script_works_offline_with_input_and_upstream(tmp_path):
    records = build_path_records(
        PRODUCTS, home=Path.home(), localappdata=LOCALAPPDATA,
    )
    paths_file = tmp_path / "paths.json"
    paths_file.write_text(json.dumps(records), encoding="utf-8")
    upstream_file = tmp_path / "agents.md"
    upstream_file.write_text(UPSTREAM_SNIPPET, encoding="utf-8")
    out_file = tmp_path / "fragment.md"

    result = subprocess.run(
        [
            sys.executable, str(REPO / "scripts" / "export_agents_md.py"),
            "--input", str(paths_file),
            "--upstream", str(upstream_file),
            "--date", "2026-11-15",
            "--output", str(out_file),
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "15 products" in result.stdout
    fragment = out_file.read_text(encoding="utf-8")
    assert "Not covered upstream" in fragment
    assert "WorkBuddy" in fragment
    assert "exported 2026-11-15" in fragment
