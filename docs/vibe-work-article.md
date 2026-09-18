# 我和 GLM-5.2 做了一个管住 11 个国产 AI Agent 技能的同步工具

> 本文是我在稀土掘金 **Vibe Work** 的参赛作品说明。项目完全开源：**[yxdwind/agent-skill-manager](https://github.com/yxdwind/agent-skill-manager)**，MIT 协议，由我与智谱 **GLM-5.2** 结对开发。

![Demo](./demo.svg)

## 痛点：skill 有了，但它们散落在 11 个地方

Agent Skills 正在成为 AI 编程工具的标准扩展方式：一个文件夹、一份 `SKILL.md`，就能教会你的 AI 助手一套专属工作流。但问题随之而来——**每个国产 AI Agent 产品都有自己的 skill 目录**：

```text
~/.openclaw/skills/            ← AutoClaw（智谱）
~/.config/agents/skills/       ← Kimi（月之暗面）
~/.agents/skills/              ← MiniMax Code
~/.workbuddy/skills/           ← WorkBuddy（腾讯）
~/.trae/skills/                ← Trae（字节跳动）
~/.codebuddy/skills/           ← CodeBuddy（腾讯）
~/.comate/skills/              ← Comate（百度）
~/.qoderwork/skills/           ← Qoder（阿里）
~/.qwenworkcn/skills/          ← QwenWork 千问办公（阿里）
...以及 App 内管理的豆包工作、DuMate
```

我写了一个调股票分析的 skill，想同时给 AutoClaw 和 Kimi 用——复制过去，改了一版，又复制，再改，再复制。第 3 次的时候我意识到：**这不是 skill 的问题，是分发的问题**。

## 方案：中央仓库 + 一键分发

**agent-skill-manager** 的思路很简单：`~/.agents/skills/` 作为唯一权威源，一条命令分发到所有产品。

```bash
askill sync my-skill
```

同步不是复制，是 **symlink（macOS）/ junction（Windows，无需管理员权限）**：编辑中央仓库里的 SKILL.md，所有产品立刻看到最新版。链接创建失败时自动降级为复制。零第三方依赖，纯 Python 标准库。

## 它现在长这样

- **11 个产品**：AutoClaw、Kimi、MiniMax Code、WorkBuddy、Trae、DuMate、CodeBuddy、Comate、Qoder、QwenWork（千问办公）、DoubaoWork（豆包工作）
- **一键安装**：`askill install --sync <github-url>`，支持仓库根目录 / `/tree/` / `/blob/` 三种 GitHub 链接，默认分支自动识别，装完直接同步
- **跨平台采纳**：`askill adopt autoclaw my-skill` 把 AutoClaw 里调好的 skill 采纳进中央仓库，同步给其他 10 个产品
- **DuMate 特殊照顾**：百度 DuMate 不暴露文件系统，`askill pack` 打包 .zip 上传

## 顺手做了一个安全评测引擎

skill 本质上是"给 AI 的指令 + 可执行脚本"，装一个来路不明的 skill 就像装一个来路不明的软件包。所以工具内置了 `askill audit`——**零依赖静态分析**，从 100 分起扣：

| 检测维度 | 级别 | 例子 |
|---------|------|------|
| 提示注入 | critical | "ignore all previous instructions"、绕过安全护栏 |
| 危险代码 | critical/high | `curl \| sh`、`rm -rf /`、`exec()`、`shell=True` |
| 敏感信息 | high/medium | 读 `~/.ssh`、硬编码 API key、webhook 外发 |
| 二进制文件 | high | `.exe`/`.dll` 混进 skill 目录 |

评分直接出现在 `askill list` / `askill status` 里。我对自己中央仓库跑了一遍：33 个 skill，最高 100/A，最低 42/F（一个读取 `~/.ssh/id_rsa` 的）——**这个功能第一次让我看清了我在给 AI 喂什么**。

## Vibe Coding 过程：GLM-5.2 是怎么跟我协作的

这个项目从 v0.1.0 到 v0.7.0，全程与 **GLM-5.2 结对开发**，几个印象深的点：

1. **需求收敛靠追问**：我最初只说"加个从 GitHub 装 skill 的功能"，GLM 先问清了 URL 形态、要不要自动同步、冲突怎么办，再动手——避免了返工
2. **测试先行不是口号**：每个功能（adopt、audit、install --sync）都是 76 个测试用例之一先行，GLM 写测试时发现了我没想到的边界（junction 与 copy 的降级语义、Windows 编码问题）
3. **CI 是 AI 代码的质检员**：GitHub Actions 三平台矩阵（ubuntu/windows/macOS）跑出来的问题（Python 3.9 语法兼容、setuptools 缺失）比人肉 review 抓得快
4. **AI 也会遗漏**：加新产品时 GLM 更新了 README、路径文档、产品注册表，但漏了架构图 SVG——**人要负责全局一致性**，这也是我保留的关键角色

工程细节：项目重构为分层架构（config / controllers / models / services / utils），CI 三平台绿标，76 个测试全部通过。

## 体验方式

```bash
git clone https://github.com/yxdwind/agent-skill-manager
cd agent-skill-manager
pip install -e .

askill status        # 查看各产品安装状态（带评分）
askill audit         # 对全部 skill 做安全评测
askill sync          # 一键同步
```

支持中文（默认）和英文 README。欢迎 star、提 issue、提 PR。

## 写在最后

Vibe Coding 的争论常常停留在"AI 能不能写代码"。这个项目给我的答案是：**AI 能写代码，但分发、安全、跨产品一致性这些"工程脏活"，恰恰是 AI 协作最出彩的地方**——前提是你把需求说清楚，把验收标准（测试 + CI）搭好。

工具地址：**[github.com/yxdwind/agent-skill-manager](https://github.com/yxdwind/agent-skill-manager)** ，觉得有用请给个 star ⭐
