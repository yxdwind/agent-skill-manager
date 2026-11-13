# GitHub Release 页面预生成文案（v0.20.1 → v0.25.0）

> 用法：GitHub → Releases → Draft a new release → Choose a tag 选对应 tag →
> 把下面对应段落整段粘贴到描述框 → Publish。全部是英文（Release 页惯例），共 6 个版本。
> 目标：把你的操作压到每个版本约 1 分钟。

---

## Tag: v0.25.0

**Title:** v0.25.0 — Dead-link cleanup, doctor naming, local `get`

```
### Feat
- `askill sync --gc`: sweep product dirs for dangling junctions/symlinks. Only links whose target is gone AND whose name is not a central skill are removed — central-named dead links are left for a normal sync to relink, real directories are never touched (drift/adopt territory).
- `askill doctor` now names the dead links per product, and its broken-links check points at both escape hatches (relink via `askill sync`, remove stale via `askill sync --gc`).
- `askill get` accepts a local skill directory (stdout / `--dir` / `--list`), same read-only semantics as the repo flow.

Full changelog: https://github.com/yxdwind/agent-skill-manager/blob/master/CHANGELOG.md
```

---

## Tag: v0.24.0

**Title:** v0.24.0 — Per-product `--only` targeting, update snapshots & rollback

```
### Feat
- `askill sync [skill] --only <short...>` and `askill install --sync --only <short...>`: distribute to the named products only (shorts from `askill products`). Unknown shorts abort with the valid list.
- `askill rollback <skill> [--list]`: every `askill update` now snapshots the outgoing version to `~/.agents/.askill-versions/` (outside central, invisible to inventory) before replacing it — a failed update no longer loses the skill. Rollback restores and re-syncs, consuming the snapshot.
- README numbers now carry their cohort/reproduce command.

Full changelog: https://github.com/yxdwind/agent-skill-manager/blob/master/CHANGELOG.md
```

---

## Tag: v0.23.0

**Title:** v0.23.0 — `askill doctor`: environment & repository health diagnostics

```
### Feat
- One command answering "why is askill misbehaving here": git availability, configured proxies (git config + env) with a live TCP reachability probe (the unreachable-local-proxy failure behind most install-from-GitHub reports), central repo state including orphan tracking entries, per-product link health (broken links, real dirs shadowing central skills), and settings.json lock detection.
- Strictly read-only. `--json` for bug reports (the bug template now asks for it). Exit 1 only on FAIL-severity findings.

Full changelog: https://github.com/yxdwind/agent-skill-manager/blob/master/CHANGELOG.md
```

---

## Tag: v0.22.0

**Title:** v0.22.0 — `askill get`, archive install, proxy-aware clone errors

```
### Feat
- `askill get <source>`: try a skill without installing it — SKILL.md to stdout, `--dir` borrows the full folder to a temp path, `--list` shows what a repo offers (borrowed from asm's get/borrow; strictly read-only).
- `askill install` accepts local `.zip` / `.skill` archives (skills.sh convention): root or single-folder layouts, zip-slip guard, frontmatter-name fallback, multi-skill archives refused. DuMate round trip closed.
- Git clone failures now name the cause: a configured-but-down local proxy (Clash/v2rayN global gitconfig — a daily reality for domestic users) prints targeted hints with the escape hatch instead of raw stderr.
- Trust infrastructure: Dependabot, CodeQL (weekly), Contributor Covenant, bug/feature/audit-false-positive issue templates.

Full changelog: https://github.com/yxdwind/agent-skill-manager/blob/master/CHANGELOG.md
```

---

## Tag: v0.21.0

**Title:** v0.21.0 — Team manifest sync & attention-budget audit

```
### Feat
- `askill bundle` / `askill install --manifest <path>`: export the local skill list as a commit-ready JSON (with reinstall sources from tracking); teammates align with one command. Zero server (borrowed from skillfish).
- `askill audit --residency`: rank every central skill by the context its description costs — CJK-aware token estimate + directory size. The attention budget for heavy users (borrowed from asm's residency audit).
- `askill-ops`: a skill that teaches agents to drive askill end to end, published at yxdwind/skills (install: `askill install yxdwind/skills@askill-ops`).
- Competitive teardown of 8 peer projects: docs/competitive-research-2026-11.md.

Full changelog: https://github.com/yxdwind/agent-skill-manager/blob/master/CHANGELOG.md
```

---

## Tag: v0.20.1

**Title:** v0.20.1 — Wheel packaging fix (sync subpackage shipped)

```
### Fix
- The v0.20.0 wheel was missing the `agent_skill_manager.services.sync` subpackage (setuptools `packages` allowlist missed the new package; in-repo CI could not catch it). v0.20.1 ships the complete wheel — verified by a clean-venv smoke install.
- CI: the release workflow now smoke-installs the built wheel before publishing, so an import-broken wheel can never reach PyPI again.

Note: if you pinned v0.20.0, upgrade to v0.20.1+. (Users without a pin were never affected.)
```
