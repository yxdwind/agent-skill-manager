"""Product definitions for supported AI agent platforms."""

from __future__ import annotations

import os
import platform
from pathlib import Path

from ..models.product import ProductSpec

HOME = Path.home()
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", HOME / "AppData" / "Local"))
IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# Central repository - the authoritative source for all skills
CENTRAL_DIR = HOME / ".agents" / "skills"

# Linux support: only products that actually ship a Linux build (or a
# platform-independent CLI convention) carry a ``linux_path``.  Desktop/IDE
# apps without a Linux build use ``None`` so askill skips them cleanly
# instead of creating dead directories - add the path (with evidence) when
# a build ships.

PRODUCTS: list[ProductSpec] = [
    {
        "name": "AutoClaw2",
        "short": "autoclaw2",
        "macos_path": HOME / ".openclaw-autoclaw" / "skills",
        "windows_path": HOME / ".openclaw-autoclaw" / "skills",
        "linux_path": HOME / ".openclaw-autoclaw" / "skills",
        "sync_method": "symlink",
        "note": "AutoClaw2 (Zhipu) profile root is ~/.openclaw-autoclaw/; it also scans ~/.agents/skills/ natively. Legacy v1 used ~/.openclaw/skills/",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
        "extra_dirs_linux": [],
    },
    {
        "name": "Kimi",
        "short": "kimi",
        "macos_path": HOME / ".config" / "agents" / "skills",
        "windows_path": HOME / ".config" / "agents" / "skills",
        "linux_path": HOME / ".config" / "agents" / "skills",
        "sync_method": "symlink",
        "note": "Kimi also scans ~/.kimi-code/skills/",
        "extra_dirs_macos": [HOME / ".kimi-code" / "skills"],
        "extra_dirs_windows": [HOME / ".kimi-code" / "skills"],
        "extra_dirs_linux": [HOME / ".kimi-code" / "skills"],
    },
    {
        "name": "MiniMax Code",
        "short": "minimax",
        "macos_path": HOME / ".agents" / "skills",
        "windows_path": HOME / ".agents" / "skills",
        "linux_path": HOME / ".agents" / "skills",
        "sync_method": "native",
        "note": "MiniMax Code natively scans ~/.agents/skills/, no sync needed",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
        "extra_dirs_linux": [],
    },
    {
        "name": "WorkBuddy",
        "short": "workbuddy",
        "macos_path": HOME / ".workbuddy" / "skills",
        "windows_path": HOME / ".workbuddy" / "skills",
        "linux_path": None,
        "sync_method": "symlink",
        "note": "Enable skill in settings.json. Desktop app: macOS & Windows builds only, no Linux path yet",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
        "extra_dirs_linux": [],
        "settings_file": HOME / ".workbuddy" / "settings.json",
        "settings_mode": "skills-switch",
    },
    {
        "name": "Trae",
        "short": "trae",
        "macos_path": HOME / ".trae" / "skills",
        "windows_path": HOME / ".trae" / "skills",
        "linux_path": None,
        "sync_method": "symlink",
        "note": "Trae also supports project-level .trae/skills/ and .agents/skills/. No Linux build yet",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
        "extra_dirs_linux": [],
    },
    {
        "name": "Trae CN",
        "short": "traecn",
        "macos_path": HOME / ".trae-cn" / "skills",
        "windows_path": HOME / ".trae-cn" / "skills",
        "linux_path": None,
        "sync_method": "symlink",
        "note": "Trae CN (ByteDance CN edition) uses ~/.trae-cn/; international Trae uses ~/.trae/ (see trae entry). No Linux build yet",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
        "extra_dirs_linux": [],
    },
    {
        "name": "TRAE SOLO CN",
        "short": "traesolo",
        "macos_path": HOME / ".trae-cn" / "skills",
        "windows_path": HOME / ".trae-cn" / "skills",
        "linux_path": None,
        "sync_method": "symlink",
        "note": "TRAE SOLO CN shares ~/.trae-cn/ with Trae CN (same dataFolderName in product.json). No Linux build yet",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
        "extra_dirs_linux": [],
    },
    {
        "name": "DuMate (Baidu)",
        "short": "dumate",
        "macos_path": None,
        "windows_path": None,
        "linux_path": None,
        "sync_method": "pack",
        "note": "DuMate manages skills via App; use pack command to generate .zip (works on all platforms)",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
        "extra_dirs_linux": [],
    },
    {
        "name": "CodeBuddy (Tencent)",
        "short": "codebuddy",
        "macos_path": HOME / ".codebuddy" / "skills",
        "windows_path": HOME / ".codebuddy" / "skills",
        "linux_path": HOME / ".codebuddy" / "skills",
        "sync_method": "symlink",
        "note": "CodeBuddy CLI also scans ~/.agents/skills/; settings in ~/.codebuddy/settings.json",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
        "extra_dirs_linux": [],
        "settings_file": HOME / ".codebuddy" / "settings.json",
        "settings_mode": "skills-switch",
    },
    {
        "name": "Comate / Wenxin Kuaima (Baidu)",
        "short": "comate",
        "macos_path": HOME / ".comate" / "skills",
        "windows_path": HOME / ".comate" / "skills",
        "linux_path": HOME / ".comate" / "skills",
        "sync_method": "symlink",
        "note": "Comate auto-loads skills from ~/.comate/skills/ on startup",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
        "extra_dirs_linux": [],
    },
    {
        "name": "Qoder CN",
        "short": "qodercn",
        "macos_path": HOME / ".qoder-cn" / "skills",
        "windows_path": HOME / ".qoder-cn" / "skills",
        "linux_path": None,
        "sync_method": "symlink",
        "note": "Qoder CN stores skills in ~/.qoder-cn/skills/ (legacy QoderWork path was ~/.qoderwork/skills/). No Linux build yet",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
        "extra_dirs_linux": [],
    },
    {
        "name": "Qoder CN IDE",
        "short": "qodercnide",
        "macos_path": HOME / ".qoder-cn" / "skills",
        "windows_path": HOME / ".qoder-cn" / "skills",
        "linux_path": None,
        "sync_method": "symlink",
        "note": "Qoder CN IDE shares ~/.qoder-cn/ with Qoder CN (same dataFolderName in product.json). No Linux build yet",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
        "extra_dirs_linux": [],
    },
    {
        "name": "QwenWork / Qianwen Office (Alibaba)",
        "short": "qwenwork",
        "macos_path": HOME / ".qwenworkcn" / "skills",
        "windows_path": HOME / ".qwenworkcn" / "skills",
        "linux_path": None,
        "sync_method": "symlink",
        "note": "QwenWork desktop scans ~/.qwenworkcn/skills/; frontmatter needs name+version+description+description_zh. Desktop app: no Linux build yet",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
        "extra_dirs_linux": [],
        "required_frontmatter": ["name", "version", "description", "description_zh"],
    },
    {
        "name": "DoubaoWork (ByteDance)",
        "short": "doubaowork",
        "macos_path": HOME / ".super_doubao" / "super-doubao-runtime" / "workspace" / ".user_skills",
        "windows_path": LOCALAPPDATA / "DoubaoWork" / "User Data" / "Default" / ".doubaowork" / "agent_mode" / "workspace" / ".user_skills",
        "linux_path": None,
        "sync_method": "symlink",
        "note": "DoubaoWork user skills live in workspace/.user_skills; system skills in workspace/.skills. Desktop app: no Linux build yet",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
        "extra_dirs_linux": [],
    },
    {
        "name": "ZCode",
        "short": "zcode",
        "macos_path": HOME / ".zcode" / "skills",
        "windows_path": HOME / ".zcode" / "skills",
        "linux_path": HOME / ".zcode" / "skills",
        "sync_method": "symlink",
        "note": "ZCode also scans ~/.agents/skills/ natively",
        "extra_dirs_macos": [],
        "extra_dirs_windows": [],
        "extra_dirs_linux": [],
    },
]


def _platform_key() -> str:
    """Return the product-field platform key for the current OS."""
    if IS_WINDOWS:
        return "windows"
    if IS_MACOS:
        return "macos"
    # Linux and any other Unix: use the Linux paths
    return "linux"


def get_product_path(product: ProductSpec) -> Path | None:
    """Get the primary skill directory for a product on the current platform."""
    return product.get(f"{_platform_key()}_path")


def get_all_product_dirs(product: ProductSpec) -> list[Path]:
    """Get all skill directories for a product on the current platform."""
    key = _platform_key()
    primary = product.get(f"{key}_path")
    dirs = []
    if primary:
        dirs.append(primary)
    dirs.extend(product.get(f"extra_dirs_{key}", []))
    return dirs


def get_product_by_short(name: str) -> ProductSpec | None:
    """Find a product by its short name."""
    for p in PRODUCTS:
        if p["short"] == name:
            return p
    return None
