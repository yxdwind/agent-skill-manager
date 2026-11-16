# agent-skill-manager 优化报告（v0.25.0 基线）

- **日期**：2026-11-15　**配套分析**：`docs/market-analysis-2026-11-15.md`（证据编号 A*/B*/C 沿用该文件 `§9`）
- **性质**：可执行方案，本报告本身未改动任何源码；所有「动作」为待执行项
- **硬约束**：① 零第三方运行时依赖不变 ② 不做服务端 / 账号体系 ③ 保持离线优先与 `PRIVACY.md` 口径 ④ 保持「声明式 `products.py` 为唯一产品事实源」的架构纪律 ⑤ 不引入内置遥测
- **执行状态（2026-11-16 22:15）**：**分析报告 P0 / P1 / P2 全部项目已完成、全部代码已提交并推送**（`9db5ba0` / `d936b7a`，远程 CI 8/8 绿）。上游 PR [#2763](https://github.com/vercel-labs/skills/pull/2763) **已被维护者关闭**（推荐 `.agents/skills` 统一路径），路径上游化路线需调整；信号已写回 `market-analysis` §7 与 `metrics.md`。**未发 v0.26**（PyPI 仍 0.25.0）。
  - P0：全仓口径与竞品结论纠偏、命名对照表、收录对象调整（文档/元数据）。
  - P1-5：`askill products --json --paths`、`scripts/export_agents_md.py`、`src/services/paths_export.py`、8 个回归测试、上游覆盖复核。
  - P1-6：`scripts/check_upstream_paths.py`（只读漂移监测，真实上游数据检出 4 条路径分歧）、5 个测试、周度 CI workflow。
  - P1-7：`askill doctor --fix`（默认 dry-run 的修复计划）/ `--fix --apply`（只执行 `sync` 与 `sync --gc`）、`src/services/remediation.py` 纯函数、7 个测试、`docs/reliability-model.md` 五环节一致性链。
  - 上游 PR **已发出**：[vercel-labs/skills#2763](https://github.com/vercel-labs/skills/pull/2763)（OPEN）。实际改 `src/agents.ts` + `src/types.ts`，因为 `docs/agents.md` 是生成物；详见 `docs/upstream/2026-11-15-pr-draft.md` 文首的差异说明。
  - P1-8：`verify --format github` / `audit --format github --fail-on D,F` 输出 CI annotation 并按评分设退出码；示例 `docs/examples/skill-gate.yml`。
  - P1-9：`audit --overlap` 确定性词面重合排序（英文词 + 中文二元组 Jaccard，零依赖、不宣称语义理解）。
  - P1-10：`bundle --external-only` + manifest `origin` 字段；`install --manifest` 对本地创作技能明确警告跳过、绝不触网；兼容无 `origin` 的旧清单。
  - P2-11：**自动发现不可直接替换**——`find_packages(where="src")` 会生成 `config` / `services` 等缺前缀的错误包名（实测）。改用 `tests/test_packaging.py` 把 `pyproject` 白名单锁到磁盘实际子包集合，新增子包未声明即红灯，同样根治 0.20.0 事故且零打包风险。
  - P2-13：`tests/test_windows_junction.py` 用真实 `mklink /J` 验证活链 / 死链 / 真实目录三类行为，由现有 `windows-latest` job 自动收集。
  - P2-14：`docs/metrics.md` 月度可观测基线（全部公开接口可复现，明确不做遥测）。
  - P2-12：`controllers/parsers/` 子包（distribution / authoring / operations 三族），21 个命令按**原注册顺序**组装，`_build_parser()` 保留为唯一入口；新增子包同步进 `pyproject` 白名单——P2-11 的锁先实战变红、补全后转绿。
  - 门禁基线：**402 passed**（隔离 uv venv / Python 3.12）；ruff / mypy 41 文件全绿。
  - **wheel 实装冒烟**：干净 venv 装 `cn_skill_sync-0.25.0` wheel → `askill version` / `products --paths`（15 条）/ 解析 21 命令全通过。
  - **收尾待决策**：**本项目工作区改动全部未提交**，行尾策略（`core.autocrlf=true` 与 README 的 CRLF blob 冲突）未定。以下各节保留原始方案文本以便追溯。

---

## 0. 优化主线

分析报告的结论可压缩成一句：**功能不是短板，分发与事实一致性是短板；护城河必须从「我列了 15 个路径」迁移到「我是这 15 个路径的权威来源 + 本机一致性的守护者」。**

因此本轮优化排序不再是「加功能」，而是：

```
P0  把对外陈述修成真的           （成本最低、可信度收益最高）
P1  把路径清单上游化 + 治理漂移   （把易被复制的资产换成不易被复制的生态位）
P2  清掉会阻碍上面两件事的工程债 （打包、CLI 膨胀、Windows 真机、度量）
```

---

## 1. 优先级总表

| # | 优化项 | 成本 | 收益 | 依赖 | 验收信号 |
|---|--------|:---:|------|------|---------|
| P0-1 | 全仓数字/版本口径对齐 | S | 消除 6+ 处事实失真 | 无 | `grep` 无 `309`/`17 commands`/`3.8+` 残留于现行文档 |
| P0-2 | 竞品结论纠偏（旧结论已证伪） | S | 避免对外被一句话反驳 | 分析报告 | 3 份文档 + 2 份营销稿带修订注 |
| P0-3 | 命名冲突文档化 | S | 降低安装/搜索混淆 | 无 | 三处入口有一致的「包名 ≠ 命令名 ≠ 仓库名」表 |
| P0-4 | skills.sh 收录对象换挡 | S | 分发入口有效化 | 维护者确认 | 主推技能页安装数开始有非零增量 |
| P1-5 | **`askill products --json --paths` + 上游路径 PR** | M | **战略级**：把清单变公共品 | P0-2 | ≥1 个上游 PR 合并或有实质回应 |
| P1-6 | 上游路径漂移监测 | M | 提前发现沉默失效 | P1-5 | CI 周任务能输出差异报告 |
| P1-7 | `doctor --fix`（dry-run 默认）+ 可靠性文档 | M | 把机制组合变成产品叙事 | 无 | 一条命令可诊断并给出修复计划 |
| P1-8 | CI 门禁输出（GitHub Actions annotation） | S-M | 进团队工作流 | 退出码契约 | 示例 workflow + 退出码测试 |
| P1-9 | `audit --overlap` 确定性去重叠 | S-M | 补齐注意力预算维度 | `audit --residency` | 对同一技能集输出稳定排序 |
| P1-10 | `bundle --external-only` | S | manifest 语义对齐 skillfish | `manifest.py` | 本地创作技能不被当远程依赖重装 |
| P2-11 | setuptools 包自动发现 + wheel 内容断言 | S | **根治 0.20.0 类事故** | 无 | 新增空子包的测试能红灯 |
| P2-12 | `cli.py` 按命令族拆 parser | M | 21 命令后继续可维护 | P2-11 | `_HANDLERS` 接缝与测试 patch 目标不变 |
| P2-13 | Windows 真机 junction/GC/settings 回归 | M | 覆盖 3 条已知限制 | CI | windows-latest job 跑真实 junction |
| P2-14 | `docs/metrics.md` 月度可观测基线 | S | 让情景判断有先行指标 | 无 | 每月一行、全部可复现 |

---

## 2. P0 — 事实一致性（建议在任何下一次发文/发版前完成）

### P0-1 数字与版本口径全仓对齐

**问题**：现行对外材料有 6 类失真，且技术受众最容易从这些地方判断项目是否可靠 [A2][A3]。

| 位置 | 现状 | 应改为 | 权威来源 |
|------|------|--------|---------|
| `README.md:13` / `README.en.md:15` | Python badge `3.8+` | `3.10+` | `pyproject.toml:11 requires-python >=3.10`（源码用 `X \| Y` / `list[...]`，3.8 实际跑不了） |
| `README.md:16` / `README.en.md:13` | `Tests-309 passed` | 实测值 | `pytest -q`；静态计数 351 个 `def test_`，历史复检 362 passed（参数化展开） |
| `README.md:265` / `README.en.md:273` | `17 commands` | `21 commands` | `src/controllers/cli.py:507-756` 的 `add_parser` 计数 |
| `README.md:272` / `README.en.md:280` | `309 个测试 / 309 tests` | 同上实测值 | 同上 |
| `package.json:3` | `0.11.0` | `0.25.0`，或注明「仅 npx 元数据、不跟版本」 | `pyproject.toml:7` / `src/__init__.py:11` |
| `docs/promotion/zai-community-post.md:32`、`oschina-article.md:45`、`zhihu-answers.md:52` | `309 个测试` | 同上（未发布稿也应改，避免发出去即失真） | 同上 |

**动作**：一次性全仓替换；在 `CONTRIBUTING.md` 加一条发版 checklist：**改版本时同步 `pyproject` 两处 version + `src/__init__.py` + `package.json` + 双语 README 徽章**（架构体检记录过 `cz bump` 静默不执行与手动 bump 的坑）。
**验收**：`grep -rn "309\|17 commands\|3\.8+" README* docs/promotion marketing` 在现行文档中无残留（历史报告保留原值并标注日期，属可追溯记录，不删）。

### P0-2 竞品结论纠偏（旧结论已被证伪）

**问题**：`docs/competitive-research-2026-11.md:22-23,78-82` 写「15 国产产品矩阵…没有任何一家复刻」「无人有」；`marketing/06-competitive-teardown-juejin.md:53` 与 `marketing/07-competitive-shard-jike.md:7` 把这句写成核心营销论点。但 `npx skills` 的 `docs/agents.md` 已有 9 行国产/中文条目、`dsh-skills-manager` 已列 WorkBuddy/CodeBuddy/Trae CN/Qoder CN 路径 [A6][A7]。

**动作**：不删历史（保留研究时间线），在每处加「2026-11-15 修订」块：
- 把「无人覆盖国产目录矩阵」改为 **「无人复刻『中央权威源 + junction/watch 自愈/冲突保护/GC/回滚 + 安装门禁』的机制组合；国产路径清单已被上游部分覆盖」**；
- 引用 `docs/market-analysis-2026-11-15.md §4` 给出可核验证据与 URL；
- 营销稿若已发布，追加一条更正短贴而不是静默改稿（技术受众对静默改稿更敏感）。

**验收**：对外任何一句「无人有」都能被替换为可核验的机制陈述；`marketing/README.md` 索引标注旧稿的时效性。

### P0-3 命名冲突文档化

**问题**：三层命名不一致，且 PyPI 上的 `askill` 是**另一个真实存在的包**（`akshayaggarwal99/agentskills` 0.2.0，仅浏览安装 `anthropics/skills`）[A13]。README:9-11 只警告「不要 `pip install askill`」，未解释命令名与包名的关系。

**动作**：在 `README.md`（中英双语）、`SKILL.md`、`docs/product-paths.md` 加同一张对照表：

| 概念 | 值 | 说明 |
|------|-----|------|
| 仓库 | `yxdwind/agent-skill-manager` | GitHub |
| PyPI 包 | `cn-skill-sync` | `pip install cn-skill-sync` |
| Python 包 | `agent_skill_manager`（映射到 `src/`） | `import` 用 |
| CLI 命令 | `askill` | **与 PyPI 上另一个 `askill` 包同名但无关** |
| 同名 PyPI 包 | `agent-skill-manager`（`ackness/skill-manager`，`sm`） | 2 stars，2026-02 起停更，Python ≥3.13 [A1][A13] |

**验收**：三处入口表述一致；`pip install askill` 的误导在任何入口都有明确一句话说明。

### P0-4 skills.sh 收录对象换挡

**问题**：`skills.sh/yxdwind/agent-skill-manager` 显示 **1 skill / 2 total installs**，收录的是仓库根的元技能 `SKILL.md`（教 agent「有这个工具」），不是用户真正会装的能力 [A4]。`npx skills add yxdwind/agent-skill-manager` 因此几乎没有转化。

**动作**（需维护者确认后再执行外部提交）：主推 `yxdwind/skills` 下的 `askill-ops` / `skill-doctor` / `sync-troubleshoot` 作为收录与 `npx skills add` 对象；仓库根 `SKILL.md` 保留但定位改为「工具自述」。README 的安装示例把 `npx skills add ...` 换成具体技能路径。
**验收**：至少 1 个能力型技能在 skills.sh 有独立页面；月度安装数不再为个位数。

---

## 3. P1 — 把护城河迁移到上游与可靠性

### P1-5 ★ 路径清单上游化（本轮最高战略价值）

**依据**：`npx skills`（39,395 stars）的 `docs/agents.md` 已覆盖 CodeBuddy / Trae / Trae CN / ZCode / Qoder / Qoder CN / MiniMax Code / Qwen Code / Kimi Code CLI，**唯独缺** AutoClaw2、WorkBuddy、DuMate、Comate、QwenWork、DoubaoWork、TRAE SOLO CN、Qoder CN IDE 等深水路径 [A6]。上游每补一行，本项目的「数量优势」就少一行；**但上游若引用本项目作为数据来源，每一行都是分发与话语权** [C]。

**动作**：
1. 在 `src/controllers/cli.py` 的 `products` 命令加 `--paths`（配合已有 `--json`）输出机器可读结构：`{short, name, macos_path, windows_path, linux_path, sync_method, settings_file, required_frontmatter, shared_with}`；**不新增第二份事实源**，只从 `PRODUCTS` 派生。
2. 加 `scripts/export_agents_md.py`：把声明导出成 `docs/agents.md` 的表格片段，供上游 PR 直接粘贴（零依赖、标准库）。
3. 向 `vercel-labs/skills` 提 PR 补齐上述深水路径；同步向 `MichengAI/dsh-skills-manager`、`libukai/awesome-agent-skills`、`VoltAgent/awesome-agent-skills` 提收录/路径修正。**外部提交属对外动作，须维护者逐项确认后执行，本报告不代为提交。**
4. `docs/product-matrix.md` 增加「上游收录状态」列，标注每个产品在 npx skills / DSH 中的覆盖情况。

**验收**：`askill products --json --paths` 通过 `tests/test_products.py` 断言；≥1 个上游 PR 被合并或获实质回应；`docs/product-matrix.md` 有可复现的上游核对日期。

### P1-6 路径漂移监测（含 4 个已核实的分歧点）

**依据**：路径一旦漂移，sync 会「成功」地链到错误目录，是最危险的静默失败 [A3][A7]。实拉比对发现的候选分歧：

| 产品 | 本项目 `products.py` | 上游/竞品 | 处置 |
|------|---------------------|-----------|------|
| Qoder CN IDE | 与 Qoder CN 共用 `~/.qoder-cn/skills/` | DSH：`~/.lingma/skills` [A7] | **优先真机复核**，可能需拆成独立声明 |
| MiniMax Code | `~/.agents/skills/`（`native`，无需同步） | npx skills：`~/.minimax/skills/` [A6] | 判定是否同一产品的不同版本/安装形态，补 `note` |
| Qwen Code | 无（本项目是 QwenWork `~/.qwenworkcn/skills/`） | npx skills：`~/.qwen/skills/` [A6] | 明确是不同产品，还是应作为新产品新增 |
| Kimi Code CLI | `~/.kimi-code/skills/` 仅作 `extra_dirs` | npx skills：与 Cline/Codex 同列 `.agents/skills/` [A6] | 核对主路径 `~/.config/agents/skills/` 是否仍有效 |

**动作**：新增 `scripts/check_upstream_paths.py`（标准库 urllib），定期抓 `vercel-labs/skills/docs/agents.md` 与 DSH README，与 `PRODUCTS` 做集合/路径 diff，输出 Markdown 报告；接 GitHub Actions 每周一次，**只读、不自动改声明**（沿用 `scripts/` 已有脚本风格）。
**验收**：能对当前 4 个分歧点稳定产出 diff；网络失败时退出码 0 并标注 `unknown`，不误报为「无漂移」。

### P1-7 把机制组合产品化：`doctor --fix`

**依据**：功能矩阵显示 askill 在「本机文件系统可靠性」列群几乎全绿且无人复刻，但用户要跑 4 条命令（doctor / sync --gc / sync / rollback）才能走完一次治理 [A3][C]；对手 `teamai-cli` 是「初始化一次、会话自动 pull」[A10]。

**动作**：`services/doctor.py` 增加 `--fix`：默认 **dry-run 打印修复计划**（重连中央同名死链 / `--gc` 残留 / 重新启用 settings 开关 / 列出可回滚快照），需显式 `--apply` 才执行；复用现有 `sync --gc`、`rollback`、`settings_io`，不新增写路径。补一份 `docs/reliability-model.md`，把「冲突保护 / 自愈 / GC / 快照回滚 / settings 锁」画成一条一致性保障链，作为对外叙事主素材。
**验收**：`doctor --fix` 在干净仓库输出 no-op；在含死链夹具的临时目录输出可执行的 4 类计划；`--apply` 有对应测试与退出码契约（0/1/2）。

### P1-8 CI 可集成门禁

**依据**：`gh skill publish` 已把 spec 校验做成官方 CLI 能力 [B3]；本项目的 `verify` / `audit` 虽有评分与退出码契约，但输出是给人看的表格 [A3]。

**动作**：`askill verify --format github` 与 `askill audit --fail-on D,F` 输出 GitHub Actions `::error file=...` annotation；在 `.github/workflows/` 加示例 workflow（可由外部仓库复制）。**不改默认人类可读输出**。
**验收**：一个含坏 frontmatter 的 fixture 在 CI 里产生 annotation 且退出码 1；`tests/test_cli_flags.py` 覆盖新 flag。

### P1-9 注意力预算补齐 `--overlap`

**依据**：`asm` 同时有 `audit residency`、`audit overlap`、`stats --tokens`、`get`、`--json/--yes/--machine` 与 TUI [A11]；本项目 v0.21 只借鉴了 residency（description 长度排序，见 `services/sync/audit_report.py`）[A3]。

**动作**：`askill audit --overlap` 用**确定性**近似：对 frontmatter description 做分词 → Jaccard/包含度 → 输出「疑似职责重叠」对及建议，明确标注是启发式、**不宣称语义理解**（与 README 对 audit 误报的诚实口径一致）。零依赖、不引入 embedding/LLM。
**验收**：同一技能集多次运行结果稳定；与现有 `audit --residency` 共享输出格式。

### P1-10 `bundle --external-only`

**依据**：skillfish 的 manifest **只追踪外部来源技能**，本地创作技能直接走项目内版本控制 [A12]；本项目 `services/manifest.py` 导出全部，跨机对齐时可能把本地技能当远程依赖重装 [A3]。

**动作**：manifest 每条增加 `origin`（`github` / `skills.sh` / `archive` / `local`，从已有 `sources.py` 派生）；`bundle --external-only` 过滤本地项；`install --manifest` 遇 `origin: local` 且本地不存在时**警告并跳过**，不静默尝试网络。
**验收**：`tests/test_manifest.py` 覆盖 4 种 origin 与离线行为。

---

## 4. P2 — 结构性债务（为 P1 让路）

### P2-11 ★ 打包白名单自动化

**依据**：v0.20.0 事故根因是 `pyproject.toml:50-60` 手工 `packages` 白名单漏掉新建的 `services.sync` 子包，仓库内 CI 天然发现不了，导致 PyPI 新装用户不可用（体检报告复检记录）。P1-5/P1-6 会新增 `scripts/` 与可能的子模块，白名单风险随拆分次数线性上升。

**动作**：改用 `setuptools.find_packages` / `find_namespace_packages`（保留 `package-dir` 映射与 `completion` 的 `package-data` 声明）；新增 `tests/test_packaging.py`：构建 wheel（或读取 `setuptools` 发现结果）断言 `agent_skill_manager.services.sync`、`...completion` 等子包齐全。**保留 release.yml 的 wheel 冒烟守门**，两者是互补而非替代。
**验收**：故意新增一个空子包的临时测试能触发断言；干净 venv 实装 `askill version` + `import agent_skill_manager.services.sync` 通过。

### P2-12 `cli.py` 按命令族拆 parser

**依据**：`cli.py` 已从 1,077 行涨到 21 命令规模，`_build_parser` 是主要增量来源（体检报告 §4 曾把「表驱动 dispatch」列为建议，v0.20 已落地 `_HANDLERS`）。

**动作**：按「同步分发 / 获取创作 / 质量运维」三组拆到 `controllers/parsers/`，`_build_parser` 只做组装；**`_HANDLERS` 表与所有测试 patch 目标保持不变**（0.20.0 拆包教训：先锁接缝再动文件）。
**验收**：`pytest -q` 全绿且 `git diff` 不含 handler 映射变更；与 P2-11 同批做，只跑一次完整发布冒烟。

### P2-13 Windows 真机回归

**依据**：README 已知限制 3 条与 Windows 相关（settings.json 占用、junction、死链），而当前测试多为 mock；体检记录里悬空 junction 的构造还需 `cmd /c mklink /J` 且目标须为本地卷 [A3]。

**动作**：GitHub Actions `windows-latest` 增加一组**非 mock**用例：真实 junction 创建/断链/GC、`settings.json` 只读锁告警、路径含空格。用临时目录隔离，不碰真机家目录。
**验收**：windows job 稳定通过；失败信息能区分「权限不足」与「逻辑缺陷」。

### P2-14 `docs/metrics.md` 月度可观测基线（不做遥测）

**依据**：三情景判断需要先行指标，而当前峰值高度依赖发版日（11-13 单日 245 次 / 三版本发布）[A5][C]。**明确拒绝内置 telemetry**：与 `PRIVACY.md` 离线定位冲突，且 2 stars 规模下收益为负。

**动作**：建 `docs/metrics.md`，每月记录一行可外部复核的指标与复现命令：`pypistats without_mirrors` 月总量 / 非发版日下载基线 / GitHub stars·forks·issues / skills.sh installs / `npx skills docs/agents.md` 国产条目数 / 上游 PR 状态。**首行填 2026-11-15 基线**（见 §6）。
**验收**：任一数字可在 2 条命令内复现；不含任何用户侧采集。

---

## 5. 明确不做（延续前两轮结论，新增 3 项）

| 不做 | 理由 |
|------|------|
| 桌面 GUI / Web 仪表盘 | 7.5k stars 的 Tauri 双雄赛道；与 CLI + 可被 agent 驱动的定位冲突 [A1][A9] |
| 企业私有注册表 / 服务端 | `iflytek/skillhub` 5.4k stars 与 `teamai-cli` 5.9k stars 的服务端战场；与零依赖离线定位冲突 [A1][A10] |
| 56 个国际 agent 覆盖竞赛 | 上游的规模游戏；只在社区 PR 出现时按 SLA 收 |
| rules/commands/agents/MCP 全资源 | `OpenPackage` 已做，范围失控风险高 |
| 内置遥测 / 用量上报 | 与 `PRIVACY.md` 冲突（见 P2-14） |
| **TAM / 收入预测模型** | 无可核验付费市场一手数据，会产出伪精确数字（分析报告 §6） |
| **为「15 这个数字」继续加产品** | 数量优势正在被上游抹平；改为提高每条声明的可信度与上游引用率 [C] |

---

## 6. 度量基线（2026-11-15，全部可复现）

| 指标 | 基线 | 复现方式 |
|------|------|---------|
| 版本 / 命令数 / 产品数 | 0.25.0 / 21 / 15 | `askill version`、`grep -c add_parser src/controllers/cli.py`、`askill products --json` |
| 测试 | 351 个 `def test_`（历史复检 362 passed） | `grep -rc "def test_" tests/*.py`、`pytest -q` |
| GitHub | 2 stars / 1 fork / 0 issues | `curl api.github.com/repos/yxdwind/agent-skill-manager` |
| PyPI 非镜像下载 | 累计 3,073；近 30 天 1,023；日均 36.5 | `curl https://pypistats.org/api/packages/cn-skill-sync/overall` |
| skills.sh | 1 skill / 2 installs | `https://skills.sh/yxdwind/agent-skill-manager` |
| 上游国产覆盖 | npx skills 9 行国产条目；DSH 7 行国产路径（含 WorkBuddy / CodeBuddy） | 分析报告 [A6][A7] |
| 发布节奏 | 25 releases / 2026-09-21 → 11-13（53 天） | `https://pypi.org/pypi/cn-skill-sync/json` |

> 本次环境未安装 `pytest` / `ruff`，**未现场复跑门禁**；测试数采用静态计数与历史复检交叉。执行 P0-1 前建议先在干净 venv 跑一次 `pip install -e ".[dev]" && pytest -q` 取实测值，避免把 362 直接写进徽章却与本机不符。

---

## 7. 落地批次与风险

| 批次 | 内容 | 版本建议 | 主要风险 / 回滚 |
|------|------|---------|----------------|
| 第一批 | P0-1 ~ P0-4（纯文档 + 收录对象） | 不触发发版，随下次提交 | 改 README 标题锚点前先查 `#支持的产品` 的徽章引用（体检记录里的既有教训） |
| 第二批 | P1-5 / P1-6（路径导出 + 漂移监测） | v0.26.0 | 外部 PR 属对外动作，需维护者确认；`--paths` 只派生不新增事实源 |
| 第三批 | P1-7 ~ P1-10（可靠性与门禁） | v0.27.0 | `doctor --fix` 默认 dry-run；`--apply` 必须有测试与退出码契约 |
| 第四批 | P2-11 ~ P2-14（打包、拆分、Windows CI、度量） | 与下一次模块拆分同批 | **先改自动发现并加 wheel 断言，再拆 parser**，避免 0.20.0 重演 |

**成功判据（相对值，不设伪精确目标）**：① 对外文档零可证伪表述；② 至少 1 个上游项目引用/合并本项目提供的国产路径；③ 非发版日下载基线抬升且峰值不再由自己发版主导；④ 新增任意子包时 CI 能自动发现；⑤ 全部门禁在干净 venv + wheel 实装上复跑通过。

---

*证据 URL 与可信度评级见 `docs/market-analysis-2026-11-15.md §9`。本报告中的优先级、成本（S/M/L）与情景判断均为推断 [C]，不是既成事实。*
