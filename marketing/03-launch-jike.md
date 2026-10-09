# 即刻发布套件

<!-- 即刻节奏：周二长文转发引流 + 周四/周五各一条碎片。以下 3 条按发布顺序排。发「一起做产品」/「AI 探索站」/「独立开发者」相关圈子，正文短、多换行、别用 Markdown 表格。 -->

---

<!-- 帖 1 · 周二，长文发布当天 -->

做了两个月的东西今天开源了。

事情起因特别简单：我的 QwenWork 里装了 165 个 skill，AutoClaw 里 122 个，每次改一行提示词，要手动复制粘贴到 15 个产品的目录里。

漏一个，那个产品里的 AI 就在用旧版技能干活，而且我不会发现。

忍不了，写了个工具：agent-skill-manager

一个中央仓库，15 个国产 AI Agent 全部自动同步。改完保存 0.4 秒全端生效。

GitHub 搜 yxdwind/agent-skill-manager，或者 pip install cn-skill-sync

写了一篇完整的踩坑记录，链接在评论区👇

（配图：docs/demo.gif）

---

<!-- 帖 2 · 周四，碎片·细节梗 -->

适配国产 AI Agent 的 skills 目录有多离谱：

豆包工作的技能目录：%LOCALAPPDATA%\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills

从产品目录往下数，7 级。顺着官方文档找到的那一刻，像完成了限时寻宝🏢

---

<!-- 帖 3 · 周五，碎片·安全视角 -->

提醒：从网上装 skill 之前最好先扫一遍。

skill 不是普通文档，它的正文会直接改变 AI 的行为，scripts/ 里可能是要执行的代码。安全社区已经有研究：光改 SKILL.md 的语义内容，就可能操纵技能的发现和选择。

我给 agent-skill-manager 内置了安装前的静态安全评测：提示注入、curl|sh 这类危险命令、硬编码 API key、混进来的 exe，都能拦下来。纯标准库实现，装个工具不引入一堆依赖。

技能生态越繁荣，这一步越不能省。

---

<!-- 评论区置顶（发帖后自己补） -->

完整文章（掘金）：[长文链接]
GitHub：https://github.com/yxdwind/agent-skill-manager
pip install cn-skill-sync ｜ MIT ｜ 零依赖 ｜ 288 tests

产品没覆盖到的、路径变了的，issue 随时提，这个项目最需要的就是一线反馈。
