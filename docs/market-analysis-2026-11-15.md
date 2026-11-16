# agent-skill-manager 功能与市场前景分析报告

- **日期**：2026-11-15　**基线**：v0.25.0（master `053e8ee`，工作区 clean）
- **方法**：本地源码走读 + GitHub REST/Search API 实拉 + 竞品 README 原文抓取 + PyPI / pypistats / skills.sh 采用度核验
- **声明**：本报告为只读分析，未改动任何源码。外部事实均带证据编号，`§9` 给出 URL 与可信度评级。**结论、情景与优先级属推断，已与事实分开标注。**
- **状态更新（2026-11-15 14:40）**：报告中的 P0 建议已执行（详见优化报告顶部状态块）。`§2` 的文档失真清单与 `§8` R6 是**执行前快照**，现已修正；保留原值作研究时间线
- **状态更新（2026-11-16 22:15）**：向上游提路径 PR 的结果已出——`vercel-labs/skills#2763` **被维护者 antfu 关闭**，回复明确推动 `.agents/skills` 统一 [A15]。这使 `§7` Bear 情景的核心触发条件从推断升级为**一手观测**；详见 `§7` 末段与 `§9` [A15]

---

## 0. 结论先行

**技术完成度显著高于市场牵引力，且旧的竞争结论已部分失效。**

1. 本项目是一个工程成熟度很高的单点工具：21 个命令、15 个产品声明、351 个测试函数、零运行时依赖、发版 25 次/53 天 [A1][A2][A3]。但可核验的采用度是 **2 stars / 1 fork / skills.sh 累计 2 次安装 / PyPI 非镜像累计 3,073 次下载、日均 36.5 次** [A1][A4][A5]。
2. 本地两轮竞品研究（11-04、11-13）的核心判断「15 个国产产品矩阵没有任何一家复刻」**已被证伪**：`npx skills` 的支持列表已含 9 行国产/中文产品条目；`dsh-skills-manager` 已列出 WorkBuddy / CodeBuddy / Trae CN / Qoder CN 的路径表 [A6][A7]。
3. 真正的差异化不在「产品数量」，而在 **「一处权威源 + Windows junction 免管理员 + 原生事件 watch 自愈 + 冲突保护/GC/回滚 + 安装即安全门禁」这一组可靠性机制的组合**；数量优势会随上游补路径被抹平，机制组合不会。
4. 最大的长期风险不是竞品功能，而是**标准收敛**：Agent Skills 已成开放规范、`~/.agents/skills/` 正在成为通用路径、`gh skill` 已把生命周期收进官方 CLI。askill 解决的是「标准未统一」的过渡摩擦，标准统一即需求收缩 [B1][B2][B3]。
5. 商业前景：**作为独立商业产品天花板低**（MIT、零依赖、离线、无网络效应、单点 CLI）；合理定位是「国产 Agent 工具链的一致性与安全基础设施」+ 开发者生态位资产，而不是按 SaaS 逻辑推演的赛道公司 [C1]。

---

## 1. 证据口径与可信度

| 级别 | 定义 | 本报告中的来源 |
|:---:|------|------|
| **A** | 一手、可机器复核 | GitHub REST API `api.github.com/repos/*`、`raw.githubusercontent.com` README、GitHub Search API、`pypi.org/pypi/*/json`、`pypistats.org/api/*`、`skills.sh` 页面、本地源码与 git |
| **B** | 官方站点静态说明 / 多源交叉但非直接机器复核 | agentskills.io 规范页、GitHub CLI `gh skill` 发布说明（经 docs 镜像 + 二手交叉） |
| **C** | 推断与判断 | 全部市场情景、竞争威胁定级、优先级、口径解释、战略建议 |

**抓取时间**：2026-11-15 14:10–14:25 GMT+8。stars / 下载量为瞬时快照，会漂移；所有数字都给了复现入口（`§9`）。
**口径纪律**：本仓库 `docs/competitive-research-round2-2026-11.md` 已立下「数字必带口径」规矩，本报告沿用——凡下载量注明 `without_mirrors`，凡仓库数注明搜索式，凡流量数字注明是否含发版日峰值。

---

## 2. 本项目功能基线（源码事实，非 README 转述）

