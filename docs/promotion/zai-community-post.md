# Z.ai 社区 / AutoClaw 用户群 发帖文案

> 两个版本：社区长帖（论坛/社区发帖）+ 群聊短版（微信群/QQ群）。
> 发布位置建议：智谱 Z.ai 开发者社区（chatglm.cn / bigmodel.cn 社区板块）、AutoClaw 官方用户群、LINUX DO 相关讨论帖。

---

## 版本 A：社区长帖（论坛用）

**标题**：给 AutoClaw 写的 skill，一条命令同步到其他 10 个 AI Agent——开源求反馈

用 AutoClaw 写 skill 的朋友应该都遇到过：**每个 AI Agent 的 skill 目录都不一样**。我在 AutoClaw 写了个调股票数据的 skill，想在 Kimi 里也用，就得手动复制到 `~/.config/agents/skills/`；改一版，再复制一遍。skill 越攒越多，哪份是最新版都分不清。

所以我做了一个开源 CLI：**agent-skill-manager**（命令 `askill`），思路是中央仓库 + 一键分发：

- `~/.agents/skills/` 作为唯一权威源
- `askill sync` 一条命令，把 skill 用 junction/symlink（不是复制）分发到所有产品——中央改一处，11 个端立即可见
- `askill install --sync <github-url>` 直接从 GitHub 装 skill，装完自动同步
- `askill adopt autoclaw xxx` 把某个产品里调好的 skill 收编进中央仓库
- 内置 `askill audit` 安全评测：提示注入 / 危险代码（curl|sh、exec）/ 敏感信息外发 / 二进制文件，A-F 评分——skill 本质是给 AI 的指令和脚本，装前扫一下很重要
- Windows 用 junction（不用管理员权限），macOS 用 symlink，失败自动降级复制
- 已支持 11 个产品：**AutoClaw、Kimi、MiniMax Code、WorkBuddy、Trae、DuMate、CodeBuddy、Comate、Qoder、QwenWork（千问办公）、DoubaoWork（豆包工作）**

安装：

```bash
pip install -e .   # PyPI 版（pip install askill）即将上线
git clone https://github.com/yxdwind/agent-skill-manager && cd agent-skill-manager && pip install -e .
```

项目与智谱 GLM-5.2 结对开发，GitHub Actions 三平台 CI，76 个测试，MIT 开源。

仓库：**https://github.com/yxdwind/agent-skill-manager**

特别想听 AutoClaw 用户的反馈：你们的 skill 目录里现在躺了几个 skill？sync 的时候有没有遇到异常情况？有产品想让我优先适配的也可以提。

---

## 版本 B：群聊短版（100 字内）

分享个自研开源小工具：写 AutoClaw skill 的朋友如果同时用 Kimi/Trae/Qoder 这些，可以试试 agent-skill-manager（`askill`）——`~/.agents/skills/` 当中央仓库，`askill sync` 一条命令 junction 同步到 11 个国产 AI Agent，改一处全端生效。还带个 skill 安全评测（防止装到提示注入/危险脚本的坏 skill）。开源 MIT：https://github.com/yxdwind/agent-skill-manager 求反馈+star 🙏

---

## 发布建议

1. 长帖先发 Z.ai 社区/论坛，配 demo 图（docs/demo.svg 截图）和 logo
2. 群聊短版在 AutoClaw 官方群发，紧跟一句"有 bug 直接群里喊我"
3. 同帖可复用： LINUX DO（项目已在 manage-my-skills 致谢区互链）、V2EX 创造者节点
4. 评论区有人问"XX 产品支持吗"——先回"已排期"，然后真的去加（每个新增产品都是一次回访流量）
