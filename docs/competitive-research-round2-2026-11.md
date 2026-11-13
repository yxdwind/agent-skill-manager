# 竞品对标第二轮：机制借鉴方案（2026-11-13）

> 方法：第一轮（docs/competitive-research-2026-11.md）覆盖 8 家「管理器」；本轮补挖 7 个上次未深挖的
> 头部项目 + 本月新生态信号（聚合站/镜像站/官方动作），只给方案不动手，等拍板。
> 证据：各项目 README 原文（raw.githubusercontent.com，2026-11-13 抓取）+ 网络搜索。

## 一、本轮新拆解的 7 个项目

| 项目 | 星 | 一句话 | 值得看什么 |
|------|-----:|--------|-----------|
| davila7/claude-code-templates | 33k | Claude Code 组件开放目录 | PR 过 NVIDIA SkillSpector 安全扫描；「栈」整装安装；文档站 |
| tech-leads-club/agent-skills | 7.2k | 安全加固的托管注册表 | **-a 定向安装**；引用 Snyk 报告做安全定位 |
| NanmiCoder/cc-haha | 15k | 桌面 Claude Code 工作台 | **中文用户群运营**（企业微信群）；社区授权模式 |
| jeremylongshore/tons-of-skills-marketplace | 2.9k | 模型无关技能平台 | **「数字必带口径」纪律**；来源四分类；镜像 content lockfile |
| FrancyJGLisboa/agent-skills-platform | 2.4k | 团队技能生命周期平台 | **quarantine + rollback** 语义；桌面贴链接安装 |
| caliber-ai-org/ai-setup | 1.3k | 代码库定制的 AI 配置持续同步 | **无 LLM 的确定性一致性评分**；跨 agent 同步的优雅降级话术 |
| binance/binance-skills-hub | 1k+ | 官方厂商技能市场 | 凭据最小权限/IP 白名单的技能安全声明范式 |

生态面新信号：skills-hub.ai（每日镜像源仓库，一条命令装）、atlasrepo.com（浏览/对比/起草）、
explainx skills-cli、ibl.ai 企业技能目录。**聚合站正在成为分发层**——被收录 = 免费流量。

## 二、借鉴方案（按优先级，全部未实现）

### P1 产品定向同步：`askill sync <skill> --only <short...>`（学 tech-leads-club -a）

现状缺口：sync 是全有或全无（15 个产品全量）。竞品支持 `install -s my-skill -a cursor claude-code`。
真实场景：「这个技能只进 AutoClaw2 和 Kimi」「先在 Trae 上试一周再推广」。
方案：sync/install 增加 `--only <short> [<short>...]`（按 products.py 的 short 匹配，非法 short 直接报
错并列出可选项）；默认行为不变。成本 M（sync_one_product 逐产品逻辑已存在，只加过滤 + 测试）。

### P2 更新快照与回滚：`askill rollback <skill>`（学 FrancyJGLisboa quarantine/rollback）

现状缺口：`askill update` 把旧目录挪到 temp 后删除——升坏了没有后悔药。
方案：update/重装前把当前版本快照到 `~/.agents/skills/.askill-versions/<skill>/`（仅保留上一版，避免
无限膨胀）；`askill rollback <skill>` 恢复快照并重新 sync；`--list` 查看可回滚项。与我们的安全叙事
（审计门禁、冒烟守门）同构：**回滚是审计的最后一道保险**。成本 S-M。

### P3 README「数字必带口径」纪律（学 tons-of-skills-marketplace）

它的原话：「无口径的数字是语料出现五个互相矛盾答案的开始」。我们的 README 已有「300 多个…以
badge 为准」，推广到全部数字：15 个产品（指向 products.py）、20 个 topics、覆盖率等，每个数字旁
给复现命令或指向权威来源。纯文档，成本 S。

### P4 收录与分发（零代码，增长线）

- 向聚合站提交收录：skills-hub.ai（自动镜像 GitHub 源仓库）、atlasrepo、explainx；awesome 列表
  PR（VoltAgent #122 已 open，跟进合并）
- 每个聚合站收录 = 一条免费分发渠道，且「一条命令装」的入口直接复用我们已有的
  `askill install yxdwind/skills@askill-ops`
- 安全叙事弹药：tech-leads 引用的 Snyk 报告（13.4% 市场 skills 有严重问题）可作为我们「安装即审计」
  定位的引用依据（注明来源与日期）

### P5 中文用户群（学 cc-haha，零代码，用户侧）

cc-haha 15k 星的中文运营路径：企业微信用户群 + 打赏 + 定制联系。我们起步版：建一个微信群/企业微信群
（群二维码进 README），国产定位配中文社区是信任信号。需要你建群，我写 README 物料。

### P6（观察）确定性一致性评分（学 caliber score）

caliber 的 `score` 无 LLM 检查上下文文件与仓库的一致性。我们已有 verify/audit/drift/doctor 四件套，
语义重叠度高；暂不动，等 doctor 用起来后看投诉分布再决定是否加 `doctor --score`。

## 三、明确不跟（延续第一轮结论，新增三项）

- **本地 Web 仪表盘**（davila7 两个 dashboard、cc-haha 桌面端）：GUI/服务化背离 CLI 定位
- **企业技能目录/组织级分配**（ibl.ai、FrancyJGLisboa 的组织验收协议）：服务端产品，不做
- **认证分级计划**（tons-of-skills T0-T4）：没有规模前搞认证是空中楼阁；已有 audit 评分 + 聚合站
  收录审核，够用
- **栈级捆绑安装**（davila7 --agent stack）：manifest 已覆盖声明式批量，语义重复

## 四、建议的落地批次（等拍板）

| 批次 | 内容 | 版本 |
|------|------|------|
| 本轮开发 | P1 定向同步 + P2 快照回滚 + P3 README 口径 | v0.24.0（一次开发轮） |
| 本轮分发 | P4 聚合站提交 + awesome PR 跟进（无代码） | 即时 |
| 用户侧 | P5 建群 + 发布第 3 篇文章（昨天已交付） | 即时 |

成功标准：347+ 测试全绿；PyPI 0.24.0 + venv 实装；README 数字全部带口径；
至少 2 个聚合站收录 askill-ops / skills 仓库。
