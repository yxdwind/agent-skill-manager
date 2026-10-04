"""Watch service: event-driven change detection + auto sync/clean/audit.

Provides the ``askill watch`` long-running mode:

- Sleeps on native OS file events (Linux inotify / macOS kqueue / Windows
  ReadDirectoryChangesW - see utils/watcher.py), falling back to snapshot
  polling where those are unavailable; zero third-party deps either way.
- Wakes are debounced, then classified by a cheap recursive
  (path -> mtime, size) snapshot diff, so a wake-up only ever syncs the
  skills that actually changed.
- New/changed skills are re-synced to all products immediately.
- Deleted skills are cleaned from every product (links removed) to avoid
  dead junctions/symlinks.
- After each sync the skill is re-audited; a score drop across the
  safe/risky boundary triggers a loud warning.
- Even in event mode a full reconciliation rescan runs every
  RECONCILE_INTERVAL_S as a safety net (queue overflow, editors that swap
  directories, root recreation).
"""
from __future__ import annotations

import contextlib
import json
import time
from pathlib import Path

from ..config.products import (
    CENTRAL_DIR,
    PRODUCTS,
    get_all_product_dirs,
)
from ..utils.filesystem import is_symlink_or_junction, remove_path
from ..utils.watcher import PollingWatcher, create_watcher
from .audit import analyze_skill_dir
from .sync import _disable_in_settings, list_skills, sync_skill

# ---------------------------------------------------------------- constants

POLL_INTERVAL_S = 3          # seconds between snapshots (poll fallback)
RECONCILE_INTERVAL_S = 30    # full-rescan safety net in native event mode
_SNAPSHOT_IGNORE = {".askill-sources.json", ".tmp"}

# verdict ranks used for downgrade detection: lower = safer
_VERDICT_RANK = {"safe": 0, "caution": 1, "risky": 2, "dangerous": 3}


# ---------------------------------------------------------------- snapshot

def snapshot_central() -> dict[str, tuple[float, int]]:
    """Build a recursive snapshot of the central repository.

    Returns:
        Mapping of relative path -> (mtime, size). Directory entries are
        recorded too (as (mtime, -1)) so renames/empty-dir deletions are
        noticed.
    """
    snap: dict[str, tuple[float, int]] = {}
    if not CENTRAL_DIR.exists():
        return snap
    for p in CENTRAL_DIR.rglob("*"):
        rel = p.relative_to(CENTRAL_DIR).as_posix()
        # skip internal bookkeeping files
        first = rel.split("/", 1)[0]
        if first in _SNAPSHOT_IGNORE:
            continue
        try:
            st = p.stat()
            if p.is_dir():
                snap[rel] = (st.st_mtime, -1)
            else:
                snap[rel] = (st.st_mtime, st.st_size)
        except OSError:
            # vanished mid-scan; omit, next poll catches the delete
            continue
    return snap


def diff_snapshots(
    old: dict[str, tuple[float, int]],
    new: dict[str, tuple[float, int]],
) -> tuple[set[str], set[str]]:
    """Compare two snapshots and classify changes per skill.

    Returns:
        (changed_skills, deleted_skills) - two sets of top-level skill names.
        A skill is "changed" if any of its files were added/modified, or the
        skill appeared.  A skill is "deleted" if all its paths disappeared.
    """
    changed: set[str] = set()
    deleted: set[str] = set()

    touched: set[str] = set()   # top-level dirs with any diff
    for key in set(old) | set(new):
        top = key.split("/", 1)[0]
        if old.get(key) != new.get(key):
            touched.add(top)

    now_skills = {k.split("/", 1)[0] for k in new}
    for top in touched:
        if top in now_skills:
            changed.add(top)
        else:
            deleted.add(top)
    return changed, deleted


# ---------------------------------------------------------------- cleaning

def clean_deleted_skill(skill_name: str, verbose: bool = True) -> list[str]:
    """Remove leftover links of a deleted skill from every product.

    Mirrors ``remove_skill``'s per-product sweep but never touches the
    central repo (the skill is already gone there).

    Returns:
        List of product shorts where a leftover was removed.
    """
    cleaned: list[str] = []
    for p in PRODUCTS:
        if p["sync_method"] in ("native", "pack"):
            continue
        for d in get_all_product_dirs(p):
            if d is None:
                continue
            link_path = Path(d) / skill_name
            try:
                if link_path.exists() or link_path.is_symlink() or is_symlink_or_junction(link_path):
                    remove_path(link_path)
                    cleaned.append(p["short"])
            except OSError:
                continue
        if p.get("settings_file"):
            _disable_in_settings(p["settings_file"], skill_name)
    if verbose and cleaned:
        print(f"  [watch] cleaned leftovers from: {', '.join(sorted(set(cleaned)))}")
    return cleaned


# ---------------------------------------------------------------- audit hook

def audit_downgrade_check(
    skill_name: str,
    prev_verdict: str | None,
    verbose: bool = True,
) -> str | None:
    """Re-audit one skill; warn loudly if its verdict got worse.

    Returns the new verdict (or None if the skill vanished).
    """
    skill_dir = CENTRAL_DIR / skill_name
    if not skill_dir.exists():
        return None
    report = analyze_skill_dir(skill_dir)
    verdict = report.get("verdict", "safe")
    score = report.get("score", 100)
    if prev_verdict is not None:
        prev_rank = _VERDICT_RANK.get(prev_verdict, 0)
        new_rank = _VERDICT_RANK.get(verdict, 0)
        if new_rank > prev_rank:
            grade = report.get("grade", "?")
            print(
                f"  !! SECURITY WARNING: '{skill_name}' verdict dropped "
                f"{prev_verdict} -> {verdict} (score {score}/100 grade {grade})"
            )
            findings = report.get("findings", [])
            for f in findings[:3]:
                sev = f.get("severity", "?")
                msg = f.get("message", "?")
                loc = f.get("file", "?")
                print(f"     - [{sev}] {msg} ({loc})")
    elif verbose:
        print(f"  [audit] {skill_name}: {score}/100 {verdict}")
    return verdict


