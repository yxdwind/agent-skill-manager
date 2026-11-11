---
name: askill-ops
description: |
  Drive the askill CLI (agent-skill-manager) to manage skills across 15
  Chinese AI agent products: check status, sync the central repo to every
  product, install skills from GitHub or skills.sh, export/import a team
  manifest, run security and attention-budget audits, pack zips for
  upload-only products, and detect drift. Use when the user asks to sync,
  install, check, audit, or troubleshoot their skills, or mentions askill,
  skill sync across products, or a skill missing in some agent.
version: 1.0.0
description_zh: |
  驱动 askill CLI（agent-skill-manager）跨 15 个国产 AI Agent 产品管理技能：
  查看状态、把中央仓库同步到全部产品、从 GitHub 或 skills.sh 安装技能、
  导出/对齐团队 manifest、跑安全与注意力预算审计、为仅支持上传的产品打包、
  检测漂移。当用户要求同步、安装、检查、审计技能，或提到 askill、技能跨产品
  同步、某个产品里技能缺失时使用。
---

# askill Ops

Drive the `askill` CLI (from [agent-skill-manager](https://github.com/yxdwind/agent-skill-manager),
`pip install cn-skill-sync`) to manage skills across 15 Chinese AI agent
products. The model: `~/.agents/skills/` is the single source of truth;
every product directory is a link to it.

## Mental model

- **Central repo**: `~/.agents/skills/` - the only real copy lives here.
- **Products**: AutoClaw2 / Kimi / MiniMax / WorkBuddy / Trae / Trae CN /
  TRAE SOLO / DuMate / CodeBuddy / Comate / Qoder CN / Qoder CN IDE /
  QwenWork / DoubaoWork / ZCode. Each has its own directory (or shares one,
  or scans central natively, or imports zips - see `askill products`).
- **Sync**: links, not copies. Editing central updates every product.

## Core commands

```bash
askill status [skill]        # which products have which skill (json: --json)
askill sync [skill] [--force]  # distribute central -> all products
askill list                  # what is in the central repo
askill products              # where each product's skills dir is
askill install <source>      # local path / GitHub URL / owner/repo@skill
askill install --manifest <path>  # align central to a team manifest
askill bundle [--output <p>] # export the manifest for teammates
askill verify [skill]        # agentskills.io spec + per-product frontmatter
askill audit [skill]         # security scan (injection / dangerous code / secrets)
askill audit --residency     # attention-budget: context cost of every description
askill drift [product]       # product-side skills that forked from central
askill update [--check]      # pull updates for git-tracked skills
askill pack <skill>          # zip for upload-only products (DuMate)
askill remove <skill>        # DESTRUCTIVE - see safety rules
askill watch                 # blocking loop; auto-sync on every save
```

## Recipes

**User says "my skills are out of sync"**: run `askill status`, report the
summary, then `askill sync`. If output shows `SKIP conflict`, do NOT pass
`--force` - a real directory with different content exists in that product;
report it and suggest `askill adopt` to bring the changes into central first.

**User says "install <name>"**: `askill install owner/repo@skill` (or the
GitHub URL). The install runs a spec + security check automatically; if it
prints a SECURITY WARNING, show the findings and let the user decide before
`askill sync`. If it prints `[product]` frontmatter issues, add the missing
fields to the central SKILL.md first, then sync.

**User asks "why is a skill not loading in product X"**: check in order -
`askill status <skill>` (missing?), then `askill verify <skill>` (missing
frontmatter, e.g. QwenWork needs `description_zh`?), then whether the
product needs a restart. For zip-only products (DuMate) run
`askill pack <skill>` and tell the user to import it in the app.

**New machine / teammate setup**: `askill install --manifest
askill-manifest.json` after getting the manifest from the team repo (or
`askill bundle` to produce one from this machine).

**Before sharing a skill**: `askill verify <skill>` then
`askill audit <skill>` - grade below A means report the findings first.

## Safety rules

- `remove` and `sync --force` are destructive. Never run them without the
  user's explicit confirmation in the current conversation.
- `publish` pushes to a public GitHub repository - confirm the repo and the
  skill list with the user first.
- `watch` blocks the terminal - run it only when the user asks for a
  long-running watcher, not as a drive-by.
- If `sync` reports settings.json failures (locked by a running IDE), report
  that the skill is linked but not enabled, and suggest restarting the IDE
  and re-running sync. Do not retry in a loop.

## Output conventions

- Prefer `--json` when the result will be post-processed; human tables are
  for direct display.
- Exit codes: 0 success, 1 operational failure, 2 usage error - check them
  instead of parsing prose when scripting.
- Every command supports `-q/--quiet`; audit and status support `--json`.
