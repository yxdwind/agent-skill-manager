"""Product definitions for supported AI agent platforms."""

import platform
from pathlib import Path

HOME = Path.home()
IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"

# Central repository - the authoritative source for all skills
CENTRAL_DIR = HOME / ".agents" / "skills"

PRODUCTS = [
    {
        "name": "AutoClaw/OpenClaw",
        "short": "autoclaw",
        "macos_path": HOME / ".openclaw" / "skills",
        "windows_path": HOME / ".openclaw" / "skills",
        "sync_method": "symlink",
        "note": "AutoClaw also scans ~/.openclaw-autoclaw/skills/ and ~/.agents/skills/",
        "extra_dirs_macos": [HOME / ".openclaw-autoclaw" / "skills"],
        "extra_dirs_windows": [HOME / ".openclaw-autoclaw" / "skills"],
    },
    {
        "name": "Kimi Code",
        "short": "kimi",
        "macos_path": HOME / ".config" / "agents" / "skills",
        "windows_path": HOME / ".config" / "agents" / "skills",
        "sync_method": "symlink",
        "note": "Kimi Code also scans ~/.kimi-code/skills/",
        "extra_dirs_macos": [HOME / ".kimi-code" / "skills"],
        "extra_dirs_windows": [HOME / ".kimi-code" / "skills"],
    },
    {
        "name": "MiniMax Code",
        "short": "minimax",
        "macos_path": HOME / ".agents" / "skills",
        "windows_path": HOME / ".agents" / "skills",
        "sync_method": "native",
        "note": "MiniMax Code natively scans ~/.agents/skills/, no sync needed",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
    },
    {
        "name": "WorkBuddy",
        "short": "workbuddy",
        "macos_path": HOME / ".workbuddy" / "skills",
        "windows_path": HOME / ".workbuddy" / "skills",
        "sync_method": "symlink",
        "note": "Enable skill in settings.json",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
        "settings_file": HOME / ".workbuddy" / "settings.json",
    },
    {
        "name": "Trae Solo",
        "short": "trae",
        "macos_path": HOME / ".trae" / "skills",
        "windows_path": HOME / ".trae" / "skills",
        "sync_method": "symlink",
        "note": "Trae also supports project-level .trae/skills/ and .agents/skills/",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
    },
    {
        "name": "DuMate",
        "short": "dumate",
        "macos_path": None,
        "windows_path": None,
        "sync_method": "pack",
        "note": "DuMate manages skills via App; use pack command to generate .zip",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
    },
]


def get_product_path(product: dict) -> Path | None:
    """Get the primary skill directory for a product on the current platform."""
    if IS_WINDOWS:
        return product.get("windows_path")
    else:
        return product.get("macos_path")


def get_all_product_dirs(product: dict) -> list[Path]:
    """Get all skill directories for a product on the current platform."""
    primary = get_product_path(product)
    dirs = []
    if primary:
        dirs.append(primary)
    if IS_WINDOWS:
        dirs.extend(product.get("extra_dirs_windows", []))
    else:
        dirs.extend(product.get("extra_dirs_macos", []))
    return dirs


def get_product_by_short(name: str) -> dict | None:
    """Find a product by its short name."""
    for p in PRODUCTS:
        if p["short"] == name:
            return p
    return None
