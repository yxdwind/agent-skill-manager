# Changelog

All notable changes to **agent-skill-manager** are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

> The package is published on PyPI as **`cn-skill-sync`** (the import
> name `agent_skill_manager` is kept for the python package to avoid
> confusion with skill-creator projects). ``pip install cn-skill-sync``.

## v0.18.2 (2026-10-11)

### Fixed
- CI `Lint (ruff)` was red since v0.17.0: RUF001 flagged the fullwidth
  punctuation in the Chinese UI strings (`：` `（` `）` `，` …) as "ambiguous"
  characters. For CJK text those are the correct characters, not homoglyph
  look-alikes, so `lint.allowed-confusables` now allowlists CJK punctuation.
  RUF001 keeps its real value elsewhere (Cyrillic / Greek look-alikes in
  identifiers and URLs) instead of being disabled outright. The two now-
  redundant `# noqa: RUF001` comments were removed.
- CI `Type check (mypy)` was red since v0.17.0: `src/services/audit.py`
  appended a `dict[str, object]` to `list[Finding]`. `Finding` is now split
  into `_FindingCore` (required keys) and `Finding(_FindingCore,
  total=False)`, which adds the optional `dev_context` marker — so the
  dev/test-path tag is part of the declared schema rather than an untyped
  extra key, and `_scan_text`'s finding literal is checked against it.

## v0.18.1 (2026-10-11)

### Fixed
- `agent_skill_manager.completion` subpackage `__init__.py` shipped with an
  unclosed docstring (syntax error) in 0.18.0. It was never imported by the
  runtime code, so 0.18.0 worked at runtime and all tests passed, but the
  file was invalid and broke static checks. The subpackage is now valid
  (exposes `COMPLETION_DIR`) and `import agent_skill_manager.completion`
  works.
- `release.yml` no longer triggers on both `release: published` and
  `push: tags` — that double-trigger fired two publish runs per release and
  the second always failed with a "version already exists" 409 on PyPI. It
  now triggers on tag push only (with `workflow_dispatch` for manual re-runs).

## v0.18.0 (2026-10-11)

### Added
- `askill --version` global flag (the `version` subcommand still works).
- `askill publish --target <short>` (repeatable): scope the per-product
  frontmatter gate to the products you actually publish to, so an unrelated
  product's requirement can no longer block a single-platform publish.
- Shell-completion scripts (`askill.bash` / `_askill` / `askill.fish`) are
  now bundled inside the PyPI wheel via package-data; pip users can source
  them from the installed package location.
- README "Known Limitations" section (settings.json lock, watch in
  restricted environments, drift permissions, publish gate, audit FPs).

### Changed
- `askill update --check` human output now prints a header with a status
  legend (up-to-date / update-available / untracked / missing / error) so
  the `missing` status is self-explanatory.
- `askill watch` prints a clearer, flushed startup banner (watching path,
  mode, Ctrl+C hint) so users can confirm it is alive.
- Cross-referenced the PyPI package name (`cn-skill-sync`) and the GitHub
  repo name (`agent-skill-manager`) in the README top and the PyPI
  description to lower discovery friction.

## v0.17.0 (2026-10-11)

### Fixed

- **sync**: 当目标产品 IDE 正在运行并锁住 `settings.json`（Windows 常见，报 `WinError 5` / 拒绝访问）时，链接仍会创建，但 `sync` 末尾现在聚合打印醒目的提示，明确列出「已链接但未启用」的产品与 `settings.json` 路径，并指导用户关闭/重启 IDE 后重跑 `askill sync` 让 skill 真正生效（不再静默白做）。

### Changed