| 维度 | 实测值 | 证据 |
|------|------|------|
| 版本 / 运行要求 | 0.25.0，`requires-python >=3.10`，MIT | `pyproject.toml`、[A2] |
| 命令面 | **21 个子命令**（`cli.py::_build_parser` 逐项计数） | `src/controllers/cli.py:507-756` |
| 产品矩阵 | 15 条声明（`PRODUCTS`），含 3 组共用目录别名 | `src/config/products.py:27+` |
| 中央源 | `~/.agents/skills/`；symlink / junction / 复制三级降级；冲突跳过 + `--force` | `products.py:19`、`utils/filesystem.py` |
| 可靠性 | watch 原生文件事件 + 30s 产品侧自愈、`doctor`、`sync --gc`、`rollback`、update 快照 | `services/watch.py`、`services/doctor.py`、`services/sync/` |
| 质量门禁 | 安装即 spec 检查 + 静态安全审计（提示注入/危险代码/凭据/二进制）+ 按产品 frontmatter 要求 | `services/audit.py`、`services/spec.py` |
| 生态 | skills.sh 简写 / GitHub URL / zip 归档 / `bundle` manifest / `publish` | `services/registry.py`、`get.py`、`manifest.py`、`publish.py` |
| 代码量 | `src/` 34 个 py / 6,517 行；`tests/` 25 个 py / 4,950 行 | 本地 `wc -l` |
| 测试 | **351 个 `def test_`**（静态计数），历史复检 362 passed（参数化展开后） | `tests/*.py`、`docs/architecture-health-check-2026-10-31.md` |
| 发版节奏 | 25 个 release，2026-09-21 → 11-13；11-13 一天发 3 个版本 | [A2] |

**事实一致性缺口（执行前快照）**：README badge 曾写 `Tests-309 passed`、Python `3.8+`、项目结构段写「17 commands」，`package.json` 停在 `0.11.0` [A3]。

> **2026-11-15 已修正**：在隔离 venv 实测 `362 passed`（35.02s），双语 README 徽章与结构段已改为 `3.10+ / 362 / 21 commands`，`package.json` 同步 0.25.0，`docs/promotion/` 三处旧测试数一并更新，`CONTRIBUTING.md` 新增发版数字口径 checklist。原值保留在此作为研究时间线记录。

---

## 3. GitHub 竞品全景（2026-11-15 实拉）

### 3.1 生态基座与分发层

| 项目 | stars | 创建 | 最后推送 | 形态 / 对本项目的意义 |
|------|-----:|------|---------|----------------------|
| `anthropics/skills` | 194,712 | 2025-09-22 | 11-14 | 规范起源仓库，品类需求真实性的最强证据 [A1] |
| `vercel-labs/skills` (`npx skills`) | 39,395 | 2026-01-14 | 11-12 | **事实标准级分发 CLI，且已覆盖国产产品**（见 §4.1）[A1][A6] |
| `VoltAgent/awesome-agent-skills` | 37,191 | 2025-10-28 | 11-05 | 1,000+ 技能目录，聚合层流量入口 [A1] |
| `davila7/claude-code-templates` | 33,672 | 2025-07-04 | 11-15 | 组件注册表 + CLI，518 open issues 说明高活跃 [A1] |
| `libukai/awesome-agent-skills` | 5,220 | 2025-12-21 | 10-25 | 中文「终极指南」，中文分发节点 [A1] |
| skills.sh（站点） | — | — | — | 榜单页显示 `All Time (1,409,025)`，**站点未标注单位**，据 Installs 列推断为累计安装量 [A8][C] |

### 3.2 通用管理器（功能直接对标）