# ---------------------------------------------------------------- main loop

def watch_loop(
    interval: int = POLL_INTERVAL_S,
    on_change=None,
    json_events: bool = False,
) -> None:
    """Run the watch loop until interrupted (Ctrl+C).

    Args:
        interval: Seconds between polls. In native event mode this is only
            the fallback poll cadence; the loop then reconciles at least
            every RECONCILE_INTERVAL_S instead of every ``interval``.
        on_change: Optional callback(skill_name) invoked after each sync -
            used by tests to observe the loop without a real filesystem.
        json_events: Emit one JSON object per line instead of human text
            (v0.15.0). Security-warning details still print as plain text
            after the event line - a deliberate trade-off so the loud
            warnings never get swallowed by a JSON consumer.
    """
    if not CENTRAL_DIR.exists():
        if json_events:
            print(json.dumps({"event": "error", "message": f"central repository not found: {CENTRAL_DIR}"}))
            return
        print(f"Central repository not found: {CENTRAL_DIR}")
        from .sync import print_onboarding
        print_onboarding()
        return

    backend = create_watcher(CENTRAL_DIR, poll_interval=interval)
    mode = backend.describe()
    if mode == "poll":
        cadence = interval
        if not json_events:
            print(f"Watching {CENTRAL_DIR} (poll every {cadence}s, Ctrl+C to stop)")
    else:
        cadence = max(RECONCILE_INTERVAL_S, interval)
        if not json_events:
            print(
                f"Watching {CENTRAL_DIR} [native {mode} events, "
                f"reconcile every {cadence}s, Ctrl+C to stop]"
            )

    known_verdicts: dict[str, str] = {}
    # prime the initial verdict table without spamming
    for s in list_skills():
        rep = analyze_skill_dir(s)
        known_verdicts[s.name] = rep.get("verdict", "safe")

    prev = snapshot_central()
    n_top = len({k.split("/", 1)[0] for k in prev})
    if json_events:
        print(json.dumps({"event": "start", "backend": mode, "tracking": n_top}))
    else:
        print(f"Tracking {n_top} entries. Ready.")

    try:
        while True:
            try:
                backend.wait(cadence)
            except OSError as exc:
                # native backend died mid-run: degrade to polling, keep watching
                if json_events:
                    print(json.dumps({"event": "backend-fallback", "mode": "poll", "reason": str(exc)}))
                else:
                    print(
                        f"  [watch] {mode} watcher failed ({exc}); "
                        f"falling back to polling every {interval}s"
                    )
                with contextlib.suppress(Exception):
                    backend.close()
                backend = PollingWatcher(CENTRAL_DIR, interval=interval)
                mode, cadence = "poll", interval
                continue

            curr = snapshot_central()
            changed, deleted = diff_snapshots(prev, curr)
            if not changed and not deleted:
                prev = curr
                continue

            if not json_events:
                print(f"\n[{time.strftime('%H:%M:%S')}] detected changes")
            for name in sorted(deleted):
                cleaned = clean_deleted_skill(name, verbose=not json_events)
                if json_events:
                    print(json.dumps({
                        "event": "deleted", "skill": name, "cleaned_from": sorted(set(cleaned)),
                    }))
                else:
                    print(f"- deleted skill: {name}")

            for name in sorted(changed):
                if not json_events:
                    print(f"- changed skill: {name}")
                sync_results = sync_skill(name, verbose=False).get(name, [])
                new_verdict = audit_downgrade_check(
                    name, known_verdicts.get(name), verbose=not json_events
                )
                if new_verdict:
                    known_verdicts[name] = new_verdict
                if json_events:
                    print(json.dumps({
                        "event": "changed",
                        "skill": name,
                        "sync": [
                            {"product": s, "ok": ok, "method": m}
                            for s, ok, m in sync_results
                        ],
                        "conflicts": [s for s, ok, m in sync_results if m == "conflict"],
                        "pack_pending": [s for s, ok, m in sync_results if m == "pack"],
                        "verdict": new_verdict,
                    }, ensure_ascii=False))
                else:
                    print(f"  [watch] synced '{name}' to all products")
                    pack_skipped = [s for s, ok, m in sync_results if m == "pack"]
                    if pack_skipped:
                        print(
                            f"  [watch] pack-mode product(s) not auto-updated - "
                            f"run 'askill pack {name}' to refresh the zip"
                        )
                    conflicts = [s for s, ok, m in sync_results if m == "conflict"]
                    if conflicts:
                        print(
                            f"  [watch] conflicts kept local: {', '.join(conflicts)} "
                            f"(resolve them or run 'askill sync {name} --force')"
                        )
                if on_change:
                    on_change(name)

            prev = snapshot_central()  # re-snapshot: sync may touch mtimes
    except KeyboardInterrupt:
        if not json_events:
            print("\nWatch stopped.")
    finally:
        backend.close()
