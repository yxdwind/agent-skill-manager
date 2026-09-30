<div align="center">

<img src="docs/logo.png" alt="Agent Skill Manager logo" width="140"/>

# Agent Skill Manager

[English](README.en.md) | [简体中文](README.md)

[![CI](https://github.com/yxdwind/agent-skill-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/yxdwind/agent-skill-manager/actions/workflows/ci.yml) [![Tests](https://img.shields.io/badge/Tests-161%20passed-22c55e)](tests/)
[![skills.sh](https://skills.sh/b/yxdwind/agent-skill-manager)](https://skills.sh/yxdwind/agent-skill-manager)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-0078D4?logo=linux&logoColor=white)](https://github.com/yxdwind/agent-skill-manager)
[![License](https://img.shields.io/badge/License-MIT-22c55e?logo=opensourceinitiative&logoColor=white)](LICENSE)
[![Products](https://img.shields.io/badge/Products-15%20supported-8b5cf6)](#supported-products)

**Write once, sync everywhere** — Cross-platform skill management for 15 domestic Chinese AI agent products.

[Install](#install) · [Usage](#usage) · [Security Audit](#security-audit) · [Architecture](#architecture)

</div>

---

## The Problem

Every Chinese AI agent product keeps its skills in its own directory. Developing one skill means manually copying it to every product:

```
~/.openclaw-autoclaw/skills/my-skill/  <- AutoClaw2
~/.config/agents/skills/my-skill/     <- Kimi
~/.workbuddy/skills/my-skill/         <- WorkBuddy
~/.trae-cn/skills/my-skill/           <- Trae CN
~/.codebuddy/skills/my-skill/         <- CodeBuddy
~/.comate/skills/my-skill/            <- Comate
~/.qoder-cn/skills/my-skill/          <- Qoder CN
... and again, every time you change it
```

**agent-skill-manager** solves this with a central repository + one-command distribution: edit once, sync everywhere.

## Supported Products (15)

| Product | Company | macOS Path | Windows Path | Linux Path | Sync Method |
|---------|---------|-----------|--------------|------------|-------------|
| AutoClaw2 | Zhipu | `~/.openclaw-autoclaw/skills/` | `%USERPROFILE%\.openclaw-autoclaw\skills\` | same as macOS | symlink/junction |
| Kimi | Moonshot AI | `~/.config/agents/skills/` | `%USERPROFILE%\.config\agents\skills\` | same as macOS | symlink/junction |
| MiniMax Code | MiniMax | `~/.agents/skills/` | `%USERPROFILE%\.agents\skills\` | same as macOS | native |
| WorkBuddy | Tencent | `~/.workbuddy/skills/` | `%USERPROFILE%\.workbuddy\skills\` | — | symlink + settings.json |
| Trae | ByteDance | `~/.trae/skills/` | `%USERPROFILE%\.trae\skills\` | — | symlink/junction |
| Trae CN | ByteDance | `~/.trae-cn/skills/` | `%USERPROFILE%\.trae-cn\skills\` | — | symlink/junction |
| TRAE SOLO CN | ByteDance | `~/.trae-cn/skills/` (shared with Trae CN) | `%USERPROFILE%\.trae-cn\skills\` | — | symlink/junction |
| DuMate | Baidu | App-managed | App-managed | App-managed (.zip pack works) | pack .zip upload |
| CodeBuddy | Tencent | `~/.codebuddy/skills/` | `%USERPROFILE%\.codebuddy\skills\` | same as macOS | symlink + settings.json |
| Comate / Wenxin Kuaima | Baidu | `~/.comate/skills/` | `%USERPROFILE%\.comate\skills\` | same as macOS | symlink/junction |
| Qoder CN | Alibaba | `~/.qoder-cn/skills/` | `%USERPROFILE%\.qoder-cn\skills\` | — | symlink/junction |
| Qoder CN IDE | Alibaba | `~/.qoder-cn/skills/` (shared with Qoder CN) | `%USERPROFILE%\.qoder-cn\skills\` | — | symlink/junction |
| QwenWork / Qianwen Office | Alibaba | `~/.qwenworkcn/skills/` | `%USERPROFILE%\.qwenworkcn\skills\` | — | symlink/junction |
| DoubaoWork | ByteDance | `~/.super_doubao/super-doubao-runtime/workspace/.user_skills/` | `%LOCALAPPDATA%\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\` | — | symlink/junction |
| ZCode | ZCode | `~/.zcode/skills/` | `%USERPROFILE%\.zcode\skills\` | same as macOS | symlink/junction |

> **Linux support (v0.10.0)**: CLI-based products (AutoClaw2, Kimi, MiniMax Code, CodeBuddy, Comate, ZCode) use the same dotdir convention + native symlinks on Linux; DuMate's .zip pack works everywhere. Desktop/IDE apps without a Linux build are skipped automatically (`askill products` shows N/A) - add a `linux_path` when a build ships.

## How It Works

![Architecture](docs/architecture.svg)

**Core design**: the central repository `~/.agents/skills/` is the single source of truth. Skills are distributed to all products via symlinks (macOS/Linux) or junctions (Windows). For DuMate, which does not expose a filesystem, skills are packed as .zip for manual upload. QwenWork and DoubaoWork are synced the same way via junctions.

- **Windows**: junction via `mklink /J`, no admin rights needed
- **macOS / Linux**: symlink via `ln -s`
- **Automatic fallback**: falls back to copying if link creation fails
- **Zero dependencies**: Python standard library only

![Demo](docs/demo.svg)

## Install

```bash
# Development install (recommended)
# Install from PyPI (recommended)
pip install cn-skill-sync

# Development install
cd agent-skill-manager
pip install -e .

# If pip hits TLS certificate issues
python -m pip install -e . --no-build-isolation
```

After installation, the `askill` command is available globally.

You can also install the skill definition through the `npx skills` ecosystem:

```bash
npx skills add yxdwind/agent-skill-manager
```

## Usage

```bash
# Show installation status across products (with security audit score column)
askill status

# Sync all skills to all products
askill sync

# Sync a specific skill
askill sync my-skill

# List all skills in the central repository (with audit scores)
askill list

# Install a skill (local path or GitHub URL)
askill install /path/to/skill-folder
askill install --sync /path/to/skill-folder          # auto-sync after install
askill install --audit /path/to/skill-folder         # run security audit after install
askill install --sync --audit <github-url>           # sync + audit together

# skills.sh ecosystem shorthand (v0.11.0, same syntax as npx skills)
askill search pdf                                    # search the skills.sh registry
askill install anthropics/skills                     # owner/repo shorthand
askill install anthropics/skills@pdf                 # one skill inside a repo
askill install https://skills.sh/anthropics/skills/pdf   # skills.sh page URL

# Multiple GitHub URL formats are supported (default branch auto-detected)
askill install --sync https://github.com/user/repo                                # repo root SKILL.md
askill install --sync https://github.com/user/repo/tree/main/my-skill             # subdirectory on a branch
askill install --sync https://github.com/user/repo/blob/main/my-skill/SKILL.md    # direct SKILL.md link

# Adopt skills from one platform into the central repo and sync everywhere
askill adopt autoclaw my-skill                       # adopt one skill from AutoClaw
askill adopt kimi                                    # adopt all skills from Kimi

# Static security audit: prompt injection / dangerous code / secrets / binaries
askill audit                                         # audit all skills
askill audit my-skill                                # audit one skill

# Live watch: auto-sync on every skill change (event-driven since v0.10.0)
askill watch                                         # watch ~/.agents/skills/ (native fs events)
askill watch --interval 5                            # fallback poll interval (s)

# Skill upgrades: GitHub-origin tracking + one-command update (v0.8.0)
askill update --check                                # list available updates
askill update my-skill                               # update one skill & sync
askill update                                        # update all tracked skills

# Remove a skill from all products
askill remove my-skill

# Pack a skill as .zip for DuMate
askill pack my-skill

# List all supported products
askill products
```

### Typical Workflow

```
1. askill status          <- check installation status
2. edit ~/.agents/skills/my-skill/SKILL.md
3. askill sync my-skill   <- distribute to 10 products
4. askill pack my-skill   <- .zip for DuMate
```

## Project Structure

```
agent-skill-manager/
├── pyproject.toml              # PEP 621 project config
├── setup.py                    # setuptools compatibility entry
├── docs/
│   ├── architecture.svg        # architecture diagram
│   ├── demo.svg                # terminal demo
│   └── product-paths.md        # per-product path reference
├── src/                        # package root (mapped as agent_skill_manager)
│   ├── __init__.py / __main__.py
│   ├── config/products.py      # 15 product definitions (incl. linux_path)
│   ├── controllers/cli.py      # CLI commands (12 commands)
│   ├── models/                 # TypedDict data shapes
│   ├── services/               # business logic (sync / audit / watch / sources
│   │                           #             / registry / spec)
│   └── utils/                  # filesystem.py (cross-platform file ops)
│                               # watcher.py (native fs events: inotify/kqueue/ReadDirectoryChangesW)
└── tests/                      # 161 tests
    ├── test_products.py
    ├── test_utils.py
    ├── test_core.py
    ├── test_adopt.py
    ├── test_security.py
    ├── test_cli.py
    ├── test_watch.py
    ├── test_watcher.py
    ├── test_registry.py
    └── test_spec.py
```

## skills.sh Ecosystem (v0.11.0)

[skills.sh](https://skills.sh) (by Vercel Labs) is the de-facto registry of the open Agent Skills ecosystem ([agentskills.io](https://agentskills.io) specification). askill integrates in three directions, all stdlib-only (urllib):

**① Consume** - install any skill from the registry, no Node.js required:

```bash
askill search pdf                        # search the registry (name / source / installs)
askill install anthropics/skills@pdf     # shorthand, same syntax as npx skills add
askill install https://skills.sh/anthropics/skills/pdf   # pasted page URLs work too
```

**② Publish** - the central repo `~/.agents/skills/` already uses the canonical layout (one directory with a SKILL.md per skill). Push it to GitHub and it can be indexed by skills.sh and read by every spec-compliant agent:

```bash
askill verify            # check against the agentskills.io spec (name/description/limits/dir match)
askill verify my-skill   # one skill; errors block indexing, warnings are advisory (e.g. body > 500 lines)
```

**③ Bridge** - skills installed via `npx skills add -g <repo>` into product directories can be pulled into the central repo and distributed to all domestic products:

```bash
npx skills add -g anthropics/skills      # install with the skills CLI first
askill adopt all                          # scan every product dir, adopt + distribute to 15 products
```

## Security Audit

`askill audit` runs a **zero-dependency static analysis** on skills. It starts at 100 points and deducts by severity (capped at 40 per category):

| Dimension | Severity | Examples |
|-----------|----------|----------|
| Prompt injection | critical | "ignore all previous instructions", safety bypass language |
| Dangerous code | critical/high | `curl \| sh`, `rm -rf /`, `exec()`, `shell=True` |
| Secrets & exfiltration | high/medium | reading `~/.ssh`, hardcoded API keys, webhook URLs |
| Binary files | high | bundled `.exe`/`.dll` executables |
| File integrity | high/medium | missing SKILL.md, oversized files, symlinks |

**Scoring & verdict**: A >= 90 (safe) - B >= 80 (safe) - C >= 70 (caution) - D >= 60 (risky) - F < 60 (dangerous)

Scores also appear in `askill list` and `askill status` output. Add `--audit` to install for a one-step "install + audit":

```bash
askill install --sync --audit https://github.com/user/repo/tree/main/my-skill
```

## Extend It

### Add a New Product

Edit `src/config/products.py` and append to the `PRODUCTS` list:

```python
{
    "name": "New Product",
    "short": "short-name",
    "macos_path": HOME / ".newproduct" / "skills",
    "windows_path": HOME / ".newproduct" / "skills",
    "linux_path": HOME / ".newproduct" / "skills",  # omit (or None) if no Linux build
    "sync_method": "symlink",  # symlink | native | pack
    "note": "description",
    "extra_dirs_macos": [],
    "extra_dirs_windows": [],
    "extra_dirs_linux": [],
}
```

### Run Tests

```bash
pip install pytest
pytest tests/ -v
```

## Related Projects

- [manage-my-skills](https://github.com/hchcx/manage-my-skills) — cross-platform skill manager for 20+ international products
- [awesome-agent-skills](https://github.com/libukai/awesome-agent-skills) — the ultimate Agent Skills guide
- [skills CLI](https://www.npmjs.com/package/skills) — npm-based agent skills package manager
- [skill-creator](https://github.com/yxdwind/agent-skill-manager) — skill authoring reference

## Contributors

Thanks to the following contributor:

- [**@GLM-5.2**](https://github.com/zai-org) — AI co-developer (Zhipu GLM-5.2)

## Security & Privacy

- [Security Policy (SECURITY.md)](SECURITY.md) — vulnerability reporting & security guidance
- [Privacy Policy (PRIVACY.md)](PRIVACY.md) — local-first data handling

## License

[MIT](LICENSE)
