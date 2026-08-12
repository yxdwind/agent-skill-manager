# 【保姆级教程】agent-skill-manager 实战：一行命令把 Skill 同步到 9 个国产 AI 开发工具

## 前言

2026 年国产 AI 编程工具百花齐放：AutoClaw、Kimi Code、MiniMax Code、WorkBuddy、Trae Solo、CodeBuddy、Comate、Qoder……每个都支持 Agent Skills，但 skill 存放目录各不相同。本教程手把手教你用 agent-skill-manager 一次性解决 skill 同步问题。

## 目录

1. 什么是 Agent Skills
2. 为什么需要 skill 管理工具
3. 环境准备
4. 安装 agent-skill-manager
5. 核心命令详解
6. 实战：创建并同步一个 skill
7. 常见问题与解决方案
8. 总结

---

## 一、什么是 Agent Skills

Agent Skills 是 2026 年 AI 编程领域的关键概念。简单说，Skill 就是一个包含 SKILL.md 文件的文件夹，里面写明了特定领域的专业知识和操作规范。

比如你可以创建一个「Python 代码规范」skill，AI 助手在任何项目中都能自动按这个规范来写代码、做 Code Review。

**Skill 的核心结构：**

```
python-standards/
├── SKILL.md           # 主文件：skill 名称、描述和指令
├── scripts/           # Python 脚本（可选）
└── references/        # 参考文档（可选）
```

## 二、为什么需要 skill 管理工具

### 问题的根源

每个国产 AI Agent 产品的 skill 目录路径都不相同：

| 产品 | Skill 目录 | 开发者 |
|------|-----------|--------|
| AutoClaw/OpenClaw | ~/.openclaw/skills/ | — |
| Kimi Code | ~/.config/agents/skills/ | 月之暗面 |
| MiniMax Code | ~/.agents/skills/ | MiniMax |
| WorkBuddy | ~/.workbuddy/skills/ | 腾讯 |
| Trae Solo | ~/.trae/skills/ | 字节跳动 |
| CodeBuddy | ~/.codebuddy/skills/ | 腾讯 |
| Comate/文心快码 | ~/.comate/skills/ | 百度 |
| Qoder/通义灵码 | ~/.qoderwork/skills/ | 阿里 |

**如果你同时用 3 个以上产品，每次开发或修改一个 skill，就要手动复制到多个目录。** 一天改几次，这个操作量就让人崩溃了。

### 解决思路

agent-skill-manager 采用「中央仓库 + 符号链接」的架构：

1. 所有 skill 统一存放在 `~/.agents/skills/` 目录
2. 运行 `askill sync` 一键创建 junction（Windows）或 symlink（macOS）
3. 中央仓库改一处，所有产品自动同步

## 三、环境准备

### 系统要求

- Python 3.8 及以上版本
- macOS 或 Windows 操作系统
- pip 包管理器

### 检查 Python 版本

```bash
python --version
# Python 3.8.0 或更高版本即可
```

## 四、安装 agent-skill-manager

### 方法一：pip 安装（推荐）

```bash
# 克隆仓库
git clone https://github.com/yxdwind/agent-skill-manager.git
cd agent-skill-manager

# 开发模式安装
pip install -e .
```

### 方法二：npx skills 安装

```bash
npx skills add yxdwind/agent-skill-manager
```

**安装成功验证：**

```bash
askill version
# 输出：agent-skill-manager v0.1.0
```

## 五、核心命令详解

### 5.1 `askill products` — 查看支持的产品

会自动检测本地安装了哪些产品，未安装的标记为 `[--]`。

### 5.2 `askill list` — 列出中央仓库的 skill

```bash
askill list
```

### 5.3 `askill status` — 查看同步状态

一目了然看到每个 skill 在每个产品中的状态：`ok link`/`ok copy`/`ok native`/`--`。

### 5.4 `askill sync` — 一键同步

```bash
# 同步所有 skill
askill sync

# 同步指定 skill
askill sync my-python-skill
```

### 5.5 `askill install` — 安装新 skill

```bash
# 从本地目录安装
askill install ~/skills/my-new-skill

# 从 GitHub 安装
askill install https://github.com/user/repo/tree/main/skill-name

# 安装后同步
askill sync
```

### 5.6 `askill remove` — 移除 skill

```bash
# 从中央仓库和所有产品中移除
askill remove my-old-skill
```

### 5.7 `askill pack` — 打包给 DuMate

```bash
# DuMate（百度搭子）通过 App 上传 skill，先打包成 zip
askill pack my-skill
# 生成 ~/.agents/skills/my-skill.zip
```

## 六、实战：创建并同步一个 skill

### 步骤 1：创建 skill

```bash
mkdir -p ~/.agents/skills/code-review
```

创建 `~/.agents/skills/code-review/SKILL.md`：

```yaml
---
name: code-review
description: Code review standards for our team
---

# Code Review Skill

## 审查要点
- 变量命名是否清晰
- 函数是否单一职责
- 是否有未处理的异常
- SQL 是否使用了参数化查询

## 审查流程
1. 先看整体结构和设计
2. 检查核心逻辑和数据流
3. 验证边界条件和异常处理
4. 确认测试覆盖
```

### 步骤 2：安装并同步

```bash
# 安装到中央仓库
askill install ~/.agents/skills/code-review

# 一键同步到所有产品
askill sync code-review
```

### 步骤 3：验证

```bash
askill status code-review

# 输出：
# Skill        AutoClaw  Kimi     MiniMax   WorkBuddy  Trae    CodeBuddy  Comate   Qoder
# ------------------------------------------------------------------------------------
# code-review  ok link  ok link  ok native ok link   ok link ok link   ok link  ok link
```

**完成！** 现在在 9 个产品中打开任何项目，AI 都会按你的规范做 code review。

## 七、常见问题与解决方案

**Q1: Windows 提示权限不足？** — 使用的是 `mklink /J`（junction），不需要管理员权限。失败会自动降级为复制。

**Q2: 如何添加新产品？** — 编辑 `src/agent_skill_manager/products.py`，加一项配置即可。欢迎提 PR。

**Q3: 跟 skills-manage 区别？** — skills-manage 面国际化产品，agent-skill-manager 专注国产产品。可同时使用。

## 八、总结

**核心优势：** 零依赖 · Python 3.8+ · 34 个测试通过 · Win/Mac 双平台 · npx skills 生态兼容

**项目地址：** https://github.com/yxdwind/agent-skill-manager

如果对你有帮助，欢迎 Star ⭐ 和提 PR 添加新产品支持！
