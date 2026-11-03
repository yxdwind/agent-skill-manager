"""Skill installation: local paths, GitHub URLs, and skills.sh shorthands."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import agent_skill_manager.services.sync as _pkg

from .audit_report import audit_skill


def install_skill(
    source: str,
    sync: bool = False,
    audit: bool = False,
    verbose: bool = True,
    no_audit: bool = False,
) -> bool:
    """Install a skill to the central repository.

    Args:
        source: Local path, GitHub URL, or skills.sh-ecosystem shorthand
            (``owner/repo``, ``owner/repo@skill``, ``https://skills.sh/...``).
        sync: If True, also sync the installed skill to all products.
        audit: If True, print the full audit report after install.
        verbose: Print progress messages.
        no_audit: If True, skip the post-install checks entirely.  By
            default every install runs the agentskills.io spec check plus a
            security audit scan (v0.12.0) - safe results print one line,
            risky/dangerous results warn loudly regardless of verbosity.

    Returns:
        True if installation succeeded.
    """
    _pkg.CENTRAL_DIR.mkdir(parents=True, exist_ok=True)

    from ..registry import resolve_source

    resolved = resolve_source(source)
    if resolved:
        if verbose:
            hint = f" (skill: {resolved['skill']})" if resolved["skill"] else ""
            print(f"skills.sh shorthand detected{hint}: {resolved['original']}")
        name, ok = _pkg._install_from_url(
            resolved["repo_url"], verbose=verbose, skill_hint=resolved["skill"],
        )
    elif source.startswith("http"):
        name, ok = _pkg._install_from_url(source, verbose=verbose)
    else:
        name, ok = _install_from_local(source, verbose=verbose)

    if ok and name and not no_audit:
        _post_install_checks(name, full_report=audit, verbose=verbose)

    if ok and sync and name:
        if verbose:
            print()
        _pkg.sync_skill(name, verbose=verbose)

    return ok

def _post_install_checks(skill_name: str, full_report: bool = False, verbose: bool = True) -> None:
    """Spec + security checks after install (v0.12.0: on by default).

    Quiet mode (default): one ``[check]`` summary line when verbose; spec
    errors and risky/dangerous verdicts print their details in any mode.
    ``full_report=True`` additionally prints the complete audit report.
    """
    from ..audit import analyze_skill_dir
    from ..spec import check_spec, product_frontmatter_issues

    skill_dir = _pkg.CENTRAL_DIR / skill_name
    if not skill_dir.exists():
        return

    spec = check_spec(skill_dir)
    report = analyze_skill_dir(skill_dir)
    score = report.get("score", 100)
    grade = report.get("grade", "?")
    verdict = report.get("verdict", "safe")
    icon = {"safe": "OK", "caution": "CAUTION", "risky": "RISKY", "dangerous": "DANGEROUS"}.get(verdict, verdict)

    risky = verdict in ("risky", "dangerous")
    spec_part = "spec PASS" if spec["ok"] else f"spec FAIL ({len(spec['errors'])} error(s))"
    if verbose:
        print(f"  [check] {spec_part} - audit {score}/100 grade {grade} ({icon})")
        for w in spec["warnings"]:
            print(f"      warning: {w}")
        for e in spec["errors"]:
            print(f"      spec error: {e}")

    # v0.13.0: per-product frontmatter requirements (e.g. QwenWork's
    # name/version/description/description_zh).  These always print - the
    # affected product will silently refuse to load the skill otherwise.
    product_issues = product_frontmatter_issues(skill_dir)
    for issue in product_issues:
        print(f"  [product] {issue}")
    if product_issues:
        print("      (add the fields to SKILL.md frontmatter; 'askill verify' re-checks)")

    if risky:
        print(f"  !! SECURITY WARNING: '{skill_name}' scored {score}/100 ({verdict})")
        for f in report.get("findings", [])[:3]:
            print(f"     - [{f.get('severity', '?')}] {f.get('message', '?')} ({f.get('file', '?')})")
        print(f"     Review with: askill audit {skill_name}")

    if full_report and verbose:
        print()
        print(f"Running security audit on {skill_name}...")
        audit_skill(skill_name, verbose=True)

def _install_from_local(source: str, verbose: bool = True) -> tuple[str | None, bool]:
    """Install skill from a local path.
    Returns (skill_name, success).
    """
    src = Path(source).resolve()
    if not src.exists():
        if verbose:
            print(f"Path not found: {src}")
        return None, False

    if not (src / "SKILL.md").exists():
        if verbose:
            print(f"No SKILL.md found in: {src}")
        return None, False

    dest = _pkg.CENTRAL_DIR / src.name
    if dest.exists():
        if verbose:
            print(f"Skill already exists: {dest}")
            print(f"Remove it first: askill remove {src.name}")
        return None, False

    shutil.copytree(src, dest)
    if verbose:
        print(f"Installed to central repo: {dest}")
        print("  Run 'askill sync' to distribute to all products.")
    return src.name, True

def _install_from_url(
    source: str,
    verbose: bool = True,
    skill_hint: str | None = None,
) -> tuple[str | None, bool]:
    """Install skill from a GitHub URL.

    Supports these GitHub URL formats:
      - https://github.com/user/repo                      (repo root SKILL.md)
      - https://github.com/user/repo/tree/branch          (branch root)
      - https://github.com/user/repo/tree/branch/path/to/skill
      - https://github.com/user/repo/blob/branch/path/to/skill/SKILL.md

    With ``skill_hint`` (from ``owner/repo@skill`` shorthand) the cloned repo
    is searched for a directory named ``skill_hint`` containing SKILL.md and
    that directory is installed instead of the repo root.

    Returns (skill_name, success).
    """
    if verbose:
        print(f"Installing from URL: {source}")

    if "github.com" not in source:
        if verbose:
            print("Unsupported URL format. Use a GitHub URL.")
        return None, False

    # Parse GitHub URL into (repo_url, branch, sub_path, skill_name)
    branch = None  # None = use git default branch
    if "/tree/" in source:
        parts = source.split("/tree/")
        repo_url = parts[0]
        rest = parts[1].lstrip("/")
        segs = rest.split("/")
        branch = segs[0] if segs else None
        sub_path = "/".join(segs[1:]) if len(segs) > 1 else ""
        skill_name = segs[-1] if len(segs) > 1 else repo_url.split("/")[-1]
    elif "/blob/" in source:
        parts = source.split("/blob/")
        repo_url = parts[0]
        rest = parts[1].lstrip("/")
        segs = rest.split("/")
        branch = segs[0] if segs else None
        if segs and (segs[-1] == "SKILL.md" or segs[-1] == "SKILL.md/"):
            segs = segs[:-1]  # strip SKILL.md from path
        sub_path = "/".join(segs[1:]) if len(segs) > 1 else ""
        skill_name = segs[-1] if len(segs) > 1 else repo_url.split("/")[-1]
    else:
        parts = source.rstrip("/").split("/")
        if len(parts) < 5:
            if verbose:
                print(f"Invalid GitHub URL: {source}")
            return None, False
        repo_url = "/".join(parts[:5])
        sub_path = ""
        skill_name = parts[-1]

    if skill_hint:
        # find_skill_dir only ever returns a directory named skill_hint, so
        # the final name (and thus the install destination) is knowable now
        skill_name = skill_hint

    dest = _pkg.CENTRAL_DIR / skill_name
    if dest.exists():
        if verbose:
            print(f"Skill already exists: {dest}")
            print(f"Remove it first: askill remove {skill_name}")
        return None, False

    if verbose:
        print(f"  Repo: {repo_url}")
        print(f"  Branch: {branch or '(default)'}")
        print(f"  Path: {sub_path or '(root)'}")

    with tempfile.TemporaryDirectory() as tmp:
        try:
            cmd = ["git", "clone", "--depth", "1"]
            if branch:
                cmd += ["--branch", branch]
            cmd += [repo_url, tmp]
            subprocess.run(
                cmd,
                check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            src = Path(tmp) / sub_path if sub_path else Path(tmp)

            if skill_hint and src.exists():
                from ..registry import find_skill_dir
                found = find_skill_dir(Path(tmp), skill_hint)
                if found is None:
                    if verbose:
                        print(
                            f"Skill '{skill_hint}' not found in this repo "
                            "(no directory of that name containing SKILL.md)."
                        )
                        print(
                            "Try the full path instead: "
                            f"askill install {repo_url}/tree/main/<path>"
                        )
                    return None, False
                src = found
                skill_name = found.name
                if verbose:
                    print(f"  Resolved '{skill_hint}' -> {found.relative_to(tmp)}")

            if not src.exists() or not (src / "SKILL.md").exists():
                if verbose:
                    print(f"No SKILL.md found in {src}")
                return None, False

            shutil.copytree(src, dest)
            if verbose:
                print(f"Installed: {dest}")
            # v0.8.0: record origin so 'askill update' can track upgrades
            try:
                from ..sources import record_source
                record_source(skill_name, repo_url, sub_path, branch)
            except Exception:
                pass  # tracking is best-effort, never blocks install
            return skill_name, True
        except subprocess.CalledProcessError as e:
            if verbose:
                print(f"Git clone failed: {e.stderr}")
            return None, False
        except Exception as e:
            if verbose:
                print(f"Error: {e}")
            return None, False
