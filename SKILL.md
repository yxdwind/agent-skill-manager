---
name: agent-skill-manager
description: >
  Cross-platform skill manager for 15 domestic Chinese AI agent products
  (AutoClaw2, Kimi, MiniMax Code, WorkBuddy, Trae, Trae CN, TRAE SOLO CN,
  DuMate, CodeBuddy, Comate, Qoder CN, Qoder CN IDE, QwenWork, DoubaoWork,
  ZCode). Installs as the `askill` CLI — sync your skills to all products
  with one command. Use when the user wants to manage, install, sync, or
  remove Agent Skills across multiple AI coding tools and platforms.
license: MIT
---

# Agent Skill Manager

Cross-platform (macOS / Windows / Linux) skill sync for 15 domestic AI agent products.

## Quick Start

```bash
# Install
pip install -e .

# Check status across all products
askill status

# Sync all skills to all products
askill sync

# Install a new skill
askill install https://github.com/user/repo/tree/main/skill-name
askill sync
```

## When to Use

- User wants to install a skill to multiple AI products simultaneously
- User asks "sync skills between products" or "install skill to all agents"
- User wants to check which products have which skills
- User asks to remove a skill from all products

## Commands

| Command | Description |
|---------|-------------|
| `askill status [name]` | Show installation status across all 15 products |
| `askill sync [name]` | Sync skill(s) from central repo to all products |
| `askill list` | List all skills in central repository |
| `askill install <path\|url\|owner/repo@skill>` | Install a skill (local path, GitHub URL, or skills.sh shorthand) |
| `askill search <query>` | Search the skills.sh registry |
| `askill verify [name]` | Check skills against the agentskills.io spec |
| `askill remove <name>` | Remove a skill from central repo and all products |
| `askill pack <name>` | Package a skill as .zip for DuMate upload |
| `askill products` | List all supported products |
| `askill version` | Show version |

## Supported Products

| Product | Company | Sync Method |
|---------|---------|-------------|
| AutoClaw2 | Zhipu | symlink/junction |
| Kimi | Moonshot AI | symlink/junction |
| MiniMax Code | MiniMax | native |
| WorkBuddy | Tencent | symlink + settings.json |
| Trae | ByteDance | symlink/junction |
| Trae CN | ByteDance | symlink/junction |
| TRAE SOLO CN | ByteDance | symlink/junction |
| DuMate | Baidu | pack .zip |
| CodeBuddy | Tencent | symlink + settings.json |
| Comate / Wenxin Kuaima | Baidu | symlink/junction |
| Qoder CN | Alibaba | symlink/junction |
| Qoder CN IDE | Alibaba | symlink/junction |
| QwenWork / Qianwen Office | Alibaba | symlink/junction |
| DoubaoWork | ByteDance | symlink/junction |
| ZCode | ZCode | symlink/junction |

## Adding New Products

Edit `src/config/products.py` and add to the `PRODUCTS` list:

```python
{
    "name": "New Product",
    "short": "newprod",
    "macos_path": HOME / ".newproduct" / "skills",
    "windows_path": HOME / ".newproduct" / "skills",
    "sync_method": "symlink",
    "note": "Description",
    "extra_dirs_macos": [],
    "extra_dirs_windows": [],
}
```

## Architecture

All skills live in `~/.agents/skills/` (the emerging universal standard). 
The `askill sync` command creates symlinks (macOS) or junctions (Windows) 
to each product's skill directory.

```
~/.agents/skills/          ← Central Repository
  └── my-skill/
      └── SKILL.md
           │
           ├── junction → ~/.openclaw-autoclaw/skills/my-skill/
           ├── junction → ~/.config/agents/skills/my-skill/
           ├── junction → ~/.workbuddy/skills/my-skill/
           ├── junction → ~/.trae-cn/skills/my-skill/
           ├── junction → ~/.codebuddy/skills/my-skill/
           ├── junction → ~/.comate/skills/my-skill/
           └── junction → ~/.qoder-cn/skills/my-skill/
```

For detailed product paths and configuration, see `docs/product-paths.md`.
