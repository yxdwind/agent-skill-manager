"""Environment and repository health diagnostics (``askill doctor``, v0.23.0).

One command that answers "why is askill misbehaving on this machine":
git availability, configured proxies (git config + env) with a live TCP
reachability probe - the unreachable-local-proxy failure mode behind most
"install from GitHub failed" reports - central repository state (skills,
tracked sources, orphan tracking entries), per-product link health
(broken links, real dirs that forked from central), and whether
settings-managed products' settings files are writable right now.

Strictly read-only: the settings probe opens ``r+b`` and closes without
writing; nothing else touches the filesystem or the network beyond the
proxy TCP probes.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from ..config.products import PRODUCTS, get_product_path
from ..utils.filesystem import is_symlink_or_junction
from .inventory import list_skills

__all__ = ["doctor_report"]


# ---------------------------------------------------------------- helpers

def _load_sources_for(central: Path) -> dict:
    """Sources registry read straight from *central* (no module globals)."""
    try:
        f = central / ".askill-sources.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    return {}


def _git_version() -> str | None:
    git = shutil.which("git")
    if not git:
        return None
    try:
        r = subprocess.run(
            ["git", "--version"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15,
        )
        return (r.stdout or "").strip() or git
    except (OSError, subprocess.TimeoutExpired):
        return git


def _configured_proxies() -> list[dict]:
    """All configured proxy URLs with their source (git config first, then env)."""
    found: dict[str, dict] = {}
    for key in ("http.proxy", "https.proxy"):
        try:
            r = subprocess.run(
                ["git", "config", "--global", "--get", key],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=15,
            )
            url = (r.stdout or "").strip()
        except (OSError, subprocess.TimeoutExpired):
            url = ""
        if url:
            found[f"git {key}"] = {"source": f"git config {key}", "url": url}
    for var in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"):
        env_url: str | None = os.environ.get(var) or os.environ.get(var.lower())
        if env_url and env_url not in {v["url"] for v in found.values()}:
            found[f"env {var}"] = {"source": f"env {var}", "url": env_url}
    return list(found.values())


def _probe_tcp(url: str, timeout: float = 1.5) -> bool | None:
    """TCP-connect to the proxy's host:port. None when the URL has no probe target."""
    try:
        parsed = urlparse(url if "//" in url else f"http://{url}")
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return None
    if not host:
        return None
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _settings_writable(path: Path) -> bool | None:
    """Probe a settings file for exclusive locks by opening r+b (no write)."""
    try:
        with open(path, "r+b"):
            return True
    except PermissionError:
        return False
    except OSError:
        return None  # missing / not a regular file


def _scan_product_dir(pdir: Path, central_names: set[str]) -> dict:
    """Link health for one product skills dir (read-only sweep).

    ``fork_dirs`` counts real (non-linked) folders whose name matches a
    central skill - the actual drift candidates.  Real folders with other
    names are product-local skills, not drift, and are not flagged.
    """
    links = broken = real_dirs = fork_dirs = 0
    try:
        entries = list(pdir.iterdir())
    except OSError:
        return {"links": None, "broken_links": None, "real_dirs": None, "fork_dirs": None}
    for e in entries:
        if is_symlink_or_junction(e):
            links += 1
            if not e.exists():
                broken += 1
        elif e.is_dir():
            real_dirs += 1
            if e.name in central_names:
                fork_dirs += 1
    return {
        "links": links, "broken_links": broken,
        "real_dirs": real_dirs, "fork_dirs": fork_dirs,
    }


# ---------------------------------------------------------------- main

