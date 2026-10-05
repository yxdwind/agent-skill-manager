"""Drift detection: product directories diverging from the central repo.

v0.16.0, first slice of the bidirectional-sync direction
(docs/v0.15.0-plan.md listed it as a non-goal; this is the safe,
read-only foundation for it).

What counts as drift - a skill directory inside a product's skills dir
that is a **real directory** (not a junction/symlink askill created):

- ``new``      no same-named skill in the central repo -> ``askill adopt``
               can pull it in
- ``differs``  same-named skill exists in central but the product's real
               copy has different content -> a decision is needed:
               ``askill sync <skill> --force`` overwrites the product copy
               with central, or the product version should be pulled in

Linked/copied-by-askill directories are never drift: junctions and
symlinks ARE the central repo by construction, and copy-mode results are
kept in sync by every sync/watch run.
"""
from __future__ import annotations

from pathlib import Path

from ..config.products import (
    CENTRAL_DIR,
    PRODUCTS,
    _platform_key,
    get_product_path,
)
from ..utils.filesystem import _dirs_equivalent, is_symlink_or_junction


def find_drift(
    product_short: str | None = None,
    central_dir: Path | None = None,
) -> dict:
    """Scan product skill dirs for real directories that diverge.

    Args:
        product_short: Limit the scan to one product (must exist).
        central_dir: Override the central repository (tests).

    Returns:
        ``{"platform", "scanned": [shorts], "products": {short: {"new":
        [names], "differs": [names]}}, "error": None | str}`` - products
        with no drift are present with empty lists.
    """
    result: dict = {
        "platform": _platform_key(), "scanned": [], "products": {}, "error": None,
    }
    known = sorted(p["short"] for p in PRODUCTS)
    if product_short is not None and product_short not in known:
        # validate against THIS module's PRODUCTS so tests can patch the registry
        result["error"] = (
            f"Unknown product: {product_short} "
            f"(available: {', '.join(known)} or 'all')"
        )
        return result

    central = Path(central_dir) if central_dir is not None else CENTRAL_DIR
    # enumerate directly (not via list_skills) so a caller-supplied
    # central_dir - tests patch it - is always the view being matched
    central_names = (
        {d.name for d in central.iterdir()
         if d.is_dir() and (d / "SKILL.md").exists()}
        if central.exists() else set()
    )

    targets = [product_short] if product_short else [p["short"] for p in PRODUCTS]
    for short in targets:
        # look up in THIS module's PRODUCTS so tests can patch the registry
        p = next((x for x in PRODUCTS if x["short"] == short), None)
        entry: dict[str, list[str]] = {"new": [], "differs": []}
        path = get_product_path(p) if p else None
        if p is None or p["sync_method"] != "symlink" or path is None or not path.is_dir():
            result["products"][short] = entry
            continue
        result["scanned"].append(short)
        for item in sorted(path.iterdir()):
            if not item.is_dir() or is_symlink_or_junction(item):
                continue  # links are central by construction
            if item.name not in central_names:
                entry["new"].append(item.name)
            elif not _dirs_equivalent(central / item.name, item):
                entry["differs"].append(item.name)
        result["products"][short] = entry
    return result
