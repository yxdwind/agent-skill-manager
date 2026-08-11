<div align="center">

# Agent Skill Manager

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-0078D4?logo=windows&logoColor=white)](https://github.com/yxdwind/agent-skill-manager)
[![License](https://img.shields.io/badge/License-MIT-22c55e?logo=opensourceinitiative&logoColor=white)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-34%20passed-22c55e)](tests/)
[![Products](https://img.shields.io/badge/Products-9%20supported-8b5cf6)](#支持的产品)

**一次开发，九端同步** — 跨平台统一管理国内 AI Agent 产品的 Skill 安装与同步

[安装](#安装) · [使用](#使用) · [二次开发](#二次开发) · [架构原理](#架构原理)

</div>

---

## 痛点

每个国产 AI Agent 产品都有自己独立的 skill 目录，开发一个 skill 要手动复制到每个产品：

```
~/.openclaw/skills/my-skill/          ← AutoClaw
~/.config/agents/skills/my-skill/      ← Kimi Code
~/.workbuddy/skills/my-skill/          ← WorkBuddy
~/.trae/skills/my-skill/               ← Trae Solo
~/.codebuddy/skills/my-skill/          ← CodeBuddy
~/.comate/skills/my-skill/             ← Comate
~/.qoderwork/skills/my-skill/          ← Qoder
... 每改一次都要重复一遍
```

**agent-skill-manager** 用「中央仓库 + 一键分发」解决这个问题：改一处，全同步。

## 支持的产品（9 个）

| 产品 | 公司 | macOS 目录 | Windows 目录 | 同步方式 |
|------|------|-----------|-------------|---------|
| AutoClaw/OpenClaw | — | `~/.openclaw/skills/` | `%USERPROFILE%\.openclaw\skills\` | symlink/junction |
| Kimi Code | 月之暗面 | `~/.config/agents/skills/` | `%USERPROFILE%\.config\agents\skills\` | symlink/junction |
| MiniMax Code | MiniMax | `~/.agents/skills/` | `%USERPROFILE%\.agents\skills\` | 原生支持 |
| WorkBuddy | 腾讯 | `~/.workbuddy/skills/` | `%USERPROFILE%\.workbuddy\skills\` | symlink + settings.json |
| Trae Solo | 字节跳动 | `~/.trae/skills/` | `%USERPROFILE%\.trae\skills\` | symlink/junction |
| DuMate | 百度 | App 内管理 | App 内管理 | 打包 .zip 上传 |
| CodeBuddy | 腾讯 | `~/.codebuddy/skills/` | `%USERPROFILE%\.codebuddy\skills\` | symlink + settings.json |
| Comate / 文心快码 | 百度 | `~/.comate/skills/` | `%USERPROFILE%\.comate\skills\` | symlink/junction |
| Qoder / 通义灵码 | 阿里 | `~/.qoderwork/skills/` | `%USERPROFILE%\.qoderwork\skills\` | symlink/junction |

## 架构原理

![Architecture](docs/architecture.svg)

**核心设计**：中央仓库 `~/.agents/skills/` 作为唯一权威源，通过 symlink（macOS）或 junction（Windows）自动分发到各产品。对不支持文件系统的 DuMate，打包为 .zip 手动上传。

- **Windows**：使用 `mklink /J` 创建 junction，无需管理员权限
- **macOS**：使用 `ln -s` 创建 symlink
- **自动降级**：链接创建失败时自动降级为复制模式
- **零依赖**：仅使用 Python 标准库

## 安装

```bash
# 开发模式安装（推荐）
cd agent-skill-manager
pip install -e .

# 如果 pip 遇到 TLS 证书问题
python -m pip install -e . --no-build-isolation
```

安装后 `askill` 命令全局可用。

也可以通过 `npx skills` 生态安装：

```bash
# 安装 skill 定义到所有支持的 agent 产品
npx skills add yxdwind/agent-skill-manager
```

## 使用

```bash
# 查看所有产品的 skill 安装状态
askill status

# 一键同步所有 skill 到所有产品
askill sync

# 同步指定 skill
askill sync my-skill

# 列出中央仓库中的所有 skill
askill list

# 安装 skill（本地路径或 GitHub URL）
askill install /path/to/skill-folder
askill install https://github.com/user/repo/tree/main/my-skill

# 从所有产品移除 skill
askill remove my-skill

# 为 DuMate 打包 skill 为 .zip
askill pack my-skill

# 列出所有支持的产品
askill products
```

### 典型工作流

```
1. askill status         ← 检查各产品安装情况
2. 编辑 ~/.agents/skills/my-skill/SKILL.md
3. askill sync my-skill  ← 一键分发到 8 个产品
4. askill pack my-skill  ← 为 DuMate 生成 .zip
```

## 项目结构

```
agent-skill-manager/
├── pyproject.toml              # PEP 621 项目配置
├── setup.py                    # setuptools 兼容入口
├── docs/
│   ├── architecture.svg        # 架构图
│   └── product-paths.md        # 各产品详细路径参考
├── src/agent_skill_manager/
│   ├── cli.py                  # CLI 命令（7 commands）
│   ├── core.py                 # 核心逻辑（sync/install/remove/pack）
│   ├── products.py             # 9 个产品定义
│   └── utils.py                # 跨平台文件操作
└── tests/                      # 34 个测试
    ├── test_products.py
    ├── test_utils.py
    └── test_core.py
```

## 二次开发

### 添加新产品

编辑 `src/agent_skill_manager/products.py`，在 `PRODUCTS` 列表中添加：

```python
{
    "name": "新产品名称",
    "short": "short-name",
    "macos_path": HOME / ".newproduct" / "skills",
    "windows_path": HOME / ".newproduct" / "skills",
    "sync_method": "symlink",  # symlink | native | pack
    "note": "说明信息",
    "extra_dirs_macos": [],
    "extra_dirs_windows": [],
}
```

### 运行测试

```bash
pip install pytest
pytest tests/ -v
```

## 相关项目

- [manage-my-skills](https://github.com/hchcx/manage-my-skills) — 跨平台 Skills 管理工具，支持 20+ 国际产品
- [awesome-agent-skills](https://github.com/libukai/awesome-agent-skills) — Agent Skills 终极指南
- [skills CLI](https://www.npmjs.com/package/skills) — npm 上的 agent skills 包管理器
- [skill-creator](https://github.com/yxdwind/agent-skill-manager) — Skill 编写规范参考

## 许可证

[MIT](LICENSE)
