# Product Skill Paths Reference

## 各产品 Skill 目录路径详细说明

### 1. AutoClaw / OpenClaw

| 属性 | macOS | Windows |
|------|-------|---------|
| 用户级 Skill 目录 | `~/.openclaw/skills/` | `%USERPROFILE%\.openclaw\skills\` |
| AutoClaw 扩展目录 | `~/.openclaw-autoclaw/skills/` | `%USERPROFILE%\.openclaw-autoclaw\skills\` |
| 个人 Agent Skill | `~/.agents/skills/` | `%USERPROFILE%\.agents\skills\` |
| 配置文件 | `~/.openclaw/openclaw.json` | `%USERPROFILE%\.openclaw\openclaw.json` |

**加载优先级**：项目级 > 用户级 > 内置

**参考来源**：
- https://docs.openclaw.ai/zh-CN/tools/skills-config
- https://docs.openclaw.ai/tools/skills
- https://www.cnblogs.com/sing1ee/p/19685515/openclaw-skills

---

### 2. Kimi Code

| 属性 | macOS | Windows |
|------|-------|---------|
| 用户级 Skill 目录 | `~/.config/agents/skills/` | `%USERPROFILE%\.config\agents\skills\` |
| Kimi Code 专用目录 | `~/.kimi-code/skills/` | `%USERPROFILE%\.kimi-code\skills\` |
| 插件管理目录 | `$KIMI_CODE_HOME/plugins/managed/` | `$KIMI_CODE_HOME\plugins\managed\` |

**加载优先级**：项目级 > 用户级 > 内置

**Skill 文件结构**：目录形式（推荐），每个目录包含 `SKILL.md` + YAML frontmatter（name + description）

**参考来源**：
- https://www.kimi.com/code/docs/kimi-code-cli/customization/skills.html
- https://www.kimi.com/zh-cn/help/features/use-skills-in-code

---

### 3. MiniMax Code

| 属性 | macOS | Windows |
|------|-------|---------|
| Skill 目录 | `~/.agents/skills/` | `%USERPROFILE%\.agents\skills\` |

**特点**：MiniMax Code 原生支持 `~/.agents/skills/` 目录，与中央仓库路径一致，无需额外同步。

**Agent Plugins 开放标准**：MiniMax Code 支持 Agent Plugins 开放标准，可以用统一格式把 Agent Skills 和 MCP server 设定打包成 plugin。

**参考来源**：
- https://github.com/MiniMax-AI/skills
- https://github.com/MiniMax-AI/Mini-Agent

---

### 4. WorkBuddy

| 属性 | macOS | Windows |
|------|-------|---------|
| Skill 目录 | `~/.workbuddy/skills/` | `%USERPROFILE%\.workbuddy\skills\` |
| 配置文件 | `~/.workbuddy/settings.json` | `%USERPROFILE%\.workbuddy\settings.json` |
| 应用数据目录 | `~/Library/Application Support/WorkBuddy/` | `%APPDATA%\WorkBuddy\` |

**安装方式**：
1. 将 skill 目录复制/链接到 `~/.workbuddy/skills/`
2. 修改 `settings.json`，将对应 skill 名称设置为 `true` 以启用

**settings.json 示例**：
```json
{
  "skills": {
    "my-skill": true,
    "another-skill": true
  }
}
```

**参考来源**：
- https://www.cnblogs.com/aquester/p/19714884
- https://cloud.tencent.com/developer/article/2672840
- https://segmentfault.com/a/1190000048110145

---

### 5. Trae Solo

| 属性 | macOS | Windows |
|------|-------|---------|
| 用户级 Skill 目录 | `~/.trae/skills/` | `%USERPROFILE%\.trae\skills\` |
| 项目级 Skill 目录 | `<project>/.trae/skills/` | `<project>\.trae\skills\` |
| 通用项目级目录 | `<project>/.agents/skills/` | `<project>\.agents\skills\` |

**Skill 文件结构**：目录形式，每个目录包含 `SKILL.md`

**安装方式**：
1. 使用 `skills` 命令安装
2. 使用 `openskills` 命令安装
3. 手动安装（将目录复制到 skill 目录）
4. 使用 SOLO Coder 模式让 AI 创建 Skills

**参考来源**：
- https://docs.trae.ai/ide/skills?_lang=zh
- https://docs.trae.ai/solo/skills?_lang=en
- https://segmentfault.com/a/1190000047588334
- https://www.cnblogs.com/jzssuanfa/p/19620447

---

### 6. DuMate（百度搭子）

| 属性 | macOS | Windows |
|------|-------|---------|
| Skill 管理 | App 内管理 | App 内管理 |
| 官网 | https://www.dumate.cn | https://www.dumate.cn |
| Windows Store | - | Microsoft Store |

**安装方式**：
1. 打开 DuMate App
2. 进入「技能」页面
3. 点击右上角「安装技能」
4. 支持 URL 导入或上传 `.zip` / `.md` 格式文件

**Skill 开发结构**：
- 最小结构：一个包含 `SKILL.md` 的目录
- `SKILL.md` 包含 YAML frontmatter（元数据）+ Markdown 正文（指令）
- 支持子目录包含脚本、引用和资源文件

**打包格式**：使用 `python skill_sync.py pack <skill-name>` 生成 `.zip` 文件

**参考来源**：
- https://cloud.baidu.com/doc/Dumate/s/5mmydgic3
- https://cloud.baidu.com/discover/skill-dev-topic-2.html
- https://cloud.baidu.com/discover/dumate-skill-overview-dev.html
- https://apps.microsoft.com/detail/xp8btb6c1msxfx

---

## 通用标准：`.agents/skills/`

业界逐渐形成通用约定，越来越多兼容客户端会扫描以下路径：

- **项目级**：`<project>/.agents/skills/<skill-name>/`
- **用户级**：`~/.agents/skills/<skill-name>/`

这是本工具选择 `~/.agents/skills/` 作为中央仓库的原因。

**参考来源**：
- https://github.com/libukai/awesome-agent-skills
- https://developer.cloud.tencent.com/article/2695248
- https://www.cnblogs.com/know-data/p/22137667

---

## 交叉参考：其他管理工具

### manage-my-skills
- 项目地址：https://github.com/hchcx/manage-my-skills
- 支持 Windows & macOS
- 支持 Claude Code, Cursor, Windsurf, Zed, Trae, Codex 等 20+ 工具
- 使用 symlink/copy 两种同步方式
- 本工具借鉴了其设计思路，但专注国内产品

### skills CLI (npx skills)
- 包地址：https://www.npmjs.com/package/skills
- 支持 OpenCode, Claude Code, Codex, Cursor 等 72+ 客户端
- 可与本工具配合使用
