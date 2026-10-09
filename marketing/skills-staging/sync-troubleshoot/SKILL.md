---
name: sync-troubleshoot
description: |
  Diagnose why a skill loads in some AI agent products but not others when
  using a central-repo + symlink setup (agent-skill-manager / askill, or any
  manual ~/.agents/skills junction/symlink layout). Walks a ordered checklist:
  directory presence, link vs real dir, per-product frontmatter requirements
  (e.g. QwenWork description_zh), settings.json skill switches, zip-only
  products, and stale/dangling links. Use when the user says a skill is
  missing, not loading, not showing up, or broken in a specific agent product.
version: 1.0.0
description_zh: |
  诊断技能在部分国产 AI Agent 产品里加载不出来的问题：按序排查中央仓库存在性、
  链接悬空或退化为复制、产品级 frontmatter 要求（如 QwenWork 的 description_zh）、
  settings.json 技能开关、zip 导入类产品、启动时扫描时机等，定位根因并给出修复命令。
  当用户说某个技能没装上、加载不出来、列表里看不到、某产品里坏了时使用。
---

# Sync Troubleshoot

Diagnose "skill X does not load in product Y". Work the checklist in order;
stop at the first root cause found, but report skipped checks briefly.

## Step 0 - Establish the facts

Ask for / determine:

1. Which skill, which product(s) load it, which do not.
2. Is the setup askill-managed (central `~/.agents/skills/` + links) or manual?
3. OS (Windows/macOS/Linux) - link semantics differ.

## Step 1 - Is the skill in the central repo?

Check `~/.agents/skills/<skill>/SKILL.md` exists. Missing here means it was
never installed (or the central root moved) - fix at install, not at the
product.

## Step 2 - Link health at the product

For each affected product, resolve its skills dir (see Step 5 for the table)
and check:

- **Dangling link:** the junction/symlink exists but its target is gone.
  Fix: re-run `askill sync <skill>`.
- **Real dir, not a link:** the product dir holds a copy, not a link. It will
  silently diverge from central on every edit. Fix: `askill sync <skill>`
  (conflict protection will warn if contents differ; review the diff first).
- **Stale copy:** a link exists but product shows old content - rare; check
  whether the user edited the product copy through the link, then reverted the
  central file separately.

On Windows, junctions need no admin rights, but **symlinks do** (or Developer
Mode). A "real dir" that was meant to be a link often means link creation
fell back to copy - check askill sync output for `copy` vs `junction`.

## Step 3 - Frontmatter requirements per product

Some products require extra frontmatter and fail silently when it is absent:

- **QwenWork:** requires `name`, `version`, `description`, `description_zh`.
  Missing `description_zh` is the classic "installed but never shows up" cause.
- Others: check the product's docs. Run `askill verify <skill>` - it checks
  per-product frontmatter for all supported products.

Fix by adding the missing fields to the central SKILL.md, then `askill sync <skill>`.

## Step 4 - Product-side switches and quirks

- **settings.json skill switches** (WorkBuddy, CodeBuddy): the skill must be
  registered and enabled in `{"skills": {"<name>": true}}`. A synced skill
  with the switch off will not load. Fix: re-run `askill sync` (registers) or
  toggle in the product.
- **Zip-only products** (DuMate): no filesystem path exists. The skill loads
  only from a zip uploaded in-app. Run `askill pack <skill>` and re-import;
  sync output will never mention pack products - that is expected, not a bug.
- **Shared skill dirs** (Trae CN + TRAE SOLO CN on `~/.trae-cn/skills/`;
  Qoder CN + IDE on `~/.qoder-cn/skills/`): one fix covers both products -
  do not look for a second directory.
- **Restart the product:** most desktop products scan skills at startup only.
  A skill synced after launch appears only after a full restart of the app.

## Step 5 - Product path reference

| Product | skills dir (macOS/Linux) | Windows |
|---|---|---|
| AutoClaw2 | `~/.openclaw-autoclaw/skills/` | same |
| Kimi | `~/.config/agents/skills/` (+ `~/.kimi-code/skills/`) | same |
| MiniMax Code | `~/.agents/skills/` (native, no link needed) | same |
| WorkBuddy | `~/.workbuddy/skills/` | same |
| Trae / Trae CN | `~/.trae/skills/`, `~/.trae-cn/skills/` | same |
| CodeBuddy | `~/.codebuddy/skills/` | same |
| Comate | `~/.comate/skills/` | same |
| Qoder CN | `~/.qoder-cn/skills/` | same |
| QwenWork | `~/.qwenworkcn/skills/` | same |
| DoubaoWork | `~/.super_doubao/.../.user_skills/` | `%LOCALAPPDATA%\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\` |
| ZCode | `~/.zcode/skills/` | same |
| DuMate | none (zip import) | none |

## Report format

```
ROOT CAUSE: <one sentence>
FIX: <exact commands/steps, in order>
VERIFIED: <which checks passed, or "user to verify">
```

One root cause per report. If multiple products fail for different reasons,
report the general cause plus a per-product line. Do not run destructive
fixes (deleting dirs, force-overwriting) yourself - state the command and let
the user confirm.
