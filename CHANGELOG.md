# Changelog

All notable changes to **agent-skill-manager** are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

> The package is published on PyPI as **`cn-skill-sync`** (the import
> name `agent_skill_manager` is kept for the python package to avoid
> confusion with skill-creator projects). ``pip install cn-skill-sync``.

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
