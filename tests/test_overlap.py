"""Tests for deterministic description overlap (P1-9)."""

import json

from agent_skill_manager.controllers import cli
from agent_skill_manager.services.overlap import overlap_rows, render_overlap


def _skill(root, name, description):
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\nbody\n",
        encoding="utf-8",
    )
    return d


def test_overlapping_pair_is_ranked_and_stable(tmp_path):
    _skill(tmp_path, "weekly-a", "Generate a weekly report from git commits and pull requests")
    _skill(tmp_path, "weekly-b", "Generate a weekly report from git commits and pull requests summary")
    _skill(tmp_path, "translate", "Translate English text into French")
    rows = overlap_rows(tmp_path, threshold=0.5)
    pairs = {(r["skill_a"], r["skill_b"]) for r in rows}
    assert ("weekly-a", "weekly-b") in pairs
    assert not any("translate" in pair for pair in pairs)
    assert rows[0]["score"] >= 0.5
    assert rows[0]["shared"]
    assert rows[0]["suggestion"]
    assert rows == overlap_rows(tmp_path, threshold=0.5)  # stable order


def test_threshold_filters_and_empty_repo(tmp_path):
    assert overlap_rows(tmp_path, threshold=0.5) == []
    _skill(tmp_path, "one", "Alpha beta gamma")
    _skill(tmp_path, "two", "Delta epsilon zeta")
    assert overlap_rows(tmp_path, threshold=0.5) == []
    assert "No description pairs" in render_overlap([], 0.5)


def test_cjk_bigrams_are_compared(tmp_path):
    _skill(tmp_path, "cn-a", "生成周报并汇总代码提交")
    _skill(tmp_path, "cn-b", "生成周报并汇总代码提交记录")
    rows = overlap_rows(tmp_path, threshold=0.5)
    assert {(r["skill_a"], r["skill_b"]) for r in rows} == {("cn-a", "cn-b")}
    assert "Lexical similarity only" in render_overlap(rows, 0.5)


def test_cli_overlap_json(tmp_path, capsys, monkeypatch):
    _skill(tmp_path, "a", "Generate a weekly report from git commits")
    _skill(tmp_path, "b", "Generate a weekly report from git commits today")
    monkeypatch.setattr(cli, "CENTRAL_DIR", tmp_path)
    cli.main(["audit", "--overlap", "--json", "--quiet"])
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list) and data
    assert {"skill_a", "skill_b", "score", "shared", "suggestion"} <= data[0].keys()
