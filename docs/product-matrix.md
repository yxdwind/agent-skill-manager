# 产品能力矩阵盘点（v0.13.0 修复前基线）

> 盘点日期：2026-10-01　基线版本：v0.12.0（commit ff4cc40）
> 方法：源码走读（`src/` 全部服务层 + CLI）＋ Windows 本机实测 ＋ `docs/product-paths.md` / README 交叉核对。
> 证据标注：`[代码]` 引用 file:line；`[实测]` 2026-10-01 本机 Windows 验证；`[文档]` docs/product-paths.md 或官方链接。
> 缺口类型：**A = askill 侧可修**、**B = 产品硬限制（文档明示+优雅跳过）**、**C = 待真机确认**。

---

## 一、总览矩阵

### 1.1 路径与同步机制

| # | 产品 | short | macOS | Windows | Linux | sync_method | extra_dirs | settings_file |
|---|------|-------|:-----:|:-------:|:-----:|-------------|:----------:|:-------------:|
| 1 | AutoClaw2 | `autoclaw2` | ✅ | ✅ | ✅ | symlink | — | — |
| 2 | Kimi | `kimi` | ✅ | ✅ | ✅ | symlink | ✅ `~/.kimi-code/skills/` | — |
| 3 | MiniMax Code | `minimax` | ✅ | ✅ | ✅ | **native** | — | — |
| 4 | WorkBuddy | `workbuddy` | ✅ | ✅ | ❌ | symlink | — | ✅ |
| 5 | Trae | `trae` | ✅ | ✅ | ❌ | symlink | — | — |
| 6 | Trae CN | `traecn` | ✅ | ✅ | ❌ | symlink | — | — |
| 7 | TRAE SOLO CN | `traesolo` | ✅ | ✅ | ❌ | symlink | — | — |
| 8 | DuMate | `dumate` | — | — | — | **pack** | — | — |
| 9 | CodeBuddy | `codebuddy` | ✅ | ✅ | ✅ | symlink | — | ✅ |
| 10 | Comate | `comate` | ✅ | ✅ | ✅ | symlink | — | — |
| 11 | Qoder CN | `qodercn` | ✅ | ✅ | ❌ | symlink | — | — |
| 12 | Qoder CN IDE | `qodercnide` | ✅ | ✅ | ❌ | symlink | — | — |
| 13 | QwenWork | `qwenwork` | ✅ | ✅ | ❌ | symlink | — | — |
| 14 | DoubaoWork | `doubaowork` | ✅ | ✅ | ❌ | symlink | — | — |
| 15 | ZCode | `zcode` | ✅ | ✅ | ✅ | symlink | — | — |

依据：`src/config/products.py:26-209`，与 README 支持矩阵、`docs/product-paths.md` 一致。

### 1.2 共享目录与特殊约束

| 约束 | 涉及产品 | 依据 |
|------|---------|------|
| 共享同一技能目录 `~/.trae-cn/skills/` | Trae CN、TRAE SOLO CN | [文档] product-paths.md §7（product.json dataFolderName 实证） |
| 共享同一技能目录 `~/.qoder-cn/skills/` | Qoder CN、Qoder CN IDE | [文档] product-paths.md §12（product.json 实证） |
| frontmatter 额外要求 `name`+`version`+`description`+`description_zh` | QwenWork | [文档] product-paths.md §13（阿里官方） |
| 仅 zip 导入，无文件系统目录 | DuMate | [文档] product-paths.md §8 |
| 原生扫描 central（`~/.agents/skills/`），无需同步 | MiniMax | [代码] products.py:58 |
| 额外原生扫描 central（配置目录已建模，无需处理） | AutoClaw2、ZCode、CodeBuddy CLI | [代码] products.py note 字段 |
| 项目级技能目录（`<project>/.trae*/skills/`，超出用户级管理范围） | Trae、Trae CN | [文档] product-paths.md §5-6 |
| 系统技能目录（产品内置，与用户技能隔离） | DoubaoWork（`.skills/` 与 `.user_skills/` 并存） | [文档] product-paths.md §14 |

### 1.3 本机 Windows 实测快照（2026-10-01）

