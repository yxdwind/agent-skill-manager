# Agent Skill Manager

跨平台（macOS / Windows）统一管理国内 Agent 产品的 Skill 安装与同步。

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

## 安装

```bash
# 开发模式安装（推荐二次开发）
cd D:\pythonproject\agent-skill-manager
pip install -e .

# 如果 pip 遇到 TLS 证书问题，使用 Anaconda Python + --no-build-isolation
python -m pip install -e . --no-build-isolation
```

## 使用

```bash
# 查看所有产品的 skill 安装状态
askill status

# 将中央仓库的所有 skill 同步到所有产品
askill sync

# 同步指定 skill
askill sync my-skill

# 列出中央仓库中的所有 skill
askill list

# 安装 skill 到中央仓库
askill install /path/to/skill-folder
askill install https://github.com/user/repo/tree/main/my-skill

# 从所有产品移除指定 skill
askill remove my-skill

# 为 DuMate 打包 skill 为 .zip
askill pack my-skill

# 列出所有支持的产品
askill products

# 查看版本
askill version
```

## 项目结构

```
agent-skill-manager/
├── pyproject.toml              # 项目配置和打包元数据
├── setup.py                    # setuptools 兼容入口
├── README.md                   # 项目说明文档
├── LICENSE                     # MIT 许可证
├── .gitignore
├── docs/
│   └── product-paths.md        # 各产品详细路径参考
├── src/
│   └── agent_skill_manager/
│       ├── __init__.py         # 包初始化
│       ├── __main__.py         # python -m agent_skill_manager 入口
│       ├── cli.py              # CLI 命令解析和入口
│       ├── core.py             # 核心同步逻辑（link/copy/sync）
│       ├── products.py         # 产品定义和路径配置（9 个产品）
│       └── utils.py            # 工具函数（symlink/junction 检测等）
└── tests/
    ├── __init__.py
    ├── test_products.py        # 产品定义测试
    ├── test_utils.py           # 工具函数测试
    └── test_core.py            # 核心逻辑测试
```

## 二次开发

### 添加新产品支持

编辑 `src/agent_skill_manager/products.py`，在 `PRODUCTS` 列表中添加新产品配置：

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
cd D:\pythonproject\agent-skill-manager
set PYTHONPATH=src
pytest tests/ -v
```

当前 34 个测试全部通过。

## 设计原理

采用 **中央仓库 + 分发** 模式：

1. 所有 Skill 统一存放在 `~/.agents/skills/`（业界通用标准目录）
2. 通过 symlink（macOS）或 junction（Windows）分发到各产品的 skill 目录
3. 对不支持文件系统的产品（DuMate），打包为 .zip 供手动上传

## 许可证

MIT
