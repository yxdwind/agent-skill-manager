"""Skill installation: local paths, GitHub URLs, and skills.sh shorthands."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import zipfile
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

    # v0.22.0: local .zip / .skill archives route before shorthand matching -
    # a path like downloads/tool.zip would otherwise false-match owner/repo.
    if source.lower().endswith((".zip", ".skill")):
        name, ok = _install_from_archive(source, verbose=verbose)
    else:
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

def _install_from_archive(
    source: str, verbose: bool = True, skill_hint: str | None = None,
) -> tuple[str | None, bool]:
    """Install a skill from a local ``.zip`` / ``.skill`` archive (v0.22.0).

    ``.skill`` files are zip archives (skills.sh convention).  Layouts
    supported: SKILL.md at archive root, or a single skill folder wrapping
    it; multi-skill archives are refused with their names.  Unsafe paths
    (absolute or ``..``) are rejected before extraction (zip-slip guard),
    and the normal post-install spec + security checks still run.  No
    source tracking: archives carry no git origin for update checks.
    """
    p = Path(source)
    if not p.exists():
        if verbose:
            print(f"Archive not found: {p}")
        return None, False

    with tempfile.TemporaryDirectory() as tmp:
        try:
            with zipfile.ZipFile(p) as z:
                unsafe = [
                    n for n in z.namelist()
                    if Path(n).is_absolute() or ".." in Path(n).parts
                ]
                if unsafe:
                    if verbose:
                        print("Unsafe archive paths rejected (zip-slip guard):")
                        for n in unsafe[:5]:
                            print(f"  {n}")
                    return None, False
                z.extractall(tmp)
        except zipfile.BadZipFile:
            if verbose:
                print(f"Not a valid zip archive: {p}")
            return None, False

        root = Path(tmp)
        if (root / "SKILL.md").exists():
            skill_dir = root
        else:
            candidates = [
                d for d in root.iterdir()
                if d.is_dir() and (d / "SKILL.md").exists()
            ]
            if not candidates:
                if verbose:
                    print("No SKILL.md found in the archive (root or single skill folder).")
                return None, False
            if len(candidates) > 1:
                if verbose:
                    print("Archive contains multiple skills - repack one per archive:")
                    for d in candidates:
                        print(f"  {d.name}")
                return None, False
            skill_dir = candidates[0]

        from ..spec import parse_frontmatter
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        fields, _warnings = parse_frontmatter(text)
        name = fields.get("name") or (skill_dir.name if skill_dir != root else p.stem)
        # frontmatter names are user input - never let them escape the central
        # repo via path separators (the zip-slip guard above covers entries,
        # this covers the SKILL.md name field itself)
        if not name or name in (".", "..") or any(
            sep in name for sep in ("/", "\\", ":")
        ):
            name = skill_dir.name if skill_dir != root else p.stem

        dest = _pkg.CENTRAL_DIR / name
        if dest.exists():
            if verbose:
                print(f"Skill already exists: {dest}")
                print(f"Remove it first: askill remove {name}")
            return None, False

        shutil.copytree(skill_dir, dest)
        if verbose:
            print(f"Installed to central repo: {dest}")
            print("  Run 'askill sync' to distribute to all products.")
        return name, True

def _clone_failure_hint(stderr: str) -> list[str]:
    """Actionable hints for common ``git clone`` network failures (v0.22.0).

    Domestic users often run a local proxy (Clash / v2rayN) configured in
    git's global config; when the proxy process is down, clones fail with a
    confusing "Failed to connect ... over proxy" error.  Name the cause and
    the escape hatch instead of leaving users with raw stderr.
    """
    s = (stderr or "").lower()
    if "proxy" in s:
        return [
            "A git proxy is configured but unreachable (see 'over proxy' above).",
            "  - Is your proxy client (Clash / v2rayN / ...) running? Start it, or",
            "    remove the git proxy: git config --global --unset http.proxy",
            "  - One-off bypass without touching git config (PowerShell):",
            '    $env:GIT_CONFIG_GLOBAL = "$env:TEMP\\empty.cfg"; askill install <source>',
        ]
    if "could not resolve host" in s:
        return ["DNS could not resolve the host - check your network or VPN."]
    if "failed to connect" in s or "connection refused" in s or "connection timed out" in s:
        return ["Could not reach the host - check your network, firewall, or VPN."]
    return []


def _report_clone_failure(stderr: str) -> None:
    """Print clone stderr plus any actionable hints (install / get share this)."""
    print(f"Git clone failed: {stderr.strip()}")
    for line in _clone_failure_hint(stderr):
        print(line)


def _shallow_clone(repo_url: str, branch: str | None, dest: Path) -> tuple[bool, str]:
    """Single ``git clone --depth 1`` path shared by install and get (v0.22.0).

    Returns (ok, stderr). Callers report failures via
    :func:`_report_clone_failure` so the proxy/network hints stay in sync.
    """
    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd += ["--branch", branch]
    cmd += [repo_url, str(dest)]
    try:
        subprocess.run(
            cmd, check=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        return True, ""
    except subprocess.CalledProcessError as e:
        return False, e.stderr or ""
    except OSError as e:
        return False, str(e)


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
            ok, err = _shallow_clone(repo_url, branch, Path(tmp))
            if not ok:
                if verbose:
                    _report_clone_failure(err)
                return None, False
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
