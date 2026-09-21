# 开源中国（OSCHINA）同步文章

> 基于 Vibe Work 参赛文章适配：OSCHINA 读者更看重技术实现与工程实践，弱化比赛语境，强化架构与代码。
> 标题候选：①《用 Python 标准库管理 11 个国产 AI Agent 的技能同步》②《junction + 中央仓库：解决国产 AI Agent 的 skill 割裂问题》

---

## 用 Python 标准库，管住 11 个国产 AI Agent 的技能同步

### 背景

Agent Skills 正在成为 AI 编程工具的标配扩展机制（一个文件夹 + 一份 SKILL.md）。国产工具新增 skill 支持的速度很快，但**目录各自为政**：AutoClaw 在 `~/.openclaw/skills/`，Kimi 在 `~/.config/agents/skills/`，Qoder 在 `~/.qoderwork/skills/`……同一个 skill 想跨工具复用，只能手工复制。

本文介绍我开源的 agent-skill-manager（`askill`）：用"中央仓库 + 文件系统链接"解决这个问题，全程只用 Python 标准库。

### 核心设计：junction/symlink 而非复制

中央仓库 `~/.agents/skills/` 是唯一权威源。分发时：

- **Windows**：`mklink /J` 创建 junction——不需要管理员权限，这是选 junction 而非 symlink 的关键原因
- **macOS**：`ln -s` 创建 symlink
- **降级策略**：链接创建失败（权限、跨盘等）自动降级为整目录复制
- **效果**：编辑中央仓库的 SKILL.md，11 个产品目录"立即"看到新版本，零同步延迟

实现上有两个坑值得记录：

1. Windows 判断 reparse point 不能用 `os.path.islink()`（对 junction 返回 False），需要 `fsutil reparsepoint query` 或 `ctypes` 读属性
2. `subprocess` 调用 `mklink` 时中文输出在 GBK 控制台会触发 `UnicodeDecodeError`，需要显式 `encoding="utf-8", errors="replace"`

### 包名与导入名分离

CLI 命令是 `askill`，PyPI 包名也用 `askill`（`pip install askill`），但导入名保持 `agent_skill_manager`——发行名与导入名分离是 CLI 工具的常见做法，命令与安装名一致对用户最友好。项目本身按 src 布局 + `package-dir` 映射组织（config / controllers / models / services / utils 分层）。

### 附带产物：零依赖安全评测引擎

skill 本质是"给 AI 的提示词 + 可执行脚本"，跨工具复用放大了供应链风险。工具内置 `askill audit`：纯静态分析、零第三方依赖，检测提示注入（instruction override）、危险代码（`curl | sh`、`exec`、`shell=True`）、敏感信息（读 `~/.ssh`、webhook 外发）、二进制混入四个维度，A-F 评分并在 `askill status` / `list` 中展示。

实测对我自己中央仓库的 33 个 skill 打分：最高 100/A，最低 42/F——那个 F 级 skill 里有一个读取 `~/.ssh/id_rsa` 的脚本。

### 工程实践

- GitHub Actions 三平台矩阵（ubuntu/windows/macOS × Python 3.10/3.13），76 个测试
- PyPI：`pip install askill`
- 与智谱 GLM-5.2 结对开发：AI 负责实现与测试用例生成，人负责需求收敛、跨文档一致性（架构图/README/代码三方同步是 AI 最容易漏的）与验收

### 链接

- 仓库：https://github.com/yxdwind/agent-skill-manager （MIT，求 star）
- 架构图与产品路径表见仓库 docs/

---

*本文同时是稀土掘金 Vibe Work 活动的参赛作品说明，欢迎交流。*
