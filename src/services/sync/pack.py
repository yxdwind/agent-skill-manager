"""``pack`` - zip a skill for upload-only products (DuMate)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import agent_skill_manager.services.sync as _pkg


def pack_skill(skill_name: str, verbose: bool = True) -> Path | None:
    """Package a skill as .zip for DuMate upload.

    Args:
        skill_name: Name of the skill to pack.
        verbose: Print progress messages.

    Returns:
        Path to the generated .zip file, or None on failure.
    """
    skill_dir = _pkg.CENTRAL_DIR / skill_name
    if not skill_dir.exists():
        if verbose:
            print(f"Skill not found: {skill_name}")
        return None

    if not (skill_dir / "SKILL.md").exists():
        if verbose:
            print(f"No SKILL.md found in: {skill_dir}")
        return None

    output_path = _pkg.CENTRAL_DIR / f"{skill_name}.zip"

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in skill_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(skill_dir.parent)
                zf.write(file_path, arcname)

    if verbose:
        print(f"Packed: {output_path}")
        print("  Upload this file in DuMate App -> Skills -> Install")
    return output_path
