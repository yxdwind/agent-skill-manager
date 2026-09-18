# Vibe Work 参赛提交清单（juejin.cn/vibe-work/create）

> 使用方法：在掘金创建页逐项填写时对照本清单。全部就绪后勾选。

## 一、作品信息（填表用）

| 字段 | 内容 |
|------|------|
| 作品名 | Agent Skill Manager — 11 个国产 AI Agent 的技能同步与安全评测工具 |
| 一句话简介（短） | 一条命令，管住 11 个国产 AI Agent 的 skill：中央仓库 + symlink 分发 + 安全评测 |
| 一句话简介（长） | 跨平台 CLI 工具，把散落在 AutoClaw/Kimi/Trae/Qoder/QwenWork/豆包工作等 11 个国产 AI Agent 的 skill 目录统一管理：中央仓库权威源 + junction/symlink 一键分发 + 零依赖安全评测（提示注入/危险代码/敏感信息 A-F 评分），与智谱 GLM-5.2 结对开发 |
| 仓库链接 | https://github.com/yxdwind/agent-skill-manager |
| 文章链接 | 发布后回填：https://juejin.cn/post/__________ |
| AI 工具声明 | 智谱 GLM-5.2（Z.ai）结对开发，覆盖需求设计、编码、测试、CI、文档全流程 |
| 开源协议 | MIT |
| 当前版本 | v0.7.0 |

## 二、仓库就绪状态（评委点进来看到什么）

- [x] README 中文（默认）+ 英文（README.en.md），顶部语言切换
- [x] CI 徽章（GitHub Actions 三平台矩阵，绿色）
- [x] 架构图（docs/architecture.svg）+ 终端演示图（docs/demo.svg）
- [x] Release v0.7.0（含完整更新说明）
- [x] LICENSE（MIT, Albert）+ SECURITY.md + PRIVACY.md
- [x] 76 个测试，`pytest tests` 可复现
- [ ] **待办**：文章发布后，把文章链接加进 README（回填动作）

## 三、发布步骤

1. 把本目录（docs/）的 `vibe-work-article.md` 全文复制到掘金文章编辑器
2. 文章内图片改为掘金图床上传（`demo.svg` 截图或直接上传 SVG）
3. 标签选择：`AI 编程` + `开源` + `Vibe Work`（以页面可选标签为准）
4. 添加参赛声明与仓库链接（文章结尾已含）
5. 发布后把文章 URL 回填到本清单"文章链接"与仓库 README
6. 在 create 页面提交：作品名 + 简介 + 仓库链接 + 文章链接

## 四、发布后动作

- [ ] 文章链接回填 README.md 与 README.en.md
- [ ] 掘金评论区置顶"安装三步走"
- [ ] 监控 GitHub star / clone 变化（一周后复盘）

---
*维护者：Albert ｜ 更新：2026-09-18*
