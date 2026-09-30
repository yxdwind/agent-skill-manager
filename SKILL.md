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
# Install (from PyPI; use `pip install -e .` for development)
pip install cn-skill-sync

# Check status across all products
askill status

# Sync all skills to all products
askill sync

# Install a new skill (local path, GitHub URL, or skills.sh shorthand)
askill install anthropics/skills@pdf
askill sync
```

## When to Use

- User wants to install a skill to multiple AI products simultaneously
- User asks "sync skills between products" or "install skill to all agents"
- User wants to check which products have which skills
- User asks to remove a skill from all products
- User wants to update/reinstall an installed skill from its source (`askill update`)
- User asks whether a skill is safe to install or keep (`askill audit`, `askill verify`)
- User wants to find skills in the skills.sh registry (`askill search`)
- User installed skills via `npx skills add` or a product UI and wants them everywhere (`askill adopt all`)

## When NOT to Use

- Managing skills for one product only - the product's own UI is fine
- Prompts, MCP servers, or plugins - askill only manages SKILL.md skill directories

## Commands

| Command | Description |
|---------|-------------|
| `askill status [name]` | Show installation status across all 15 products |
| `askill sync [name]` | Sync skill(s) from central repo to all products |
| `askill list` | List all skills in central repository (with audit scores) |
| `askill install <path\|url\|owner/repo@skill>` | Install a skill (spec + security checks run by default; `--no-audit` skips, `--audit` prints the full report) |
| `askill search <query> [--install N]` | Search the skills.sh registry; `--install N` installs that result |
| `askill verify [name]` | Check skills against the agentskills.io spec |
| `askill audit [name]` | Full security audit report (prompt injection / dangerous code / secrets) |
| `askill adopt <platform\|all> [name]` | Adopt skills from one product (or every product) into the central repo |
| `askill remove <name>` | Remove a skill from central repo and all products |
| `askill update [name]` | Check/apply updates for skills installed from GitHub |
| `askill watch` | Auto-sync on every change (native fs events, Ctrl+C to stop) |
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
    "linux_path": HOME / ".newproduct" / "skills",  # omit (or None) if no Linux build
    "sync_method": "symlink",
    "note": "Description",
    "extra_dirs_macos": [],
    "extra_dirs_windows": [],
    "extra_dirs_linux": [],
}
```

## Architecture

All skills live in `~/.agents/skills/` (the emerging universal standard). 
The `askill sync` command creates symlinks (macOS/Linux) or junctions 
(Windows, no admin rights needed) to each product's skill directory. 
Desktop/IDE products without a Linux build are skipped on Linux.

```
~/.agents/skills/          ← Central Repository (single source of truth)
  └── my-skill/
      └── SKILL.md
           │
           ├── link → ~/.openclaw-autoclaw/skills/my-skill/
           ├── link → ~/.config/agents/skills/my-skill/
           ├── link → ~/.workbuddy/skills/my-skill/
           ├── link → ~/.trae-cn/skills/my-skill/
           ├── link → ~/.codebuddy/skills/my-skill/
           ├── link → ~/.comate/skills/my-skill/
           └── link → ~/.qoder-cn/skills/my-skill/
```

For detailed product paths and configuration, see `docs/product-paths.md`.