| 项目 | stars | 最后推送 | 语言 | 关键机制 |
|------|-----:|---------|------|---------|
| `NanmiCoder/cc-haha` | 15,439 | 11-14 | TS | 中文桌面工作台，8,618 forks；中文社区运营样板 [A1] |
| `xingkongliang/skills-manager` | 7,513 | 11-14 | Rust | Tauri 桌面，50+ agents、**自定义工具路径覆盖**、Git 多机备份、agent 自管理技能 [A1][A9] |
| `tech-leads-club/agent-skills` | 7,167 | 11-12 | TS | 安全加固注册表、`-a` 定向安装 [A1] |
| `iflytek/skillhub` | 5,424 | 11-13 | Java | 讯飞企业自托管注册表（RBAC/审计/Docker）[A1] |
| `Tencent/teamai-cli` | 5,850 | 11-15 | — | **腾讯官方**：团队 skills/rules/MCP/agents 走 git 仓库，初始化后每次会话自动 pull [A1][A10] |
| `jeremylongshore/tons-of-skills-marketplace` | 2,924 | 11-15 | Python | 模型无关平台、content lockfile [A1] |
| `FrancyJGLisboa/agent-skills-platform` | 2,414 | 09-15 | Python | quarantine / rollback 生命周期 [A1] |
| `caliber-ai-org/ai-setup` | 1,315 | 09-24 | TS | 代码库定制、确定性一致性评分 [A1] |
| `binance/binance-skills-hub` | 1,183 | 11-12 | Python | 官方厂商技能市场 [A1] |
| `MoizIbnYousaf/ai-agent-skills` | 1,156 | 09-21 | JS | 12+ runtime，已停更 2 个月 [A1] |
| `jiweiyeah/Skills-Manager` | 1,062 | 09-10 | TS | 32 工具 symlink + 三级 Windows 链接策略，已停更 [A1] |
| `luongnv89/asm` | 974 | 11-14 | TS | **功能最完整的 CLI 对手**：residency / overlap / security / `get` / TUI / `--json --yes --machine` [A1][A11] |
| `enulus/OpenPackage` | 618 | 05-29 | TS | 全资源（rules/commands/agents/MCP），已停更 [A1] |
| `MichengAI/dsh-skills-manager` | 570 | 11-15 | — | **国产路径直接竞品**，见 §4.2 [A1][A7] |
| `knoxgraeme/skillfish` | 331 | 11-01 | TS | `bundle`/`install` 团队 manifest（本项目 v0.21 借鉴源）[A1][A12] |
| `reorx/skm` | 78 | 10-31 | — | 轻量 Python CLI [A1] |
| `hchcx/manage-my-skills` | 28 | 06-26 | TS | 中文跨平台，已停更 [A1] |

### 3.3 命名与同名干扰

| 事实 | 证据 |
|------|------|
| PyPI `agent-skill-manager`（`sm`）指向 `ackness/skill-manager`：**2 stars，最后推送 2026-02-07，Python ≥3.13，8 个 release 后停更** | [A1][A13] |
| PyPI **`askill` 名字已被占**：`akshayaggarwal99/agentskills` 0.2.0（2025-12-05），仅浏览安装 `anthropics/skills` | [A13] |
| 本项目 `yxdwind/skills`（官方技能仓库）0 stars | [A1] |

> 对本项目而言：同名 PyPI 包已实质停更，威胁可忽略；但 `askill` 命令名与 PyPI 上另一个 `askill` 包长期同名，是文档与搜索层面的持续混淆源。

---

## 4. 三个改写旧结论的发现

### 4.1 `npx skills` 已进入国产产品（最重要）

`vercel-labs/skills` 的 `docs/agents.md` 共 71 行表格，实拉到以下国产/中文条目 [A6]：

| agent 标识 | Global Path | 与本项目 `products.py` 的关系 |
|-----------|-------------|------------------------------|
| `codebuddy` | `~/.codebuddy/skills/` | ✅ 一致 |
| `trae` / `trae-cn` | `~/.trae/skills/` / `~/.trae-cn/skills/` | ✅ 一致 |
| `qoder` / `qoder-cn` | `~/.qoder/skills/` / `~/.qoder-cn/skills/` | 🟡 本项目只声明 `qoder-cn` 系 |
| `zcode` | `~/.zcode/skills/` | ✅ 一致 |
| `minimax-code` | `~/.minimax/skills/` | 🔴 与本项目 `~/.agents/skills/`（native）不同 |
| `qwen-code` | `~/.qwen/skills/` | 🔴 与 QwenWork `~/.qwenworkcn/skills/` 是不同产品 |
| `kimi-code-cli`（与其他 9 个 agent 同一行） | `.agents/skills/` 系 | 🟡 本项目 Kimi 主路径 `~/.config/agents/skills/`，`~/.kimi-code/skills/` 仅为 `extra_dirs` |

