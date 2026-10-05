"""Skill publishing for ``askill publish`` (v0.15.0, docs/v0.15.0-plan.md R2).

Takes one skill from the central repository to a GitHub repository so
others can ``askill install owner/repo@skill`` (or ``npx skills add``).

Design notes:

- Three gates run before anything touches git: spec check, per-product
  frontmatter, and a security audit floor (dangerous verdicts block).
- ``push=False`` (the CLI default) is a dry run: gates and the exact git
  plan print, nothing is pushed and no bookkeeping is written.
- The remote URL defaults to SSH (``git@github.com:owner/repo.git``) to
  match the maintainer workflow; ``https=True`` switches to the credential
  helper route.
- Two layouts: **subdir** (default, additive and non-destructive - the
  skill lands in ``<name>/`` next to whatever the repo already holds) and
  **root** (``root=True``, replaces the repo root contents; refuses when
  the remote has files unless ``force=True``).
- Tests drive the whole flow against local ``file://`` bare remotes - no
  network, no credentials.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from ..config.products import CENTRAL_DIR
from .audit import analyze_skill_dir
from .spec import check_spec, product_frontmatter_issues

PUBLISHED_FILE = ".askill-published.json"

_GIT_TIMEOUT_S = 120


def _git(*args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command; capture output, never inherit the terminal."""
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=check, timeout=_GIT_TIMEOUT_S,
    )


def _remote_url(repo: str, https: bool) -> str:
    """``owner/name`` -> a cloneable URL (SSH default, HTTPS opt-in).

    Anything that is not a strict ``owner/name`` shorthand (explicit URLs,
    local paths - the latter is how tests inject file remotes) passes
    through unchanged.  Only trailing slashes are stripped: stripping the
    leading one would corrupt absolute Unix paths (``/tmp/...`` became
    ``tmp/...`` and stopped resolving - caught by CI on Linux).
    """
    repo = repo.rstrip("/")
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        return f"https://github.com/{repo}.git" if https else f"git@github.com:{repo}.git"
    return repo


def _run_gates(skill_dir: Path) -> tuple[list[str], bool]:
    """Pre-publish gates. Returns (problems, risky_but_allowed)."""
    problems: list[str] = []

    spec = check_spec(skill_dir)
    if not spec["ok"]:
        problems.extend(f"spec: {e}" for e in spec["errors"])

    product_issues = product_frontmatter_issues(skill_dir)
    problems.extend(f"frontmatter: {i}" for i in product_issues)

    risky = False
    report = analyze_skill_dir(skill_dir)
    verdict = report.get("verdict", "safe")
    if verdict == "dangerous":
        problems.append(
            f"audit: verdict is dangerous ({report.get('score')}/100) - "
            "fix the findings before publishing"
        )
    elif verdict in ("risky", "caution"):
        risky = True

    return problems, risky


