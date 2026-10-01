"""Golden-sample regression tests for the security audit.

Each fixture under ``tests/fixtures/malicious/`` is a real skill directory
that triggers at least one audit rule. Loading from disk (instead of
inlining strings in test code) keeps the malicious patterns in one place
that mirrors what real attacks look like.

Adding a new fixture is one new directory + one new entry in
``EXPECTED_TRIGGERS``. There is no need to extend the test class.
"""
from pathlib import Path

import pytest
from agent_skill_manager.services.audit import analyze_skill_dir

FIXTURES_ROOT = Path(__file__).parent / "fixtures" / "malicious"


def _fixture_ids():
    """Yield pytest ids from each fixture's directory name."""
    return sorted(p.name for p in FIXTURES_ROOT.iterdir() if p.is_dir())


# Minimum severity count to expect after analysing the fixture. ``severity``
# is one of critical / high / low / info. If a fixture is meant to trigger
# ``critical`` patterns, use ``critical_min=1``; for a non-critical
# pattern use the lowest expected severity instead.
EXPECTED_TRIGGERS = {
    # critical-severity patterns
    "curl_pipe_sh":               {"critical_min": 1},
    "rm_rf_root":                 {"critical_min": 1},
    "nc_reverse_shell":           {"critical_min": 1},
    "powershell_iex_irm":         {"critical_min": 1},
    "prompt_injection_override":  {"critical_min": 1},
    "bypass_safety_directive":    {"critical_min": 1},
    "exfil_webhook":              {"medium_min": 1},  # webhook URL → medium
    # high-severity patterns
    "exec_dynamic_code":          {"high_min": 1},
    "shell_true_subprocess":      {"high_min": 1},
    "credential_grab":            {"high_min": 1},
    # file-integrity / binary
    "exe_payload":                {"high_min": 1},
    # low-severity patterns
    "hardcoded_api_key":          {"low_min": 1},
}


@pytest.mark.parametrize("name", _fixture_ids())
def test_fixture_triggers_audit_finding(name):
    """Each golden-sample fixture must trigger at least one finding of
    the severity the docs/audit says it should (locks regressions in the
    PROMPT_PATTERNS / CODE_PATTERNS / binary / size rules).

    We assert on summary counts (the contract) rather than overall score /
    verdict (which is a derived aggregate the audit grader decides
    independently). That way ``hardcoded_api_key`` (low finding, score
    97, verdict safe) still counts as detected - the audit noticed it,
    that's all the security guarantee we need.
    """
    if name not in EXPECTED_TRIGGERS:
        pytest.fail(
            f"missing EXPECTED_TRIGGERS entry for {name!r} - "
            "add it to test_malicious_fixtures.py"
        )
    expectations = EXPECTED_TRIGGERS[name]
    skill_dir = FIXTURES_ROOT / name
    report = analyze_skill_dir(skill_dir)
    summary = report["summary"]
    for severity in ("critical", "high", "medium", "low", "info"):
        floor = expectations.get(f"{severity}_min", 0)
        actual = summary.get(severity, 0)
        assert actual >= floor, (
            f"{name}: expected at least {floor} {severity}-severity "
            f"findings, got {actual}; report={report['findings'][:3]}"
        )
