# 两个月内这个赛道挤进了 7 个千星项目，我还是开源了一个"没人做"的

> 首发：掘金 · agent-skill-manager 系列 第 3 篇 · 2026-11
> 数据口径：GitHub Search API + 各项目 README，2026-11 上旬抓取；星数会变，趋势不会。

## 一、先交代背景：我的项目现在 2 个星

不装。我做了一个管理 AI agent 技能的命令行工具，[agent-skill-manager](https://github.com/yxdwind/agent-skill-manager)（PyPI 名 `cn-skill-sync`，命令 `askill`），到写这篇文章时 **2 个 star，1 个 fork**。

这不妨碍它是我今年投入最认真的开源项目：15 个国产 AI agent 产品（AutoClaw2、Kimi、MiniMax、Trae、CodeBuddy、Comate、Qoder、QwenWork、DoubaoWork、ZCode 等）的技能目录，用中央仓库加链接的方式一处维护、全部同步；Windows 上用 junction，不需要管理员权限；改动实时监听自动同步；装技能先跑安全审计；300 多个自动化测试（准确数字以 README 的 badge 为准）。

九月底立项时我搜了一圈，同类只有 PyPI 上一个叫 `agent-skill-manager` 的国际项目。两个月后再搜，搜索结果让我有点坐不住。

## 二、两个月，这条赛道挤成红海

GitHub 搜索 "agent skills manager"，相关仓库一千多个。按星数排，头部是这样（2026-11 上旬数据）：

| 项目 | 星数 | 形态 |
|------|-----:|------|
| xingkongliang/skills-manager | 7400+ | 桌面应用（Tauri + Rust CLI），覆盖 56 个 agent |
| jiweiyeah/Skills-Manager | 1000+ | 桌面应用，32 个工具，symlink 同步 |
| MoizIbnYousaf/ai-agent-skills | 1100+ | npm CLI + TUI，策展式技能库 |
| iflytek/skillhub | 5300+ | 讯飞出的企业自托管技能注册表 |
| caliber-ai-org/ai-setup | 1300+ | 按代码库定制 AI 配置的 CLI |
| luongnv89/asm | 900+ | npm CLI，主打"注意力预算"审计 |
| knoxgraeme/skillfish | 300+ | npm CLI，团队 manifest 同步 |

还有一个背景信号：GitHub 官方在 2026 年 4 月把 `gh skill` 做进了 CLI（官方 changelog 可查）。生态判断很一致：**技能会成为 agent 时代的"包管理问题"**。

桌面双雄两个月 7 千星的速度，说明需求真实存在。但也说明一个残酷事实：如果我只是"再做一个技能管理器"，入场即炮灰。

## 三、我把 7 个头部项目挨个拆了一遍

花了两天读这 7 家的 README 和文档，逐个问三个问题：它解决什么、它的机制我能不能学、它做的事我要不要跟。

**学了四个，全部进了 v0.21.0 和 v0.22.0：**

1. **团队 manifest 同步**（学 skillfish）。`askill bundle` 把本机技能清单导出成一个可提交进代码仓库的 JSON，队友一条 `askill install --manifest` 对齐。多机、小团队场景最轻的同步方案，零服务端。
2. **注意力预算审计**（学 asm）。一个洞察让我后背发凉：你装的每个技能，它的 description 都常驻在 agent 的系统提示词里，每条消息都在烧 token，用不用都烧。`askill audit --residency` 按上下文成本给全部技能排序，超长的给出精简建议。第一次跑就抓出我自己一个 1014 字符的 description。
3. **先看后装**（学 asm 的 get/borrow）。`askill get` 把 SKILL.md 打到 stdout 预览，`--dir` 借用完整目录到临时路径，`--list` 看仓库里有什么。试用成本归零。
4. **agent 自管理**（学 xingkongliang 的 manage-skills）。他们往 agent 里装一个教会 agent 自己管理技能的技能，两个月 7 千星里这个分发飞轮功不可没。我做了 [askill-ops](https://github.com/yxdwind/skills) 发布到技能仓库，装一条命令：`askill install yxdwind/skills@askill-ops`。

另外顺手修了一个国内用户天天会撞的坑：全局 git 代理（Clash 那类）没开的时候，装技能报一屏看不懂的错。现在错误信息会点名代理问题并给出绕过命令。

**拒绝了三个，写进了决策记录：**

- **桌面 GUI**：双雄的战场，Tauri + Rust 两套技术栈我养不起，而且会稀释 askill 的定位（脚本化、可被 agent 驱动）。
- **企业私有注册表**：讯飞用一整个平台做这个。我的零依赖 CLI 做服务端产品是自我背叛。
- **56 个 agent 覆盖竞赛**：国际产品覆盖是对手的主场。askill 的差异化恰恰是**只做国产纵深**：每家产品的目录在哪、哪些产品共享目录、哪些要传 zip、哪些直接扫中央仓库，这些脏活国际项目永远不会为你做。

## 四、为什么 2 个星还要继续

对标报告里最扎心的一行是我自己写的：竞品每一家都比我有流量。但拆完发现，**没有任何一家的机制覆盖国产产品的目录矩阵**。junction 免管理员、事件驱动 watch 加产品侧链接自愈、按产品 frontmatter 的门禁校验，这些是从国产产品的真实目录结构里长出来的，不是从国际生态翻译过来的。

红海证明需求，空白证明定位。这轮对标让 askill 的边界第一次变得清晰：不做桌面应用，不做注册表，不做国际覆盖；做国产 agent 技能层的基础设施。

止损规则我也提前写好了：如果单篇内容平均阅读低于 1000，就换选题角度，而不是继续堆功能。

## 五、给你的可复用流程

这次对标到落地的流程，别的项目可以直接抄：

1. GitHub Search API 跑 5 组关键词，头部项目按星数全量拉 README；
2. 每家回答三个问题：解决什么 / 能借什么 / 要不要跟；
3. 借的进版本（v0.21.0、v0.22.0 各带来源标注），拒绝的写进文档说明理由，防止三个月后自己忘了为什么不做；
4. 发布前跑全量测试加干净 venv 实装验证，CI 里加 wheel 冒烟守门。

完整对标文档在仓库 `docs/competitive-research-2026-11.md`，8 家的机制拆解都在。

---

仓库：https://github.com/yxdwind/agent-skill-manager
安装：`pip install cn-skill-sync`
上一篇与上上篇：launch 系列长文（仓库 marketing/01、marketing/02，已发掘金与知乎）

*本文所有星数为 2026-11 上旬快照，会过时；机制描述以各项目当前 README 为准。*
