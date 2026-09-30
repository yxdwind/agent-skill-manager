# Product Skill Paths Reference

## 各产品 Skill 目录路径详细说明

### 1. AutoClaw2

| 属性 | macOS | Windows |
|------|-------|---------|
| 用户级 Skill 目录 | `~/.openclaw-autoclaw/skills/` | `%USERPROFILE%\.openclaw-autoclaw\skills\` |
| 个人 Agent Skill | `~/.agents/skills/` | `%USERPROFILE%\.agents\skills\` |
| 配置根目录 | `~/.openclaw-autoclaw/` | `%USERPROFILE%\.openclaw-autoclaw\` |

AutoClaw2（智谱，bundleId `com.zhipuai.autoclaw2`）的 profile root 为 `~/.openclaw-autoclaw/`，
并原生扫描 `~/.agents/skills/`。旧版 v1 的路径 `~/.openclaw/skills/` 已废弃。

**加载优先级**：项目级 > 用户级 > 内置

---

### 2. Kimi

| 属性 | macOS | Windows |
|------|-------|---------|
| 用户级 Skill 目录 | `~/.config/agents/skills/` | `%USERPROFILE%\.config\agents\skills\` |
| Kimi 专用目录 | `~/.kimi-code/skills/` | `%USERPROFILE%\.kimi-code\skills\` |

---

### 3. MiniMax Code

| 属性 | macOS | Windows |
|------|-------|---------|
| Skill 目录 | `~/.agents/skills/` | `%USERPROFILE%\.agents\skills\` |

原生支持，无需额外同步。

---

### 4. WorkBuddy

| 属性 | macOS | Windows |
|------|-------|---------|
| Skill 目录 | `~/.workbuddy/skills/` | `%USERPROFILE%\.workbuddy\skills\` |
| 配置文件 | `~/.workbuddy/settings.json` | `%USERPROFILE%\.workbuddy\settings.json` |

settings.json: `{"skills": {"my-skill": true}}`

---

### 5. Trae

| 属性 | macOS | Windows |
|------|-------|---------|
| 用户级 | `~/.trae/skills/` | `%USERPROFILE%\.trae\skills\` |
| 项目级 | `<project>/.trae/skills/` | `<project>\.trae\skills\` |

国际版 Trae 使用 `~/.trae/`；国内版见下一节 Trae CN。

---

### 6. Trae CN

| 属性 | macOS | Windows |
|------|-------|---------|
| 用户级 | `~/.trae-cn/skills/` | `%USERPROFILE%\.trae-cn\skills\` |
| 项目级 | `<project>/.trae-cn/skills/` | `<project>\.trae-cn\skills\` |

Trae CN（字节跳动国内版）的 dataFolderName 为 `.trae-cn`（经 product.json 实证）。

---

### 7. TRAE SOLO CN

| 属性 | macOS | Windows |
|------|-------|---------|
| 用户级 | `~/.trae-cn/skills/` | `%USERPROFILE%\.trae-cn\skills\` |

TRAE SOLO CN 与 Trae CN 共用数据目录 `~/.trae-cn/`（product.json 中 dataFolderName 相同），
因此 Skill 目录也相同。

---

### 8. DuMate (Baidu)

App 内管理：技能 → 安装技能 → 上传 .zip/.md

官网: https://www.dumate.cn

---

### 9. CodeBuddy (Tencent)

| 属性 | macOS | Windows |
|------|-------|---------|
| 用户级 Skill 目录 | `~/.codebuddy/skills/` | `%USERPROFILE%\.codebuddy\skills\` |
| 配置文件 | `~/.codebuddy/settings.json` | `%USERPROFILE%\.codebuddy\settings.json` |

CodeBuddy CLI 也扫描 `~/.agents/skills/`。每个 Skill 一个独立目录，包含 `SKILL.md`。
**参考来源**：
- https://www.cnblogs.com/yangykaifa/p/19681812
- https://www.codebuddy.cn/docs/cli/skills

---

### 10. Comate / 文心快码 (Baidu)

| 属性 | macOS | Windows |
|------|-------|---------|
| Skill 目录 | `~/.comate/skills/` | `%USERPROFILE%\.comate\skills\` |

Comate 启动时自动从 `~/.comate/skills/` 发现并加载 Skills。内置 `create-rule`、`create-skill`、`create-subagent` 三个系统级 Skill 也在该目录。
**参考来源**：
- https://cloud.baidu.com/doc/COMATE/s/Nmma28iqe
- https://segmentfault.com/a/1190000047679474

---

### 11. Qoder CN

| 属性 | macOS | Windows |
|------|-------|---------|
| Skill 目录 | `~/.qoder-cn/skills/` | `%USERPROFILE%\.qoder-cn\skills\` |

Qoder CN 桌面端把 Skill 存放在 `~/.qoder-cn/skills/` 目录下（经本机数据目录实证）。
旧版 QoderWork 路径 `~/.qoderwork/skills/` 已废弃。
**参考来源**：
- https://docs.qoder.com/zh/qoderwork/skills
- https://help.aliyun.com/zh/lingma/qoder-cn/user-guide/skills

---

### 12. Qoder CN IDE

| 属性 | macOS | Windows |
|------|-------|---------|
| Skill 目录 | `~/.qoder-cn/skills/` | `%USERPROFILE%\.qoder-cn\skills\` |

Qoder CN IDE（VSCode 系）的 dataFolderName 为 `.qoder-cn`（经 product.json 实证），
与 Qoder CN 桌面端共用同一 Skill 目录。

---

### 13. QwenWork / 千问办公 (Alibaba)

| 属性 | macOS | Windows |
|------|-------|---------|
| Skill 目录 | `~/.qwenworkcn/skills/` | `%USERPROFILE%\.qwenworkcn\skills\` |

QwenWork 桌面端从 `~/.qwenworkcn/skills/` 自动发现技能，每个 Skill 是包含 `SKILL.md` 的独立文件夹。
frontmatter 需要 `name` + `version` + `description` + `description_zh` 字段。
**参考来源**：
- https://help.aliyun.com/zh/qwenwork/skills
- https://www.aliyun.com/product/qwenwork

---

### 14. DoubaoWork / 豆包工作 (ByteDance)

| 属性 | macOS | Windows |
|------|-------|---------|
| 用户 Skill 目录 | `~/.super_doubao/super-doubao-runtime/workspace/.user_skills/` | `%LOCALAPPDATA%\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\` |
| 系统 Skill 目录 | `~/.super_doubao/super-doubao-runtime/workspace/.skills/` | `%LOCALAPPDATA%\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.skills\` |

豆包工作（豆包专业版）通过 super-doubao runtime 加载技能：系统内置技能在 `.skills/`，
用户自定义技能放在 `.user_skills/`（与系统技能隔离，避免升级时被覆盖）。
**参考来源**：
- https://www.doubao.com/work
- https://www.luomor.com/blog/2026/08/14/豆包新工作任务

---

### 15. ZCode

| 属性 | macOS | Windows |
|------|-------|---------|
| 用户级 Skill 目录 | `~/.zcode/skills/` | `%USERPROFILE%\.zcode\skills\` |
| 个人 Agent Skill | `~/.agents/skills/` | `%USERPROFILE%\.agents\skills\` |

ZCode 同时扫描 `~/.zcode/skills/` 与 `~/.agents/skills/`（经本机实测确认）。

---

## 通用标准：`.agents/skills/`

业界通用约定，越来越多客户端扫描以下路径：
- **项目级**：`<project>/.agents/skills/<skill-name>/`
- **用户级**：`~/.agents/skills/<skill-name>/`

## Linux 支持（v0.10.0）

仅发布过 Linux 版本（或目录约定与平台无关）的 CLI 类产品提供 `linux_path`，与 macOS 走相同的 dotdir 约定 + 原生 symlink：

| 产品 | Linux 目录 | 说明 |
|------|-----------|------|
| AutoClaw2 | `~/.openclaw-autoclaw/skills/` | OpenClaw 系 CLI，跨平台同路径 |
| Kimi | `~/.config/agents/skills/`（另扫 `~/.kimi-code/skills/`） | XDG 约定 |
| MiniMax Code | `~/.agents/skills/` | 原生支持，无需同步 |
| CodeBuddy | `~/.codebuddy/skills/` | CLI 跨平台 |
| Comate | `~/.comate/skills/` | CLI 跨平台 |
| ZCode | `~/.zcode/skills/` | CLI 跨平台 |
| DuMate | —（`pack` 命令的 .zip 打包全平台可用） | App 内管理 |

其余产品（Trae / Trae CN / TRAE SOLO CN、WorkBuddy、Qoder CN / Qoder CN IDE、QwenWork、DoubaoWork）暂无 Linux 版本：Linux 上 `linux_path` 为 `None`，askill 自动跳过，`askill products` 显示 N/A。产品发布 Linux 版后，在 `src/config/products.py` 补充 `linux_path`（附实证来源）即可。

## 交叉参考
### manage-my-skills
- https://github.com/hchcx/manage-my-skills

### skills CLI (npx skills)
- https://www.npmjs.com/package/skills
