"""Core sync logic: install, sync, remove, pack operations."""

import json
import shutil
import zipfile
import tempfile
import subprocess
from pathlib import Path

from .products import PRODUCTS, CENTRAL_DIR, get_product_path, get_all_product_dirs
from .utils import (
    is_symlink_or_junction,
    create_link,
    copy_skill,
    remove_path,
    read_skill_metadata,
)


def list_skills() -> list[Path]:
    """List all skills in the central repository.

    Returns:
        Sorted list of skill directory paths.
    """
    if not CENTRAL_DIR.exists():
        return []
    return sorted(
        d for d in CENTRAL_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )


def get_status(skill_name: str | None = None) -> list[dict]:
    """Get installation status of skills across all products.

    Args:
        skill_name: If specified, only check this skill.

    Returns:
        List of dicts with keys: skill_name, product_short, status, method.
    """
    skills = list_skills()
    if skill_name:
        skills = [s for s in skills if s.name == skill_name]
        if not skills:
            return []

    results = []
    for skill_dir in skills:
        for p in PRODUCTS:
            entry = {
                "skill_name": skill_dir.name,
                "product_short": p["short"],
                "product_name": p["name"],
                "status": "",
                "method": p["sync_method"],
            }
            if p["sync_method"] == "native":
                entry["status"] = "ok" if skill_dir.exists() else "missing"
            elif p["sync_method"] == "pack":
                entry["status"] = "manual"
            else:
                target = get_product_path(p)
                if target is None:
                    entry["status"] = "n/a"
                else:
                    link_path = target / skill_dir.name
                    if link_path.exists() or link_path.is_symlink():
                        if is_symlink_or_junction(link_path):
                            entry["status"] = "ok"
                            entry["method"] = "link"
                        else:
                            entry["status"] = "ok"
                            entry["method"] = "copy"
                    else:
                        entry["status"] = "missing"
            results.append(entry)
    return results


def sync_skill(skill_name: str | None = None, verbose: bool = True) -> dict:
    """Sync skills from central repo to all products.

    Args:
        skill_name: If specified, only sync this skill. None = sync all.
        verbose: Print progress messages.

    Returns:
        Dict mapping skill_name -> list of (product_short, success, method).
    """
    if not CENTRAL_DIR.exists():
        if verbose:
            print(f"Central repository not found: {CENTRAL_DIR}")
        return {}

    skills = list_skills()
    if skill_name:
        skills = [s for s in skills if s.name == skill_name]
        if not skills:
            if verbose:
                print(f"Skill not found: {skill_name}")
            return {}

    if not skills:
        if verbose:
            print("No skills to sync.")
        return {}

    if verbose:
        print(f"\nSyncing {len(skills)} skill(s) to {len(PRODUCTS)} product(s)...\n")

    results = {}
    for skill_dir in skills:
        if verbose:
            print(f"[{skill_dir.name}]")
        sync_results = []
        for p in PRODUCTS:
            if p["sync_method"] == "native":
                if verbose:
                    print(f"  {p['short']:>10}: ok native (uses central repo)")
                sync_results.append((p["short"], True, "native"))
                continue

            if p["sync_method"] == "pack":
                if verbose:
                    print(f"  {p['short']:>10}: skip (use 'pack' command)")
                sync_results.append((p["short"], False, "pack"))
                continue

            target = get_product_path(p)
            if target is None:
                if verbose:
                    print(f"  {p['short']:>10}: n/a")
                sync_results.append((p["short"], False, "n/a"))
                continue

            link_path = target / skill_dir.name
            success, method, message = create_link(skill_dir, link_path)
            status_icon = "ok" if success else "FAIL"
            if verbose:
                print(f"  {p['short']:>10}: {status_icon} {method}")
            sync_results.append((p["short"], success, method))

            # Sync extra dirs (e.g. AutoClaw's ~/.openclaw-autoclaw/skills/)
            from .products import IS_WINDOWS
            if IS_WINDOWS:
                extra_dirs = p.get("extra_dirs_windows", [])
            else:
                extra_dirs = p.get("extra_dirs_macos", [])
            for extra in extra_dirs:
                if extra is None:
                    continue
                extra_link = Path(extra) / skill_dir.name
                try:
                    extra_link.parent.mkdir(parents=True, exist_ok=True)
                except OSError:
                    pass
                ok2, method2, _ = create_link(skill_dir, extra_link)
                if verbose:
                    print(f"  {p['short']:>10}: extra -> {extra_link} ({method2 if ok2 else 'FAIL'})")

            # Handle WorkBuddy settings.json
            if p.get("settings_file") and success:
                _update_workbuddy_settings(p["settings_file"], skill_dir.name, verbose=verbose)

        if verbose:
            print()
        results[skill_dir.name] = sync_results

    return results


def install_skill(source: str, verbose: bool = True) -> bool:
    """Install a skill to the central repository.

    Args:
        source: Local path or GitHub URL.
        verbose: Print progress messages.

    Returns:
        True if installation succeeded.
    """
    CENTRAL_DIR.mkdir(parents=True, exist_ok=True)

    if source.startswith("http"):
        return _install_from_url(source, verbose=verbose)
    else:
        return _install_from_local(source, verbose=verbose)