def doctor_report(central: Path | None = None, verbose: bool = True) -> dict:
    """Run all diagnostics and return the report (also printed when verbose).

    ``ok`` is False only when at least one check has severity ``fail``
    (things that make askill itself unable to work).  Warnings are
    machine/product states the user can heal with documented commands.
    """
    base = Path(central) if central is not None else None
    if base is None:
        from ..config.products import CENTRAL_DIR
        base = CENTRAL_DIR

    checks: list[dict] = []

    # 1. git
    ver = _git_version()
    if ver:
        checks.append({"id": "git", "severity": "ok", "detail": ver})
    else:
        checks.append({
            "id": "git", "severity": "fail",
            "detail": "git not found - 'askill install' from GitHub needs it",
        })

    # 2. proxies (configured but unreachable = the top install-failure cause)
    proxies: list[dict] = []
    for px in _configured_proxies():
        reachable = _probe_tcp(px["url"])
        entry = {**px, "reachable": reachable}
        proxies.append(entry)
        if reachable is False:
            checks.append({
                "id": f"proxy:{px['source']}", "severity": "fail",
                "detail": (
                    f"{px['source']} -> {px['url']} is not reachable; "
                    "git clone (askill install / get / update) will fail. "
                    "Start your proxy client, or: "
                    "git config --global --unset http.proxy"
                ),
            })
            continue
        checks.append({
            "id": f"proxy:{px['source']}", "severity": "ok",
            "detail": f"{px['source']} -> {px['url']} reachable",
        })

    # 3. central repository
    skills = list_skills(base) if base.exists() else []
    sources = _load_sources_for(base)
    orphan_sources = [n for n in sources if n not in {d.name for d in skills}]
    checks.append({
        "id": "central", "severity": "warn" if not base.exists() else "ok",
        "detail": (
            f"{base} - {len(skills)} skill(s), "
            f"{len(sources)} tracked source(s)"
            + (f", {len(orphan_sources)} orphan source entr(ies)" if orphan_sources else "")
        ),
    })
    if orphan_sources:
        checks.append({
            "id": "orphan-sources", "severity": "warn",
            "detail": (
                "tracking entries without a matching central skill: "
                + ", ".join(sorted(orphan_sources))
                + " (clean with: remove the entry from .askill-sources.json)"
            ),
        })

    # 4. products
    central_names = {d.name for d in skills}
    product_rows: list[dict] = []
    broken_total = 0
    real_dir_products: list[str] = []
    for p in PRODUCTS:
        # get_product_path is typed Path | None but the config paths are raw
        # strings at runtime - coerce defensively instead of trusting the cast
        raw = get_product_path(p)
        pdir = Path(raw) if raw is not None else None
        row = {
            "name": p["name"], "short": p["short"],
            "sync_method": p.get("sync_method"),
            "dir": str(pdir) if pdir else "",
            "dir_exists": bool(pdir and pdir.exists()),
        }
        if pdir is None:
            product_rows.append(row)
            continue
        scan = _scan_product_dir(pdir, central_names) if pdir.exists() else {}
        row.update(scan)
        if (scan.get("broken_links") or 0) > 0:
            broken_total += scan["broken_links"]
        if (scan.get("fork_dirs") or 0) > 0:
            real_dir_products.append(p["name"])
        sf = p.get("settings_file")
        if sf is not None:
            sfp = Path(sf)
            row["settings_file"] = str(sfp)
            row["settings_writable"] = _settings_writable(sfp) if sfp.exists() else None
        product_rows.append(row)

    if broken_total:
        checks.append({
            "id": "broken-links", "severity": "warn",
            "detail": f"{broken_total} broken link(s) across products - run: askill sync",
        })
    if real_dir_products:
        checks.append({
            "id": "drift-candidates", "severity": "warn",
            "detail": (
                "product dirs contain real folders shadowing central skills: "
                + ", ".join(real_dir_products)
                + " - inspect with: askill drift"
            ),
        })

    ok = not any(c["severity"] == "fail" for c in checks)
    report = {
        "ok": ok,
        "checks": checks,
        "central": {
            "dir": str(base), "exists": base.exists(),
            "skills": len(skills), "tracked": len(sources),
            "orphan_sources": sorted(orphan_sources),
        },
        "products": product_rows,
    }

    if verbose:
        _print_report(report)
    return report


def _print_report(report: dict) -> None:
    """Human-readable rendering (the --json dump is the report dict itself)."""
    print("askill doctor - environment & repository health\n")
    icon = {"ok": "[ok]  ", "warn": "[warn]", "fail": "[FAIL]"}
    for c in report["checks"]:
        print(f"  {icon.get(c['severity'], '[?]   ')} {c['id']}: {c['detail']}")
    print(f"\n  products ({len(report['products'])}):")
    for row in report["products"]:
        if not row["dir_exists"]:
            print(f"    {row['name']:<28} dir missing (run askill sync to create)")
            continue
        parts = [f"{row.get('links', '?')} link(s)"]
        if row.get("broken_links"):
            parts.append(f"{row['broken_links']} broken")
        if row.get("real_dirs"):
            parts.append(f"{row['real_dirs']} real dir(s)")
        if row.get("settings_writable") is False:
            parts.append("settings.json LOCKED")
        print(f"    {row['name']:<28} {', '.join(parts)}")
    print()
    verdict = "healthy" if report["ok"] else "issues found (see FAIL above)"
    print(f"  overall: {verdict}")
    print("  --  pass --json for a machine-readable report (great for bug reports)")
