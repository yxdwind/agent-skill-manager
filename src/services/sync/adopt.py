"""``adopt`` - bring product-side skills under the central repo."""

from __future__ import annotations

import contextlib
import shutil
from pathlib import Path

import agent_skill_manager.services.sync as _pkg

from ...config.products import (
    ProductSpec,
)


def adopt_from_platform(
    platform_short: str,
    skill_name: str | None = None,
    verbose: bool = True,
) -> dict:
    """Adopt skills from one product platform into central repo, sync to all others.

    Scans a product skill directory for skills not yet in the central
    repository, copies them in, then syncs to all OTHER products.
    Reverse of sync: pull from one product to everywhere else.

    ``platform_short="all"`` scans every product directory at once - the
    bridge for skills installed outside askill (e.g. via ``npx skills add``
    from the skills.sh ecosystem, or a product's own UI).

    Args:
        platform_short: Short name of source product (e.g. autoclaw, trae),
            or "all".
        skill_name: If specified, only adopt this single skill.
        verbose: Print progress messages.

    Returns:
        Dict with keys: adopted (list of tuples), synced (dict from sync_skill).
    """
    from ...config.products import get_all_product_dirs

    adopt_all = platform_short == "all"
    product: ProductSpec | None = None
    if not adopt_all:
        for p in _pkg.PRODUCTS:
            if p["short"] == platform_short:
                product = p
                break
        if product is None:
            if verbose:
                print(f"Unknown platform: {platform_short}")
                shorts = [p["short"] for p in _pkg.PRODUCTS]
                print(f"Available: {', '.join(shorts)} (or 'all')")
            return {"adopted": [], "synced": {}}

        if product["sync_method"] in ("native", "pack"):
            if verbose:
                print(
                    f"Platform {platform_short!r} uses {product['sync_method']} mode, "
                    "no skill directory to adopt from."
                )
            return {"adopted": [], "synced": {}}

    # ``product`` is non-None when ``not adopt_all`` (the None-check above
    # returned in that case), but mypy can't see through the ``if/else``
    # branches at the use-sites below, so we re-narrow once and reuse.
    if adopt_all:
        source_products: list[ProductSpec] = list(_pkg.PRODUCTS)
    else:
        assert product is not None
        source_products = [product]
    source_skills: dict[str, Path] = {}

    for sp in source_products:
        if sp["sync_method"] in ("native", "pack"):
            continue
        for d in get_all_product_dirs(sp):
            if d is None or not d.exists():
                continue
            for item in sorted(d.iterdir()):
                if item.is_dir() and (item / "SKILL.md").exists():
                    real = item.resolve()
                    if item.name not in source_skills:
                        source_skills[item.name] = real

    if not source_skills:
        if verbose:
            scope = "any product directory" if adopt_all else product["name"]  # type: ignore[index]
            print(f"No skills found in {scope}.")
        return {"adopted": [], "synced": {}}

    if skill_name:
        if skill_name not in source_skills:
            if verbose:
                scope = "any product" if adopt_all else product["name"]  # type: ignore[index]
                print(f"Skill {skill_name!r} not found in {scope}.")
                print("Available: " + ", ".join(sorted(source_skills.keys())))
            return {"adopted": [], "synced": {}}
        source_skills = {skill_name: source_skills[skill_name]}

    if verbose:
        scope = "all products" if adopt_all else f"{product['name']} ({platform_short})"  # type: ignore[index]
        print(f"\nAdopting from {scope}:")
        print(f"  Found {len(source_skills)} skill(s)")
        print(f"  Central repo: {_pkg.CENTRAL_DIR}\n")

    _pkg.CENTRAL_DIR.mkdir(parents=True, exist_ok=True)

    adopted = []
    skills_to_sync = []

    for name, src_path in source_skills.items():
        dest = _pkg.CENTRAL_DIR / name

        if dest.exists():
            if dest.resolve() == src_path:
                if verbose:
                    print(f"  [{name}] already in central repo, skipping")
                adopted.append((name, True, "already-present"))
                skills_to_sync.append(name)
                continue
            else:
                if verbose:
                    print(f"  [{name}] already exists (different source)")
                    print(f"    Remove first: askill remove {name}")
                adopted.append((name, False, "conflict"))
                continue

        try:
            real_src = src_path
            # A link is adopted by content, not by reference: resolve it to
            # the real directory first. `is_symlink_or_junction` covers the
            # Windows junction case (and, unlike a bare `is_symlink()`, a
            # dangling one) as well as POSIX symlinks.
            if _pkg.is_symlink_or_junction(src_path):
                real_src = src_path.resolve()

            shutil.copytree(real_src, dest)
            if verbose:
                print(f"  [{name}] adopted -> {dest}")
            adopted.append((name, True, "copied"))
            skills_to_sync.append(name)
        except Exception as e:
            if verbose:
                print(f"  [{name}] FAILED: {e}")
            adopted.append((name, False, f"error: {e}"))

    synced = {}
    if skills_to_sync:
        if verbose:
            print(
                f"\nSyncing {len(skills_to_sync)} skill(s) to "
                "other products...\n"
            )

        other_products = [p for p in _pkg.PRODUCTS if p["short"] != platform_short]
        with _patch_products(other_products):
            for skill in skills_to_sync:
                result = _pkg.sync_skill(skill, verbose=verbose)
                synced.update(result)

    return {"adopted": adopted, "synced": synced}

@contextlib.contextmanager
def _patch_products(new_products):
    """Temporarily replace PRODUCTS list (exclude source platform)."""
    old = _pkg.PRODUCTS[:]
    _pkg.PRODUCTS.clear()
    _pkg.PRODUCTS.extend(new_products)
    try:
        yield
    finally:
        _pkg.PRODUCTS.clear()
        _pkg.PRODUCTS.extend(old)
