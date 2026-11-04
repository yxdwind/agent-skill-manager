# 即刻发布套件 — 目录全表篇

<!-- 发布说明：周二长文发布当天发帖 1，周五发帖子 2；长文链接出来后评论区置顶补链接。发「一起做产品」「AI 探索站」圈。 -->

<!-- 帖 1 · 周二，长文发布当天 -->

把 15 个国产 AI Agent 的 skills 目录挨个扒了一遍，整理成一张全表，Windows/macOS 都在。

几个最有画面感的：

豆包工作的技能目录藏了 7 级，中间还带空格：User Data\Default\.doubaowork\agent_mode\workspace\.user_skills

Trae CN 和 TRAE SOLO CN 共用同一个目录，Qoder CN 和它的 IDE 版也共用——一个目录两个产品。

Kimi 有两个技能目录（~/.config/agents/skills 和 ~/.kimi-code/skills），只同步主目录的话副目录的技能就是悬案。

MiniMax 直接扫 ~/.agents/skills，加上 AutoClaw2、ZCode、CodeBuddy 也双扫——开放规范的目录约定，国产阵营其实已经接受一半了。

全表在这篇文章里，收藏向👇（评论区放链接）

（配图：docs/social-preview.png）

---

<!-- 帖 2 · 周五，碎片·改名坑 -->

提醒一个搜教程时的坑：国产 AI Agent 改名会留下毒药路径。

Qoder 旧版技能目录是 ~/.qoderwork/skills，现在是 ~/.qoder-cn/skills；AutoClaw 一代是 ~/.openclaw，二代是 ~/.openclaw-autoclaw。

搜到的旧教程让你往旧路径放东西，大概率白放。判别方法：看当前版本实际扫描哪里，别信年前的帖子。

顺手把 15 家的现行目录全表更新进了这篇文章（评论区链接），以后改名我会跟着更新。

#AI编程 #AgentSkills
