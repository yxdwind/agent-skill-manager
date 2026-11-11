"""Tests for the attention-budget (residency) report."""

import json

from agent_skill_manager.services.sync.audit_report import residency_report


def _mk_skill(central, name, desc):
    d = central / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: %s\ndescription: %s\n---\n# body\n" % (name, desc),
        encoding="utf-8",
    )
    return d


def _short():
    return "x" * 15


def _normal():
    return "Convert PDF files to text and extract pages. Use when asked to parse PDFs."


def _long():
    return "y" * 500


def _over():
    return "z" * 1100


def test_residency_ranks_by_token_estimate(tmp_path):
    central = tmp_path / "central"
    _mk_skill(central, "s-short", _short())
    _mk_skill(central, "s-over", _over())
    _mk_skill(central, "s-normal", _normal())
    _mk_skill(central, "s-long", _long())

    rows = residency_report(central)
    names = [r["skill"] for r in rows]
    # ranking: over (1100) > long (500) > normal (~20) > short (15)
    assert names == ["s-over", "s-long", "s-normal", "s-short"]


def test_residency_suggestions(tmp_path):
    central = tmp_path / "central"
    _mk_skill(central, "s-short", _short())
    _mk_skill(central, "s-normal", _normal())
    _mk_skill(central, "s-long", _long())
    _mk_skill(central, "s-over", _over())

    rows = residency_report(central)
    by_name = {r["skill"]: r["suggestion"] for r in rows}
    assert by_name["s-over"] == "over spec limit - trim required"
    assert by_name["s-long"] == "consider trimming"
    assert by_name["s-normal"] == "ok"
    assert by_name["s-short"] == "too short - weak trigger"


def test_residency_cjk_counts_heavier_than_ascii(tmp_path):
    central = tmp_path / "central"
    # 100 CJK chars (~100 est tokens) vs 100 ASCII chars (~25 est tokens)
    _mk_skill(central, "cjk", "管" * 100)
    _mk_skill(central, "ascii", "a" * 100)
    rows = {r["skill"]: r["desc_tokens_est"] for r in residency_report(central)}
    assert rows["cjk"] > rows["ascii"]
    assert rows["ascii"] == 25


def test_residency_includes_dir_size(tmp_path):
    central = tmp_path / "central"
    _mk_skill(central, "s1", _normal())
    (central / "s1" / "notes.txt").write_text("payload" * 300, encoding="utf-8")
    rows = residency_report(central)
    assert rows[0]["dir_kb"] > 1


def test_residency_report_is_json_serializable(tmp_path):
    central = tmp_path / "central"
    _mk_skill(central, "s1", _normal())
    rows = residency_report(central)
    payload = json.dumps(rows, ensure_ascii=False)
    assert '"suggestion": "ok"' in payload
