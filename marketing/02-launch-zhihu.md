# 知乎版：「同时用多个国产 AI Agent 是什么体验？」

<!-- 定位：知乎问题下回答体。目标问题：「同时使用多个 AI 编程助手/Agent 是什么体验」「有哪些值得推荐的开发效率工具」。与掘金版差异：以「体验」切入而不是以「工具」切入，前 300 字全是共鸣，工具只是答案的载体。 -->

同时用 5 个国产 AI Agent 干活是什么体验？

体验就是：我给「周报生成」这个 skill 改了一行提示词，然后花了 20 分钟做搬运工——Kimi 的目录粘一遍，CodeBuddy 的粘一遍，Comate 的粘一遍，Trae CN 的粘一遍……

漏一个，那个产品里的 AI 就在用旧版技能给我干活。而且我不会发现，直到某天它产出的东西不对劲。

这不是段子。国产 AI Agent 这两年爆发，每家都做了自己的 skill 体系（这点要肯定，skill 确实是让 agent 干专业活的好东西），但目录约定互不相认：

- Kimi：`~/.config/agents/skills/`
- Trae CN：`~/.trae-cn/skills/`
- CodeBuddy：`~/.codebuddy/skills/`
- QwenWork：`~/.qwenworkcn/skills/`
- ……

我的 QwenWork 里装了 165 个技能。可以想象手动同步是什么地狱。

## 我的解法

我的第一反应是工程上的老思路：中央仓库 + 分发。`~/.agents/skills/` 放一份真身，其他全是链接，改一处全生效。

把这个思路做成了开源工具 **agent-skill-manager**（`pip install cn-skill-sync`），两个月迭代下来：

- 15 个国产产品全量支持，AutoClaw / Kimi / MiniMax / WorkBuddy / Trae / DuMate / CodeBuddy / Comate / Qoder / QwenWork / 豆包工作 / ZCode 都在
- `askill watch` 事件驱动监听，保存后约 0.4 秒全端同步（Windows 用 junction 不需要管理员权限，链接失败自动降级复制）
- 装别人的 skill 前自动跑安全评测：提示注入、危险代码、硬编码密钥都能扫出来
- 从 GitHub / skills.sh 一条命令装：`askill install owner/repo@skill`

## 两个印象深的坑

**豆包工作的技能目录藏在 7 级目录深处**：`%LOCALAPPDATA%\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills`。顺着官方文档找到的那一刻，像完成了限时寻宝。

**DuMate 没有 skills 目录**，技能只能 App 内 zip 导入。对这种产品只能换模式：`askill pack` 打包。一个工具支持 15 个产品，注定不是 15 次复制粘贴的逻辑，而是 15 种适配模式的编排。

## 值不值

现在我改 skill 就是：改文件 → 保存 → 0.4 秒后 15 个产品同时是新版本。回不去手动同步的时代了。

GitHub 搜 **yxdwind/agent-skill-manager**，MIT 开源，纯 Python 标准库零依赖，288 个测试三平台 CI。觉得有用点个 star，也欢迎在 issue 里告诉我你用的产品没被覆盖，这就是这个项目最需要的输入。

---

*利益相关：作者本人。写出来是因为真被这个问题折磨够了，分享给同样被折磨的人。*
