"""Static security audit for agent skills.

Zero-dependency static analysis of a skill directory. Detects:
  - prompt injection / instruction-override patterns in SKILL.md
  - dangerous code patterns in bundled scripts (exec, eval, shell pipes, ...)
  - data exfiltration patterns (sensitive paths, secrets, webhooks, outbound POST)
  - network access in instructions and scripts
  - binary payloads (executables and unexpected binary data)
  - file integrity issues (missing SKILL.md, oversized files, too many files)

Scoring: start at 100 and subtract weighted severities (capped per category).
Grade: A >= 90, B >= 80, C >= 70, D >= 60, F < 60.
Verdict: safe / caution / risky / dangerous.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..models.report import Finding, SkillReport

# ---------------------------------------------------------------- constants

SCRIPT_EXTS = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".sh", ".bash", ".zsh",
    ".bat", ".cmd", ".ps1", ".psm1", ".rb", ".pl", ".go", ".rs", ".java", ".exs",
}
MARKDOWN_EXTS = {".md", ".markdown"}
# Extensions treated as known-safe binary data files (images, fonts, archives)
BINARY_DATA_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".bmp",
    ".pdf", ".woff", ".woff2", ".ttf", ".otf", ".zip", ".gz", ".tar", ".7z",
}
# Extensions treated as executable / native binaries
BINARY_EXEC_EXTS = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".scr", ".jar", ".class",
    ".msi", ".pkg", ".app", ".o", ".a", ".sys", ".drv",
}
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 50 * 1024 * 1024
MAX_FILES = 200

# Development artifacts skipped entirely (not skill payload).
SKIP_DIRS = {".git", ".hg", ".svn", "__pycache__", "node_modules",
             ".venv", "venv", ".idea", ".vscode", ".DS_Store", "dist", "build"}
SKIP_FILE_SUFFIXES = {".pyc", ".pyo", ".class", ".log", ".tmp", ".swp"}
SKIP_FILE_NAMES = {".DS_Store", "Thumbs.db"}

SEVERITY_WEIGHTS = {"critical": 40, "high": 20, "medium": 10, "low": 3, "info": 0}
_CATEGORY_CAP = 40

# ---------------------------------------------------------------- patterns

# (severity, regex, message) — matched against SKILL.md / markdown content.
PROMPT_PATTERNS = [
    ("critical", re.compile(r"ignore\s+(all\s+|any\s+)?(previous|prior|earlier|above)\s+(instructions?|rules?|guidelines?|directives?)", re.IGNORECASE),
     "prompt injection: instruction override detected"),
    ("critical", re.compile(r"disregard\s+(all\s+|any\s+)?(previous|prior|earlier|above|safety)?\s*(instructions?|rules?|guidelines?|directives?)", re.IGNORECASE),
     "prompt injection: 'disregard instructions' pattern"),
    ("critical", re.compile(r"bypass\s+(the\s+|all\s+)?(safety|security|sandbox|content\s*filter|moderation)", re.IGNORECASE),
     "prompt injection: bypass-safety language"),
    ("critical", re.compile(r"(steal|exfiltrate|leak)\s+(the\s+|user'?s\s+|all\s+)?(data|files|credentials|secrets|conversation)", re.IGNORECASE),
     "exfiltration instruction in prompt text"),
    ("critical", re.compile(r"never\s+(ask|request|seek)\s+(for\s+)?(permission|consent|confirmation|approval)", re.IGNORECASE),
     "instructed to act without user permission"),
    ("critical", re.compile(r"do\s+not\s+(follow|obey|comply\s+with)\s+(any\s+|the\s+)?(safety|security|policy|policies|rules?|guardrails?)", re.IGNORECASE),
     "instructed to ignore safety rules"),
    ("critical", re.compile(r"(turn|switch)\s+off\s+(safety|security|guardrails?)", re.IGNORECASE),
     "instructed to disable safety features"),
    ("critical", re.compile(r"(disable|deactivate)\s+(all\s+)?(safety|security|guardrails?|sandbox)", re.IGNORECASE),
     "instructed to deactivate safeguards"),
    ("high", re.compile(r"(hide|conceal)\s+(your|this|the)\s+(activity|actions?|behavior|tracks?)", re.IGNORECASE),
     "instructed to hide its activity"),
    ("high", re.compile(r"do\s+not\s+(tell|inform|disclose|reveal|mention)\s+(the\s+)?user", re.IGNORECASE),
     "instructed to withhold information from the user"),
    ("high", re.compile(r"(silently|secretly)\s+(send|upload|copy|exfiltrate)", re.IGNORECASE),
     "covert data transfer instruction"),
    ("high", re.compile(r"without\s+(the\s+)?user'?s\s+(knowledge|awareness|consent|permission)", re.IGNORECASE),
     "acting without user awareness"),
    ("high", re.compile(r"(send|upload|post|transmit)\s+(this|all|the|collected)\s+(data|files|conversation|content)\s+to", re.IGNORECASE),
     "instructed to send data to an external party"),
    ("medium", re.compile(r"(discord(app)?\.com/api/webhooks|hooks\.slack\.com/services|open\.feishu\.cn/open-apis|qyapi\.weixin\.qq\.com/cgi-bin/webhook|api\.telegram\.org/bot)", re.IGNORECASE),
     "webhook URL in instructions"),
    ("medium", re.compile(r"(phishing|keylog\w*|record\s+keystrokes|screen\s*capture)", re.IGNORECASE),
     "credential-harvesting language"),
    ("low", re.compile(r"https?://[^\s\)\]\">]+", re.IGNORECASE),
     "network endpoint referenced in instructions"),
]

# (severity, regex, message) — matched against script files.
CODE_PATTERNS = [
    ("critical", re.compile(r"(curl|wget)\b[^\n|]{0,200}\|\s*(ba)?sh\b", re.IGNORECASE),
     "remote content piped to shell (curl|sh)"),
    ("critical", re.compile(r"(curl|wget)\b[^\n|]{0,200}\|\s*zsh\b", re.IGNORECASE),
     "remote content piped to zsh"),
    ("critical", re.compile(r"irm\s+\S+\s*\|\s*iex", re.IGNORECASE),
     "PowerShell download-and-execute (irm | iex)"),
    ("critical", re.compile(r"\bnc\s+-e\b", re.IGNORECASE),
     "netcat reverse shell"),
    ("critical", re.compile(r"\bbash\s+-i\s*>&", re.IGNORECASE),
     "interactive reverse shell"),
    ("critical", re.compile(r"\brm\s+-rf\s+(/|/tmp|/var|/usr|/etc|~)", re.IGNORECASE),
     "destructive recursive delete of system paths"),
    ("critical", re.compile(r"\bmkfs\b", re.IGNORECASE),
     "filesystem format command"),
    ("critical", re.compile(r"\bformat\s+[c-zC-Z]:", re.IGNORECASE),
     "Windows drive format command"),
    ("high", re.compile(r"\bexec\s*\(", re.IGNORECASE),
     "dynamic code execution (exec)"),
    ("high", re.compile(r"subprocess\b[\s\S]{0,120}?shell\s*=\s*True", re.IGNORECASE),
     "shell=True subprocess call"),
    ("high", re.compile(r"Invoke-Expression", re.IGNORECASE),
     "PowerShell Invoke-Expression"),
    ("high", re.compile(r"\biex\s*\(", re.IGNORECASE),
     "PowerShell iex call"),
    ("high", re.compile(r"-EncodedCommand", re.IGNORECASE),
     "PowerShell encoded command"),
    ("high", re.compile(r"new\s+Function\s*\(", re.IGNORECASE),
     "JavaScript dynamic function constructor"),
    ("high", re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
     "recursive delete (rm -rf)"),
    ("high", re.compile(r"\bdd\s+if=", re.IGNORECASE),
     "raw disk write (dd)"),
    ("high", re.compile(r"\bshutdown\b", re.IGNORECASE),
     "system shutdown command"),
    ("high", re.compile(r"(\.ssh|\.aws|\.gnupg|id_rsa|id_ed25519|\.netrc|credentials)", re.IGNORECASE),
     "reads sensitive credential files"),
    ("medium", re.compile(r"\beval\s*\(", re.IGNORECASE),
     "dynamic code evaluation (eval)"),
    ("medium", re.compile(r"os\.system\s*\(", re.IGNORECASE),
     "shell command via os.system"),
    ("medium", re.compile(r"__import__\s*\(", re.IGNORECASE),
     "dynamic module import"),
    ("medium", re.compile(r"base64\.b64decode\s*\(", re.IGNORECASE),
     "base64 payload decoding"),
    ("medium", re.compile(r"\bDownloadString\b", re.IGNORECASE),
     "PowerShell DownloadString"),
    ("medium", re.compile(r"\bDownloadFile\b", re.IGNORECASE),
     "PowerShell DownloadFile"),
    ("medium", re.compile(r"child_process", re.IGNORECASE),
     "JavaScript child_process usage"),
    ("medium", re.compile(r"curl\s+\S+\s+(-d\b|--data\b|-X\s+POST)", re.IGNORECASE),
     "outbound POST via curl"),
    ("medium", re.compile(r"requests\.(post|put)\s*\(", re.IGNORECASE),
     "outbound data upload via requests"),
    ("low", re.compile(r"\.env", re.IGNORECASE),
     "references .env (possible secrets file)"),
    ("low", re.compile(r"(api[_-]?key|access[_-]?token|secret[_-]?key|client[_-]?secret)\s*[:=]", re.IGNORECASE),
     "hardcoded secret in code"),
    ("low", re.compile(r"fetch\s*\(\s*['\"]https?://", re.IGNORECASE),
     "network fetch to remote URL"),
    ("low", re.compile(r"https?://", re.IGNORECASE),
     "network access in script"),
]


def _read_bytes(path: Path) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read(4096)
    except OSError:
        return b""


def _is_binary(chunk: bytes) -> bool:
    return b"\x00" in chunk


def _scan_text(
    content: str,
    patterns: list[tuple[str, re.Pattern[str], str]],
    path: Path,
    findings: list[Finding],
    category: str,
) -> None:
    """Match patterns against text content; one finding per (file, pattern)."""
    seen = set()
    for severity, regex, message in patterns:
        for i, line in enumerate(content.splitlines(), 1):
            if regex.search(line):
                key = (path.name, regex.pattern)
                if key in seen:
                    break
                seen.add(key)
                findings.append({
                    "severity": severity,
                    "category": category,
                    "file": str(path),
                    "line": i,
                    "pattern": regex.pattern,
                    "message": message,
                })
                break


def _grade(score: int) -> tuple[str, str]:
    if score >= 90:
        return "A", "safe"
    if score >= 80:
        return "B", "safe"
    if score >= 70:
        return "C", "caution"
    if score >= 60:
        return "D", "risky"
    return "F", "dangerous"


def _score(findings: list[Finding]) -> int:
    """100 minus weighted severities, capped per category."""
    per_category: dict[str, int] = {}
    for f in findings:
        w = SEVERITY_WEIGHTS.get(f["severity"], 0)
        if w == 0:
            continue
        per_category[f["category"]] = per_category.get(f["category"], 0) + w
    total = sum(min(v, _CATEGORY_CAP) for v in per_category.values())
    return max(0, 100 - total)


def analyze_skill_dir(skill_dir: Path) -> SkillReport:
    """Run the full static audit on one skill directory.

    Returns a :class:`SkillReport` (TypedDict) with:
      skill, path, files, total_bytes, score, grade, verdict,
      summary {critical/high/medium/low/info: count}, findings [ ... ]
    """
    skill_dir = Path(skill_dir)
    findings: list[Finding] = []

    skill_md = skill_dir / "SKILL.md"
    files = []
    if skill_dir.exists():
        for p in skill_dir.rglob("*"):
            if not p.is_file():
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.suffix.lower() in SKIP_FILE_SUFFIXES:
                continue
            if p.name in SKIP_FILE_NAMES:
                continue
            files.append(p)
    total_bytes = sum(p.stat().st_size for p in files)

    # --- file integrity -------------------------------------------------
    if not skill_dir.exists():
        findings.append({
            "severity": "critical", "category": "file-integrity",
            "file": str(skill_dir), "line": None, "pattern": "",
            "message": "skill directory does not exist",
        })
    elif not skill_md.exists():
        findings.append({
            "severity": "critical", "category": "file-integrity",
            "file": str(skill_dir), "line": None, "pattern": "",
            "message": "SKILL.md is missing",
        })
    else:
        raw = _read_bytes(skill_md)
        if len(raw) < 20:
            findings.append({
                "severity": "high", "category": "file-integrity",
                "file": str(skill_md), "line": None, "pattern": "",
                "message": "SKILL.md is suspiciously small (< 20 bytes)",
            })

    if len(files) > MAX_FILES:
        findings.append({
            "severity": "medium", "category": "file-integrity",
            "file": str(skill_dir), "line": None, "pattern": "",
            "message": f"unusually many files ({len(files)} > {MAX_FILES})",
        })
    if total_bytes > MAX_TOTAL_BYTES:
        findings.append({
            "severity": "medium", "category": "file-integrity",
            "file": str(skill_dir), "line": None, "pattern": "",
            "message": f"total size {total_bytes // 1024 // 1024}MB exceeds {MAX_TOTAL_BYTES // 1024 // 1024}MB",
        })

    # --- per-file scans --------------------------------------------------
    for f in files:
        rel = f.relative_to(skill_dir)
        if f.is_symlink():
            findings.append({
                "severity": "medium", "category": "file-integrity",
                "file": str(f), "line": None, "pattern": "",
                "message": "symlink inside skill directory",
            })
            continue

        chunk = _read_bytes(f)
        if _is_binary(chunk):
            if f.suffix.lower() in BINARY_EXEC_EXTS:
                findings.append({
                    "severity": "high", "category": "binary-file",
                    "file": str(f), "line": None, "pattern": f.suffix,
                    "message": f"executable binary file ({f.suffix})",
                })
            elif f.suffix.lower() not in BINARY_DATA_EXTS:
                findings.append({
                    "severity": "high", "category": "binary-file",
                    "file": str(f), "line": None, "pattern": f.suffix or "(none)",
                    "message": "unexpected binary data (not an image/font/archive)",
                })
            else:
                findings.append({
                    "severity": "low", "category": "binary-file",
                    "file": str(f), "line": None, "pattern": f.suffix,
                    "message": "binary data file bundled with skill",
                })
            continue

        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        if f.suffix.lower() in MARKDOWN_EXTS:
            _scan_text(content, PROMPT_PATTERNS, rel, findings, "prompt-injection")
        elif f.suffix.lower() in SCRIPT_EXTS:
            _scan_text(content, CODE_PATTERNS, rel, findings, "dangerous-code")

        if f.stat().st_size > MAX_FILE_BYTES:
            findings.append({
                "severity": "high", "category": "file-integrity",
                "file": str(f), "line": None, "pattern": "",
                "message": f"file too large ({f.stat().st_size // 1024 // 1024}MB)",
            })

    # --- score -----------------------------------------------------------
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    # Renamed from ``f`` -> ``finding`` so mypy doesn't reuse the outer
    # loop's ``f: Path`` type from the per-file scan above.
    for finding in findings:
        summary[finding["severity"]] = summary.get(finding["severity"], 0) + 1

    score = _score(findings)
    grade, verdict = _grade(score)

    return {
        "skill": skill_dir.name,
        "path": str(skill_dir),
        "files": len(files),
        "total_bytes": total_bytes,
        "score": score,
        "grade": grade,
        "verdict": verdict,
        "summary": summary,
        "findings": findings,
    }


def analyze_all(central_dir: Path, max_workers: int = 8) -> list[SkillReport]:
    """Audit every skill directory under the central repository.

    Each ``analyze_skill_dir`` call is I/O bound (reads SKILL.md and any
    bundled scripts), so we run them concurrently via a small thread
    pool. ``pool.map`` preserves the sorted input order in the output,
    matching the previous serial behaviour so existing callers (and the
    tests that check report order) keep working.
    """
    central_dir = Path(central_dir)
    if not central_dir.exists():
        return []
    skill_dirs = sorted(
        d for d in central_dir.iterdir()
        if d.is_dir() and not d.is_symlink()
    )
    if not skill_dirs:
        return []
    with ThreadPoolExecutor(
        max_workers=min(len(skill_dirs), max_workers),
    ) as pool:
        return list(pool.map(analyze_skill_dir, skill_dirs))