**本项目仍独有**：AutoClaw2、WorkBuddy、DuMate、Comate、QwenWork、DoubaoWork，以及 TRAE SOLO CN / Qoder CN IDE 这两个共用目录别名。即 **15 条声明里约 6 条深水路径是真正的空白**，其余已进入或接近上游覆盖范围。

同时，`xingkongliang/skills-manager` 支持「自定义工具路径覆盖」[A9]——用户可自行录入国产路径，进一步削弱「我们列了 15 个」的稀缺性。

**结论 [C]**：护城河不是「路径清单」，而是「路径清单 × 本地可靠性机制 × 安全门禁」的组合；清单本身应在 12 个月内主动上游化（见优化报告 P1-5），否则会从资产变成维护负担。

### 4.2 国产路径已有直接竞品

`MichengAI/dsh-skills-manager`（570 stars，2026-08-15 建库，11-15 仍在推送，Apache-2.0）README 明确列出 20+ 工具的路径表，含 Trae / Trae CN / **CodeBuddy** / **WorkBuddy** / Qoder / Qoder CN CLI / Qoder CN IDE，并有项目级路径与回收站防误删 [A7]。

值得注意的一处**技术分歧**：它把 Qoder CN IDE 标为 `~/.lingma/skills`，而本项目把 Qoder CN IDE 当作与 Qoder CN 共用 `~/.qoder-cn/skills/` [A7][A3]。两者至少有一方需要按真机复核——这属于产品路径漂移风险，已列入优化报告 P1-6。

它的形态是 DSH 宿主插件 + 侧栏 GUI（「不侵入第三方文件」的多来源聚合视图），不做 junction 同步，因此**不是同步模型的替代品，但争夺同一批国产多产品用户的心智**。

### 4.3 团队同步被官方方案降维

本项目 v0.21 的 `bundle` / `install --manifest` 借鉴自 skillfish（331 stars）。但 `Tencent/teamai-cli`（5,850 stars，腾讯官方）把 skills/rules/agents/MCP/workflows 统一放进 git 仓库，**初始化一次后每次 AI 会话自动 pull，通过 `/teamai` 对话分享** [A10]；skillfish 的 manifest 语义也更细——只追踪外部来源技能，本地创作技能直接走项目版本控制 [A12]。

**结论 [C]**：`bundle` 是「有功能」，不是「有壁垒」。团队场景应放弃正面竞争，把叙事锚定在**离线、零服务端、本机多产品一致性**上。

---

## 5. 功能对比矩阵

`●` 具备且成体系　`◐` 部分具备　`—` 不具备　（基于 README 原文与本项目源码，非实测运行）

| 能力 | **askill** | npx skills | asm | skills-manager | skillfish | DSH | teamai-cli |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 中央权威源 + 一处改动全端生效 | ● | — | ◐ | ◐ | ◐ | — | ◐ (git 仓库) |
| 国产产品深水路径 | ● (15 条) | ◐ (9 行) | — | ◐ (自定义) | — | ◐ (20+) | — |
| Windows junction 免管理员 + 降级 | ● | — | — | ◐ | — | — | — |
| 原生事件 watch + 产品侧链接自愈 | ● | — | — | — | — | — | ◐ (会话 pull) |
| 冲突保护 / 死链回收 / 更新回滚 | ● | — | ◐ | ◐ | — | ◐ (回收站) | ◐ |
| 安装即静态安全审计 + frontmatter 门禁 | ● | ◐ | ● | ◐ | — | ◐ | — |
| 注意力预算 / 语义去重叠 | ◐ (仅 residency) | — | ● | — | — | — | — |
| 先看后装引用层 | ● (`get`) | — | ● | — | — | — | — |
| 团队清单 | ◐ (`bundle`) | ◐ (repo scope) | — | ◐ (Git 备份) | ● | — | ● |
| Agent 自管理技能 | ◐ (`askill-ops`) | ● | ◐ | ● | — | — | ● |
| 桌面 GUI | — | — | ◐ (TUI) | ● | — | ● | — |
| 零第三方依赖 / 离线优先 | ● | — | — | — | — | — | — |
| 服务端 / 企业治理 | — | — | — | — | — | — | ● (git) |

**读法**：askill 在「本机文件系统可靠性」这一列群几乎全绿且无人复刻；在「生态规模、社区、团队协同、GUI」四列几乎全空。这不是功能差距，是**产品形态选择 + 冷启动差距**。