| 产品 | 配置目录 | skills 目录 | 备注 |
|------|---------|------------|------|
| AutoClaw2 | ✅ | ✅ 122 项 | 重度使用 |
| Kimi | ✅ | ✅ 主 10 项 + extra 5 项 | extra_dirs 唯一使用者 |
| MiniMax | ✅（=central） | ✅ 16 项 | central 本体 |
| WorkBuddy | ✅ | ✅ | settings.json 实测存在 |
| Trae / Trae CN | ✅ | ✅ 10 / 1 项 | |
| CodeBuddy | ✅ | ✅ 16 项 | **settings.json 含 `skills` 开关字典，schema 与 WorkBuddy 一致**（实测确认） |
| Comate | ✅ | ✅ 10 项 | |
| Qoder CN | ✅（`.qoder-cn` 存在） | ❌ 未创建 | sync 时由 create_link 自动补建 [代码] filesystem.py:55 |
| QwenWork | ✅ | ✅ 165 项 | 重度使用 |
| DoubaoWork | ✅ | ✅ `.user_skills/` 存在 | 深层路径与代码声明一致 |
| ZCode | ✅（`.zcode` 存在） | ❌ 未创建 | 同上 |
| DuMate | — | — | App 内管理，无目录可测 |

---

## 二、命令级行为矩阵（当前实现）

行为由 `sync_method` × 平台可用性推导，以下为**现状**（含不一致点，★ 标注）：

| 命令 | symlink（11 产品） | symlink + 无路径（Linux 上 8 产品） | native（MiniMax） | pack（DuMate） |
|------|--------------------|--------------------|-------------------|----------------|
| `sync` | 建 junction/symlink + extra_dirs + settings 写入；输出 `ok junction` | 输出 `n/a`，★无原因说明 [代码] sync.py:178-181 | `ok native` | `skip (use 'pack' command)` |
| `status` | `ok link/copy` / `--`（含 extra_dirs 检查） | `n/a` | `ok` | 恒为 `manual`，★不反映 zip 是否已打包 [代码] sync.py:83-84 |
| `watch` 变更 | 同步 + extra_dirs + settings | 同上（`n/a`） | 同步 | ★静默跳过，不提示可重新 pack [代码] sync.py:171-175 |
| `watch` 删除清理 | 删链接 + settings 移除 | 跳过（无路径） | 跳过 | 跳过 |
| `remove` | 删链接 + settings 移除（settings 项★误标 `workbuddy-settings` [代码] sync.py:608） | 跳过 | 跳过 | 跳过 |
| `adopt` | 扫描目录收编 | 跳过（无路径） | 明确提示不支持 | 明确提示不支持 |
| `update` | 按 git origin 逐 skill，与产品无关 | 同左 | 同左 | 同左 |
| `products` | 显示路径 + 存在性 | `N/A on this platform` | native 说明 | App-managed 说明 |

settings 写入：`_update_workbuddy_settings` 对所有带 `settings_file` 的产品生效（WorkBuddy、CodeBuddy）[代码] sync.py:218-219。**实测**两者 settings.json 均为 `{"skills": {name: bool}}` schema，当前行为正确，但实现按 WorkBuddy 硬编码命名，schema 一致属巧合而非设计（缺口 A3）。

---

## 三、缺口清单

### A 类：askill 侧可修（本轮修复候选）

