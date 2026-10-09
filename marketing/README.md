# marketing/ — 增长与发布资产

本目录归档项目增长相关的内容资产：发布文案、模板，以及已发布技能的源副本。
早期推广文案见 [docs/promotion/](../docs/promotion/)。

## 内容索引

| 文件 | 用途 |
|------|------|
| `01-launch-juejin.md` | 首发主打文（开发故事型，约 2900 字，掘金首发） |
| `02-launch-zhihu.md` | 知乎回答版（体验切入，适配「多个 AI Agent 体验」类问题） |
| `03-launch-jike.md` | 即刻 3 连发套件（官宣 + 细节梗 + 安全视角，含评论区模板） |
| `templates/new-product-adapted.md` | 新产品适配官宣模板（每次新增产品支持后使用） |
| `skills-repo/` | [yxdwind/skills](https://github.com/yxdwind/skills) 发布仓库的源文件（README / LICENSE） |
| `skills-staging/` | `skill-doctor`、`sync-troubleshoot` 两个已发布技能的 SKILL.md 源副本 |

## 使用说明

- **发布/更新技能**：先改 `skills-staging/`，再
  `askill publish <skill> --repo yxdwind/skills --push`；
  推送后确认与线上仓库对应文件一致（blob 哈希相同即一致）。
- **发布新产品适配官宣**：用 `templates/new-product-adapted.md`，替换 `{{ }}` 占位符。
- **发布节奏建议**：长文周二发（掘金首发 → 同日即刻转发 → 知乎分题回答），
  碎片周四/周五各一条；发完把链接补进评论区置顶。