---

## 6. 采用度与市场信号（可核验，不推测 TAM）

| 指标 | 数值 | 口径 / 说明 |
|------|------|-------------|
| GitHub stars / forks / issues | **2 / 1 / 0** | 2026-11-15 快照，建库 2026-08-10 [A1] |
| PyPI 非镜像累计下载 | **3,073** | `without_mirrors`，2026-09-21 → 11-14 [A5] |
| 近 30 天 / 日均 | **1,023 / 36.5** | `without_mirrors`，含 CI 与自发验证流量 [A5] |
| 月度分布 | 9月 465 · 10月 1,814 · 11月(至14日) 794 | 同上 [A5] |
| 单日峰值 | **245（11-13）** | 恰为 0.23/0.24/0.25 三版本发布日 → **峰值由发版与自测驱动，非自然增长** [A5][C] |
| skills.sh 收录 | **1 个技能 / 2 次总安装** | `skills.sh/yxdwind/agent-skill-manager` [A4] |
| 官方技能仓库 | `yxdwind/skills` 0 stars | [A1] |
| 对照：同名包 `agent-skill-manager` | 近 30 天 282 / 日均 9.4 | 已停更 9 个月，仍有长尾下载 [A5][A13] |

**品类热度代理指标**（GitHub Search API，口径 = 仓库 name/description 含关键词，按 `created` 分桶；**含噪声**：会命中技能内容仓库与 `Product-Manager-Skills` 之类无关项，仅作趋势代理）[A14][C]：

| 关键词 | 2025H2 | 2026H1 | 2026Q3 | 2026Q4 (10/1–11/15，1.5 个月) |
|--------|-------:|-------:|-------:|------------------------------:|
| `skills manager` | 401 | 2,100 | 1,278 | 699 |
| `agent skills` | 7,210 | 63,688 | 49,778 | （API 限流未取） |

**规范与平台侧信号**：
- Agent Skills 是 Anthropic 发起的开放标准，核心是 `SKILL.md` + 三级渐进披露（Discovery 只加载 name/description → Activation 读全文 → Execution 执行）；官方 client showcase 已含 **TRAE**、VS Code、GitHub Copilot、Cursor、Gemini CLI、Spring AI 等 [B1]。规范普及既做大品类，也让「description 常驻上下文」成为真实的成本问题（asm residency 与本项目 `audit --residency` 的共同前提）。
- GitHub CLI **v2.90.0（2026-04-16，public preview）新增 `gh skill`**：search / install / update / publish / `--pin` / `--scope` / `--agent`，`--agent` 目标为 Claude Code、Cursor、Codex、Gemini、Antigravity，**不含国产产品** [B3]。平台方已吸收通用生命周期管理，但留出了国产缝隙。
- skills.sh 榜单头部单个技能安装量已达百万量级（`find-skills` 4.4M）[A8]，说明**分发层的网络效应极强**，而本项目在分发层只有 2 次安装。

> **明确不给 TAM / 渗透率 / 收入预测**：本次未取得任何可核验的付费市场或用户规模一手数据；用「下载量 × 假设转化率」推演会产出伪精确数字。以下改用可观测先行指标 + 条件情景判断 [C]。

---

## 7. 市场前景：三情景（判断，非事实）

| | **Bear** | **Base** | **Bull** |
|---|---|---|---|
| 触发条件 | `~/.agents/skills/` 成为国产产品原生统一路径；npx skills / gh skill 补齐国产条目；Windows 产品转向原生扫描 | 国产桌面/办公产品继续各自为政 12–18 个月，路径碎片化维持；上游只补主流产品 | askill 成为国产路径的**上游数据源**（被 npx skills / DSH / awesome 列表引用），安全门禁进团队 CI |
| 结果 | 「同步」退化为 Windows junction 补丁与历史兼容层，下载量停滞在长尾 | 在 Windows 多产品重度用户中形成小众但稳定的口碑工具，缓慢增长 | 从工具升级为「国产 Agent 工具链一致性基础设施」，生态位与话语权显著高于 stars 数 |
| 可观测先行指标 | npx skills `docs/agents.md` 国产条目数持续上升；MiniMax 式 native 产品在 15 条中占比上升 | 非发版日下载基线（当前峰值高度依赖发版）；stars 与 skills.sh installs 的月增量 | 上游 PR 合并数；`askill products --json` 被第三方引用；CI 门禁被外部仓库采用 |
| 防线 | 把价值迁移到审计/门禁/漂移治理，与路径解耦 | 守住可靠性组合 + 中文场景，别去比功能数量 | 主动上游化 + 把声明式路径表变成机器可读公共品 |