def _remote_exists(url: str) -> bool:
    try:
        result = _git("ls-remote", url, check=False)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def _load_published(central: Path) -> dict:
    path = central / PUBLISHED_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _record_published(central: Path, entry: dict) -> None:
    data = _load_published(central)
    data[entry["skill"]] = entry
    (central / PUBLISHED_FILE).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def publish_skill(
    name: str,
    repo: str,
    *,
    root: bool = False,
    force: bool = False,
    https: bool = False,
    push: bool = False,
    create: bool = False,
    central_dir: Path | None = None,
    verbose: bool = True,
) -> dict:
    """Publish one skill from the central repo to a git repository.

    Args:
        name: Skill directory in the central repository.
        repo: ``owner/name`` shorthand or an explicit URL (tests use
            ``file://`` remotes).
        root: Replace the repository ROOT contents with the skill
            (single-skill repo, install as ``owner/repo``). Default is the
            additive ``<skill>/`` subdir layout (install as
            ``owner/repo@skill``).
        force: Allow root mode on a non-empty remote (still requires push).
        https: Clone/push over the HTTPS credential-helper route instead
            of the default SSH URL.
        push: Actually push. Without it the run is a dry run: gates run,
            the git plan prints, nothing is written.
        create: Create the GitHub repository first via ``gh repo create``
            (needs the gh CLI; other hosts must pre-create the repo).
        central_dir: Override the central repository (tests).
        verbose: Print progress.

    Returns:
        ``{"ok", "error", "problems", "risky", "plan", "published", "url"}``
        where ``plan`` lists the git actions (dry run fills this instead
        of pushing) and ``published`` is the bookkeeping entry on success.
    """
    report: dict = {
        "skill": name, "ok": False, "error": None, "problems": [],
        "risky": False, "plan": [], "published": None, "url": None,
    }

    central = Path(central_dir) if central_dir is not None else CENTRAL_DIR
    skill_dir = central / name
    if not skill_dir.is_dir() or not (skill_dir / "SKILL.md").exists():
        report["error"] = f"Skill not found in central repo: {name}"
        return report

    # ------------------------------------------------------------- gates
    problems, risky = _run_gates(skill_dir)
    report["problems"] = problems
    report["risky"] = risky
    if problems:
        report["error"] = "pre-publish gates failed (see problems)"
        return report

    url = _remote_url(repo, https)
    report["url"] = url

    # ------------------------------------------------------------ remote
    workdir = Path(tempfile.mkdtemp(prefix="askill-publish-"))
    try:
        if _remote_exists(url):
            _git("clone", "--depth", "1", url, str(workdir))
        elif create:
            gh = shutil.which("gh")
            if not gh:
                report["error"] = (
                    "repo does not exist and gh CLI is unavailable - create it "
                    f"manually (github.com/new) and rerun with --repo {repo}"
                )
                return report
            if verbose:
                print(f"  creating GitHub repo {repo} via gh...")
            result = subprocess.run(
                [gh, "repo", "create", repo, "--public"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=_GIT_TIMEOUT_S,
            )
            if result.returncode != 0:
                report["error"] = f"gh repo create failed: {result.stderr.strip()}"
                return report
            _git("clone", "--depth", "1", url, str(workdir))
        else:
            report["error"] = (
                f"repo not reachable: {url} - pass --create to create it "
                "on GitHub, or check the name"
            )
            return report

        # -------------------------------------------------- copy the skill
        dest = workdir if root else workdir / name
        if root:
            leftovers = [
                p.name for p in workdir.iterdir()
                if p.name != ".git" and not (p.is_dir() and not any(p.iterdir()))
            ]
            if leftovers and not force:
                # gate in dry runs too: the plan must not promise an action
                # a real push would refuse
                report["error"] = (
                    "root mode would replace existing repo content "
                    f"({', '.join(leftovers[:3])}...) - pass --force to allow"
                )
                return report
            for p in list(workdir.iterdir()):
                if p.name == ".git":
                    continue
                shutil.rmtree(p) if p.is_dir() else p.unlink()
        dest.mkdir(parents=True, exist_ok=True)
        for item in skill_dir.iterdir():
            target = dest / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)

        # ------------------------------------------------------- git plan
        if not _git("status", "--porcelain", cwd=workdir).stdout.strip():
            report["error"] = "nothing to publish - remote already matches the skill"
            return report
        commit_msg = f"publish {name} from askill"
        plan = [
            f"git add -A  ({'repo root' if root else name + '/'} layout)",
            f'git commit -m "{commit_msg}"',
            "git push origin HEAD",
        ]
        report["plan"] = plan
        if verbose:
            for line in plan:
                print(f"  plan: {line}")

        if not push:
            report["ok"] = True  # dry run completed cleanly
            return report

        _git("add", "-A", cwd=workdir)
        _git("-c", "user.name=askill-publish", "-c",
             "user.email=askill@local", "commit", "-m", commit_msg, cwd=workdir)
        _git("push", "origin", "HEAD", cwd=workdir)
        commit = _git("rev-parse", "--short", "HEAD", cwd=workdir).stdout.strip()

        entry = {
            "skill": name, "repo": repo, "url": url,
            "layout": "root" if root else "subdir",
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD", cwd=workdir).stdout.strip(),
            "commit": commit, "pushed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        _record_published(central, entry)
        report["published"] = entry
        report["ok"] = True
        return report
    except subprocess.CalledProcessError as e:
        report["error"] = f"git failed: {(e.stderr or e.stdout or '').strip()[:300]}"
        return report
    except (subprocess.TimeoutExpired, OSError) as e:
        report["error"] = f"git failed: {e}"
        return report
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def published_skills(central_dir: Path | None = None) -> dict:
    """Load the publish bookkeeping (``.askill-published.json``)."""
    central = Path(central_dir) if central_dir is not None else CENTRAL_DIR
    return _load_published(central)