| # | 缺口 | 证据 | 影响 | 修复方案 |
|---|------|------|------|---------|
| A1 | USAGE 帮助文本产品列表停在 6 个（"Supports: AutoClaw, Kimi, MiniMax Code, WorkBuddy, Trae, DuMate"） | cli.py:178 | 新用户低估支持面 | 动态生成或更新为 15 产品列表 |
| A2 | sync/status 对「平台无路径」输出 `n/a`，不说明原因 | sync.py:178-181 | Linux 用户困惑为何 8 个产品无输出语义 | 统一输出模板：`skip (no linux build)` / `ok native` / `skip (use 'pack')`，status 表同步 |
| A3 | settings 适配按 WorkBuddy 硬编码：函数名 `_update_workbuddy_settings`、removed 列表误标 `workbuddy-settings`，CodeBuddy 靠 schema 巧合工作 | sync.py:218-219, 572-610 | 新增带 settings 的产品时会复制错误模式；remove 报告误导 | 抽象为按产品声明的 `settings_adapter`（`skills` 开关字典作为一种可复用类型），命名与产品解耦 |
| A4 | 无按产品 frontmatter 校验：QwenWork 需要 `name`+`version`+`description`+`description_zh`，但 spec.py 只查 agentskills.io 通用规范，需求只存在于 note 字符串 | spec.py 全文; products.py:180 | QwenWork 用户装完技能加载失败才发现问题，且提示不指向原因 | 在 ProductSpec 增加声明式 `required_frontmatter`，install 后检查、sync/verify 时按产品警告，并提示修复命令 |
| A5 | 共享目录产品对重复同步：traecn+traesolo、qodercn+qodercnide 各建/删同一链接两次，输出重复两行 | products.py:102-111, 150-172 | 输出冗余；remove 报告重复项；未来 settings/extra 逻辑可能双写 | ProductSpec 增加 `shares_dir_with` 声明，sync/status/remove 按组去重，输出标注 `（与 traecn 共享目录）` |
| A6 | sync 无冲突检测：create_link 会 rmtree 产品目录中已存在的**真实目录**再建链接 | filesystem.py:57-64; 对比 adopt 有冲突检测 sync.py:792-804 | **数据丢失风险**：用户手动维护的同名技能被无警告覆盖 | create_link 前检测 dst 为真实目录且与 central 内容不同时：跳过 + 警告 + 建议 adopt/diff，除非 `--force` |
| A7 | adopt_from_platform 存在死代码：745-764 与 766-782 重复块（后者不可达） | sync.py:745-782 | 维护噪音 | 删除重复块 |
| A8 | pack 产品 status 恒为 `manual`，不反映 zip 状态 | sync.py:83-84 | DuMate 用户无法从 status 知道是否已打包/过期 | 检查 central 下 `{skill}.zip`：存在且新于 SKILL.md → `packed`，否则 `stale` |
| A9 | 为未安装产品创建空目录：extra_dirs 同步会 mkdir -p 全部额外目录（目前仅 Kimi），产品未安装也建目录 | sync.py:209-212 | 轻微：产生空目录噪音 | extra_dirs 建目录前检查产品配置根目录是否已存在（主路径由产品自身创建，保持现状） |

### B 类：产品硬限制（保持现状 + 文档/输出明示）

| # | 限制 | 涉及产品 | 处置 |
|---|------|---------|------|
| B1 | 官方未发布 Linux 版 | WorkBuddy、Trae、Trae CN、TRAE SOLO CN、Qoder CN、Qoder CN IDE、QwenWork、DoubaoWork | `linux_path` 保持 `None`；由 A2 的统一输出明示原因；`docs/product-paths.md` 已注明，产品发布 Linux 版后补 `linux_path` 即可 |
| B2 | 仅支持 App 内 zip 导入 | DuMate | pack 模式保持；由 A8 提升 status 可见性；watch 跳过时输出提示（A2 一并覆盖） |
| B3 | 原生扫描 central，无需同步 | MiniMax（另 AutoClaw2/ZCode/CodeBuddy 双扫，已由 central 覆盖） | native 模式保持，输出已明确 `ok native` |

### C 类：待真机确认（矩阵已标注，不阻塞本轮）

| # | 项 | 需要的环境 |
|---|----|-----------|
| C1 | macOS 路径全表（`~/.trae`、`~/.super_doubao/...` 等）与 Linux symlink 行为 | macOS / Linux 真机或虚拟机 |
| C2 | QwenWork frontmatter 精确校验口径（`version` 格式、`description_zh` 长度上限是否复用 1024） | QwenWork 客户端实测 + 官方文档更新核对 |
| C3 | WorkBuddy / CodeBuddy settings.json 是否存在 skills 之外的开关字段需求 | 两产品 Windows 实测（本机已有基础数据） |

---

## 四、修复路线图（阶段 1 输入）

按风险与收益排序：

1. **A6 冲突检测**（数据丢失风险，最高优先级）
2. **A4 按产品 frontmatter 校验**（用户可感知的失败 → 提前拦截）
3. **A2 统一输出模板** + **A1 USAGE 更新**（一致性体验主线）
4. **A3 settings 适配器**（为未来产品接入铺路）
5. **A5 共享目录去重**（输出正确性）
6. **A8 pack 状态、A9 目录噪音、A7 死代码**（收尾）

每项验收标准见阶段 2 的 `tests/test_matrix.py`（从 `products.py` 声明推导断言：无静默跳过、三平台行为可推导、共享目录单次同步）。