**共同判断 [C]**：
1. **需求真实**（规范被主流客户端接受、品类仓库数仍在增长、官方 CLI 下场），但**需求是过渡性的**：同步工具的价值来自路径碎片化，碎片化收敛即价值衰减。这是本项目所有战略判断的第一性原理起点。
2. **窗口期由上游决定，不由自己决定**：`npx skills` 39k stars 与 `gh skill` 官方分发，一次路径表更新就能覆盖本项目大半声明。抢窗口的方式不是加功能，而是**成为那张路径表的来源**。
3. **商业上限受限**：MIT + 零依赖 + 离线 + 单点 CLI，无账号、无服务端、无数据沉淀、无网络效应；作为独立商业化产品天花板低。更现实的价值形态是开发者声誉、生态位，或作为企业侧支持/合规门禁服务的入口。不建议按 SaaS 或平台型估值框架推演。
4. **当前最大短板不是功能，是分发**：25 个 release / 54 天的高迭代速度，对应的是 2 stars 与 2 次 skills.sh 安装。工程投入的边际收益已明显低于分发投入的边际收益。

### 7.1 已观测信号（2026-11-16）：Bear 的核心触发条件被一手证据命中

本项目向 `vercel-labs/skills` 提交了 5 个国产 agent 的全局路径（`src/agents.ts`，非文档），
即 [PR #2763](https://github.com/vercel-labs/skills/pull/2763)。维护者 **antfu 于 2026-11-16 关闭了该 PR**，
理由原文要点 [A15]：

> 推荐 coding agents 从共享 `.agents/skills` 文件夹读取；这样它们开箱即用地兼容 `npx skills`，本仓库无需改动。
> 若你不维护该 agent，请让它的维护者支持 `.agents/skills`。想按名字列出的话，等它支持 `.agents/skills` 后
> 再开一个小 PR，把项目目录写成 `.agents/skills`，我们就很乐意收录。

**判定变化**：Bear 列的「`~/.agents/skills/` 成为国产产品原生统一路径」此前是推断 [C]，
现在有了**上游维护者主动推动该标准、且拒绝维护产品特定路径**的一手证据 [A15]。
这是 `R1` / `R2` 风险从「高」走向「已发生」的信号，而不是新的独立风险。

**但不能过度外推**：上游拒绝的是「在本仓库维护产品特定路径」，并不等于国产桌面/办公产品
已经统一支持 `.agents/skills`。真实用户侧的路径碎片化、Windows junction 免管理员、settings 开关、
产品侧链接丢失后的自愈，短期内仍然存在——**消失的是「路径清单」这一层护城河，不是「可靠性机制」这一层**。

**路线调整**：
1. 不再把「向上游 PR 加路径」当作主要上游化方式；改按上游建议，推动国产产品支持 `.agents/skills`。
2. 对外叙事重心从「支持 15 个产品」移到「权威源 + 分发 + 自愈 + 诊断修复 + 回滚」的机制组合（见 `docs/reliability-model.md`）。
3. `askill products --json --paths` 仍保留——它现在更适合作为**用户自查与漂移监测**的输入，而非上游 PR 素材。

---

## 8. 风险清单

| # | 风险 | 证据 | 级别 |
|---|------|------|:---:|
| R1 | 标准收敛 / 产品原生化，核心痛点消失 | MiniMax Code 已是 `sync_method: native`；agentskills.io 普及 [A3][B1] | 高 |
| R2 | 39k stars 上游补齐国产路径，清单优势归零 | `docs/agents.md` 已含 9 行 [A6] | 高 |
| R3 | 路径声明漂移，静默同步到错误目录 | Qoder CN IDE `~/.lingma` vs `~/.qoder-cn` 分歧 [A7][A3] | 中高 |
| R4 | 冷启动失败：无社区、无贡献者、单人维护 | 2 stars / 1 fork / 0 issues [A1] | 中高 |
| R5 | 打包回归（0.20.0 事故根因仍在）：`pyproject` 手工 `packages` 白名单 | `pyproject.toml:50-60`、体检报告复检记录 | 中 |
| R6 | 文档口径失真，损害技术受众信任 | 3.8+/309/17 commands/0.11.0 四处 [A3] | 中 |
| R7 | PyPI `askill` 名被占，搜索与安装路径混淆 | [A13] | 低 |
| R8 | Windows `settings.json` 占用、watch 容器降级、audit 误报 | README「已知限制」 | 低中 |

---

## 9. 证据索引（URL · 可信度）

| # | 来源 | URL | 级别 |
|---|------|-----|:---:|
| A1 | GitHub REST API，22+5 个仓库元数据 | `https://api.github.com/repos/{owner}/{repo}`（如 `/repos/yxdwind/agent-skill-manager`），2026-11-15 | A |
| A2 | PyPI 发布元数据 | `https://pypi.org/pypi/cn-skill-sync/json` | A |
| A3 | 本地源码与配置 | `src/config/products.py`、`src/controllers/cli.py`、`pyproject.toml`、`README.md`、`package.json` | A |
| A4 | skills.sh 项目收录页 | `https://skills.sh/yxdwind/agent-skill-manager` | A |
| A5 | pypistats 下载量 | `https://pypistats.org/api/packages/cn-skill-sync/overall`、`.../recent` | A |
| A6 | npx skills 支持列表 | `https://raw.githubusercontent.com/vercel-labs/skills/main/docs/agents.md` | A |
| A7 | DSH Skills Manager README | `https://raw.githubusercontent.com/MichengAI/dsh-skills-manager/master/README.md` | A |
| A8 | skills.sh 榜单首页 | `https://skills.sh/` | A（单位解释属 C） |
| A9 | xingkongliang README | `https://raw.githubusercontent.com/xingkongliang/skills-manager/main/README.md` | A |
| A10 | Tencent/teamai-cli README | `https://raw.githubusercontent.com/Tencent/teamai-cli/main/README.md` | A |
| A11 | luongnv89/asm README | `https://raw.githubusercontent.com/luongnv89/asm/main/README.md` | A |
| A12 | knoxgraeme/skillfish README | `https://raw.githubusercontent.com/knoxgraeme/skillfish/main/README.md` | A |
| A13 | 同名包元数据 | `https://pypi.org/pypi/agent-skill-manager/json`、`https://pypi.org/pypi/askill/json`、`https://api.github.com/repos/ackness/skill-manager` | A |
| A14 | GitHub Search API 分桶统计 | `https://api.github.com/search/repositories?q=...created:...` | A（噪声解释属 C） |
| A15 | 上游维护者对路径 PR 的处置 | `https://github.com/vercel-labs/skills/pull/2763`（antfu 2026-11-16 评论） | A |
| B1 | Agent Skills 规范概览 | `https://agentskills.io/` | B |
| B2 | 规范仓库 popularity 侧证 | `https://github.com/anthropics/skills` + [A1] | A/B |
| B3 | `gh skill` 发布说明（2026-04-16, gh v2.90.0 public preview） | GitHub Docs changelog 镜像 `https://github.com/MIATC-AF/docs/blob/main/CHANGELOG.md`；交叉 `https://releases.sh/github/github-cli`、`https://agentpatterns.ai/tools/copilot/gh-skill-cli-management/` | B |
| 本仓库 | 前两轮竞品研究 / 架构体检 | `docs/competitive-research-2026-11.md`、`docs/competitive-research-round2-2026-11.md`、`docs/architecture-health-check-2026-10-31.md` | A（历史基线） |

**局限性说明 [C]**：① stars / 下载量为瞬时快照，且 pypistats `without_mirrors` 仍含 CI 与自动化流量，不能等同于活跃用户；② GitHub 搜索式分桶含大量噪声仓库，只作趋势代理；③ 竞品能力矩阵依据 README 声明，未逐项运行验证；④ 本次环境未安装 `pytest` / `ruff`，测试数采用静态 `def test_` 计数（351）与历史复检（362 passed）交叉，未现场复跑；⑤ `gh skill` 未直接抓到官方 changelog 原页，采用多源交叉，故列 B。

---

*配套行动方案见 `docs/optimization-report-2026-11-15.md`。*
