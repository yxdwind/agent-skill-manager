# 竞品对标研究：GitHub 上的同类 skill 管理器（2026-11-04）

> 方法：GitHub Search API 5 组关键词 + 网络搜索交叉验证，深读 8 个头部项目 README。
> 目的：为 agent-skill-manager（askill v0.20.1）提炼可借鉴机制，排出优化优先级。

## 一、生态快照

自研工具 9 月立项时同类只有 PyPI 上的 `sm` 一个；两个月后「skill 管理器」已是一个红海品类，
且**桌面 GUI 是爆发方向**（Tauri/Electron 双雄两个月冲到 7k+ 星）。

| 项目 | 星 | 形态 | 覆盖 | 一句话定位 |
|------|-----:|------|------|-----------|
| xingkongliang/skills-manager | 7446 | Tauri 桌面 + Rust CLI | 56 agents | 库式管理 + 多设备 Git 备份 + agent 自管理 |
| jiweiyeah/Skills-Manager | 1058 | Tauri 桌面 + skm CLI | 32 tools | symlink 同步 + 三级 Windows 链接策略 |
| MoizIbnYousaf/ai-agent-skills | 1156 | npm CLI+TUI | 多 runtime | 策展式库（house copies + 上游精选）+ collections |
| luongnv89/asm | 971 | npm CLI | 多 agent | **注意力预算审计** + 引用层（不装先用） |
| knoxgraeme/skillfish | 330 | npm CLI | 33 agents | **团队 manifest 同步**（bundle/install） |
| enulus/OpenPackage | 617 | npm CLI | 多平台 | 超越 skills：rules/commands/agents/MCPs 全资源管理 |
| iflytek/skillhub | 5398 | 自托管平台 + CLI | 多 agent | 企业私有注册表（讯飞，中文，Docker 部署） |
| caliber-ai-org/ai-setup | 1311 | CLI | 多 agent | 按代码库定制、持续同步整套 AI 配置 |

结论先行：askill 的**独有护城河**（15 国产产品矩阵、Windows junction 免管理员、原生事件 watch + 自愈、
按产品 frontmatter 门禁、声明式 products + 一致性测试锁）没有任何一家复刻；但对手有**四个成熟机制**
我们没有，且都直接命中我们的核心用户（多机/多产品/技能数百个的重度用户）。

## 二、值得借鉴的四个机制（深度拆解）

### 1. 团队 manifest 同步（skillfish）

`skillfish bundle` 把本机已装技能扫描成一份 `skillfish.json` 提交进代码仓库；队友 `skillfish install`
读取 manifest 把本地技能对齐到与清单一致。**把「我的技能清单」变成可提交、可评审、可还原的资产**——
这是团队/多机场景最轻的同步方案，不依赖任何服务端。

askill 缺口：我们有 sources 追踪（装了什么、来自哪），但没有「把当前清单导出为声明、在别处对齐」的
工作流。我们的中央仓库本身就是规范布局，做一个 `askill bundle` 导出 + `askill install --manifest`
对齐是天然契合，成本中等。

### 2. 注意力预算审计（asm residency audit）

洞察：每个已装技能的 description 都会常驻 agent 的系统提示词，**不管用不用都在花 token**。
装 165 个技能的 QwenWork 重度用户（这正是我们的典型用户画像）每条消息都在为长描述付费。
`asm audit residency` 给「不配常驻」的技能排序并给出处置命令。

askill 缺口：我们的 audit 是安全视角（提示注入/危险代码），没有**成本视角**。做一个
`askill audit residency`：统计中央仓库每个技能的 description 长度/token 占用、按「描述收益比」
排序、给出 demote/卸载建议。成本小，差异化强，且与我们的 audit 命令族天然同构。

### 3. agent 自管理技能（xingkongliang manage-skills）

桌面应用往选定的 agent 里装一个 `manage-skills` 技能，教会 agent 自己去装/部署/汇报技能状态——
**把人从管理循环里拿出来**。这个分发飞轮也是它两个月 7k 星的重要推力。

askill 缺口：我们完全有能力做且更顺——用户就在 AutoClaw 这类 agent 里。做一个 `askill-ops`
技能发布到 yxdwind/skills：教会 agent 用 askill 完成「装/同步/查状态/审计/打包」全流程，
AutoClaw/Kimi/QwenWork 用户装一个技能就获得「对话式技能管理」。

### 4. 引用层：不装先用（asm get / borrow）

`asm get <skill>` 把 SKILL.md 写到 stdout、`asm borrow` 借用完整目录（用完 cleanup）——
试用成本降为零，也顺便解决「注意力预算」问题的另一面。

askill 缺口：装是唯一入口。`askill get <owner/repo@skill>` 输出到 stdout / 临时目录（打印
路径，用户自行清理），作为「先看后装」的低成本试用层。成本中小。

## 三、对手强但我们不跟的（明确不做，避免功能债）

- **桌面 GUI**：双雄的赛道。askill 的定位是脚本化/自动化友好的 CLI + 可被 agent 驱动，GUI
  会稀释定位且开发成本不可承受（Tauri+Rust 双技术栈）。
- **企业私有注册表（skillhub）**：服务端产品，与零依赖 CLI 定位冲突；未来若企业用户出现，
  对接其 API 比自建合理。
- **56 agent 覆盖竞赛**：国际产品覆盖是对手的战场，我们的差异化就是国产纵深；不加国际产品，
  只在社区 PR 出现时按 SLA 收。
- **rules/commands/agents/MCP 全资源管理（OpenPackage）**：范围失控风险高；skills 垂直打透
  是我们的立足点。

## 四、我们强于所有对手的（营销物料可直接引用）

1. 15 个国产产品矩阵 + 按产品 frontmatter 门禁（无人有）
2. Windows junction 免管理员 + 三级降级（jiweiyeah 有类似，无人覆盖国产路径矩阵）
3. 原生文件事件 watch + 产品侧链接自愈（v0.19.0，无人有）
4. 安装即静态安全审计 + 按产品漂移检测 drift（asm 有安全审计，无国产 frontmatter 维度）
5. 声明式 products.py + 一致性测试锁（工程可靠性无人对标）

## 五、优化优先级（本轮提案）

| # | 优化项 | 来源 | 成本 | 价值 | 本轮 |
|---|--------|------|------|------|:---:|
| P1 | `askill bundle` / `install --manifest` 团队清单同步 | skillfish | M | 多机/团队核心场景 | ✅ |
| P2 | `askill audit residency` 注意力预算报告 | asm | S | 165 技能重度用户画像强命中 | ✅ |
| P3 | `askill-ops` agent 自管理技能（发布到 yxdwind/skills） | xingkongliang | S | AutoClaw 生态分发飞轮 | ✅ |
| P4 | `askill get` 引用层 | asm | S-M | 先看后装 | 下轮 |
| P5 | 中央仓库 Git 备份/多机合并 | xingkongliang | L | 有 P1 后价值递减 | 观察 |
| P6 | zip/.skill 归档安装 | xingkongliang | S | DuMate 往返 | 下轮 |

若本轮 P1-P3 落地，随 v0.21.0 发布（feat 语义），营销物料的差异化表述同步更新。

## 六、资料出处

- 各项目 README 原文（raw.githubusercontent.com，2026-11-04 抓取）
- GitHub Search API：agent skills manager / skills manager claude / claude skills sync /
  skills marketplace / agent skills registry 五组查询
- agentskillshub.top「182 个安全评分的管理工具」榜单（2026-10-09 更新）
- GitHub Changelog 2026-04-16：gh skill 官方化（2.90+）