- **audit**: 提升安全评测精度，降低误报——
  - 良性 low 级命中（URL、`.env` 引用、`child_process`）每类单独封顶（`_MINOR_CAP=10`），不再刷满分类上限把无害的大 skill 误评成 F；
  - 开发/测试路径（`test/ tests/ bin/ scripts/ dev/ examples/ fixtures/ node_modules/ dist/ build/ docs/` 等）里的发现降权并标注 `(dev/test path - verify)`，保留供人工复核但不拉低评分；可用 `ASKILL_AUDIT_DEV_MODE`（`downweight` 默认 / `skip` / `off`）切换；
  - 收紧两处过宽正则：`regex.exec()` 不再误判为「动态代码执行」（`child_process.exec` 仍由中危规则覆盖）；移除凭据检测对裸词 `credentials` 的匹配，防御性「拒绝携带凭据的 URL」代码不再被误判为「读取敏感凭据文件」。
  - 实测评分对比（真实数据）：`archify` 57/F → 77/C、`book-to-skill` 42/F → 77/C；含真实 prompt injection 的 `agently-mail` 仍保持 57/F 不被洗白。

## v0.16.1 (2026-10-05)

### Fix

- **publish**: preserve leading slash on absolute Unix remote paths

## v0.16.0 (2026-10-05)

### Feat

- **cli,v016**: exit-code contract + askill drift scan

### Fix

- **watcher**: signal event on reader-thread failure (Windows root deletion)

## v0.15.0 (2026-10-04)

### Feat

- **cli**: R3 — list --json publish fields + watch --json event stream
- **publish**: askill publish — one-command skill publishing (v0.15.0 R2)
- **new**: askill new skill scaffolding (v0.15.0 R1)

## v0.14.2 (2026-10-03)

### Fix

- **sync**: audit P3-7/8 — per-worker exception fallback + shared-dir failure propagation

## v0.14.1 (2026-10-03)

### Fix

- **cli**: audit P1/P2 — dedupe sync call, install-None crash, quiet/json contract, exit codes

## v0.14.0 (2026-10-02)

### Feat

- **cli**: global --quiet / --json + golden-sample fixtures + CHANGELOG

### Fix

- **test**: write_text 显式声明 encoding 防止 Windows cp1252 截断中文
- **sync,sources**: three P0 hardening fixes (v0.13.x)

### Refactor

- **perf,quality**: concurrent sync/audit + ruff + mypy in CI
- **cli**: argparse subcommands + status adaptive table + drop dead field

## v0.13.0 (2026-10-01)

### Feat

- v0.13.0 跨产品一致性对齐——sync 冲突保护 + 按产品 frontmatter 校验 + 统一输出
- v0.12.0 A 档优化——install 默认安全检查 + 空仓库引导 + search --install + SKILL.md 触发面补全
- v0.11.0 接入 skills.sh 生态（search + owner/repo@skill 简写安装 + verify 规范检查 + adopt all）
- v0.10.0 Linux 支持 + askill watch 升级为原生文件事件驱动
- v0.9.0 新增 Trae CN/TRAE SOLO CN/Qoder CN/Qoder CN IDE/ZCode/AutoClaw2 支持
- v0.8.0 askill watch + update (origin tracking, auto sync/clean/audit)
- PyPI 包名切换 askill + 第二梯队推广资料
- audit/status 输出增加来源尾注（自传播）

### Fix

- 四个产品路径测试改为平台感知，Linux 上断言无 linux_path
- 测试夹具补 linux_path，修复 ubuntu CI 失败

## v0.7.0 (2026-09-07)

## v0.6.0 (2026-08-31)

### Feat

- 新增千问办公(QwenWork)与豆包工作(DoubaoWork)支持，产品数 9 -> 11
- list/status 命令增加安全评测评分显示
- 新增安全评测(audit)功能，支持 skill 静态安全分析
- install --sync 支持 GitHub URL 一键安装并同步到所有平台

### Fix

- get_status now checks extra_dirs; add detailed comments and tests
- sync extra_dirs (e.g. AutoClaw ~/.openclaw-autoclaw/skills)

### Refactor

- 完善类型注解（TypedDict/ProductSpec/Finding），修复 editable 安装映射
- reorganize src into layered subpackages (config/controllers/models/services/utils)
- flatten package into src/ and relocate egg-info

## v0.1.0 (2026-08-11)