def _install_from_local(source: str, verbose: bool = True) -> bool:
    """Install skill from a local path."""
    src = Path(source).resolve()
    if not src.exists():
        if verbose:
            print(f"Path not found: {src}")
        return False

    if not (src / "SKILL.md").exists():
        if verbose:
            print(f"No SKILL.md found in: {src}")
        return False

    dest = CENTRAL_DIR / src.name
    if dest.exists():
        if verbose:
            print(f"Skill already exists: {dest}")
            print(f"Remove it first: askill remove {src.name}")
        return False

    shutil.copytree(src, dest)
    if verbose:
        print(f"Installed to central repo: {dest}")
        print(f"  Run 'sync' to distribute to all products.")
    return True


def _install_from_url(source: str, verbose: bool = True) -> bool:
    """Install skill from a GitHub URL."""
    if verbose:
        print(f"Installing from URL: {source}")

    skill_name = source.rstrip("/").split("/")[-1]
    if skill_name == "tree":
        skill_name = source.rstrip("/").split("/")[-1]

    dest = CENTRAL_DIR / skill_name
    if dest.exists():
        if verbose:
            print(f"Skill already exists: {dest}")
        return False

    if "github.com" in source and "/tree/" in source:
        parts = source.replace("/tree/", "/").split("/")
        repo_url = "/".join(parts[:5])
        branch = parts[5] if len(parts) > 5 else "main"
        sub_path = "/".join(parts[6:]) if len(parts) > 6 else ""

        with tempfile.TemporaryDirectory() as tmp:
            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", "--branch", branch, repo_url, tmp],
                    check=True, capture_output=True, text=True
                )
                src = Path(tmp) / sub_path if sub_path else Path(tmp)
                if src.exists() and (src / "SKILL.md").exists():
                    shutil.copytree(src, dest)
                    if verbose:
                        print(f"Installed: {dest}")
                    return True
                else:
                    if verbose:
                        print(f"No SKILL.md found in {src}")
                    return False
            except subprocess.CalledProcessError as e:
                if verbose:
                    print(f"Git clone failed: {e.stderr}")
                return False
            except Exception as e:
                if verbose:
                    print(f"Error: {e}")
                return False
    else:
        if verbose:
            print("Unsupported URL format. Use GitHub tree URL or local path.")
        return False


def remove_skill(skill_name: str, verbose: bool = True) -> list[str]:
    """Remove a skill from central repo and all products.

    Args:
        skill_name: Name of the skill to remove.
        verbose: Print progress messages.

    Returns:
        List of locations where the skill was removed.
    """
    skill_dir = CENTRAL_DIR / skill_name
    if not skill_dir.exists():
        if verbose:
            print(f"Skill not found in central repo: {skill_name}")
        return []

    removed = []

    for p in PRODUCTS:
        if p["sync_method"] in ("native", "pack"):
            continue

        target = get_product_path(p)
        if target is None:
            continue

        link_path = target / skill_name
        if link_path.exists() or link_path.is_symlink():
            remove_path(link_path)
            removed.append(p["short"])

        for d in get_all_product_dirs(p)[1:]:
            link_path = d / skill_name
            if link_path.exists() or link_path.is_symlink():
                remove_path(link_path)
                removed.append(f"{p['short']}-alt")

        if p.get("settings_file"):
            _remove_from_workbuddy_settings(p["settings_file"], skill_name, removed, verbose=verbose)

    shutil.rmtree(skill_dir)
    removed.append("central")

    if verbose:
        print(f"Removed '{skill_name}' from: {', '.join(removed)}")
    return removed


def pack_skill(skill_name: str, verbose: bool = True) -> Path | None:
    """Package a skill as .zip for DuMate upload.

    Args:
        skill_name: Name of the skill to pack.
        verbose: Print progress messages.

    Returns:
        Path to the generated .zip file, or None on failure.
    """
    skill_dir = CENTRAL_DIR / skill_name
    if not skill_dir.exists():
        if verbose:
            print(f"Skill not found: {skill_name}")
        return None

    if not (skill_dir / "SKILL.md").exists():
        if verbose:
            print(f"No SKILL.md found in: {skill_dir}")
        return None

    output_path = CENTRAL_DIR / f"{skill_name}.zip"

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in skill_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(skill_dir.parent)
                zf.write(file_path, arcname)

    if verbose:
        print(f"Packed: {output_path}")
        print(f"  Upload this file in DuMate App -> Skills -> Install")
    return output_path


def _update_workbuddy_settings(settings_path: Path, skill_name: str, verbose: bool = True) -> None:
    """Enable a skill in WorkBuddy's settings.json."""
    try:
        if settings_path.exists():
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        else:
            settings = {}

        skills_config = settings.setdefault("skills", {})
        skills_config[skill_name] = True

        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        if verbose:
            print(f"  {'':>10}   Updated settings.json")
    except Exception as e:
        if verbose:
            print(f"  {'':>10}   Warning: could not update settings.json: {e}")


def _remove_from_workbuddy_settings(
    settings_path: Path, skill_name: str, removed: list, verbose: bool = True
) -> None:
    """Remove a skill from WorkBuddy's settings.json."""
    try:
        if settings_path.exists():
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            if "skills" in settings and skill_name in settings["skills"]:
                del settings["skills"][skill_name]
                settings_path.write_text(
                    json.dumps(settings, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
                removed.append("workbuddy-settings")
    except Exception:
        pass
