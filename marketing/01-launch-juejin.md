# 中国有 15 个 AI Agent，每个都有自己的 skills 目录

> <!-- 发布说明：首发掘金 · 约2900字 · 封面用 docs/social-preview.png，正文在「先说结论」后插 docs/demo.gif -->

我的 QwenWork 里装着 165 个技能，AutoClaw 里 122 个，Kimi、CodeBuddy、Comate 里还各有十几个。

上个月我想给「周报生成」这个技能改一行提示词，然后我数了数要动手的地方：

```text
~/.openclaw-autoclaw/skills/weekly-report/
~/.qwenworkcn/skills/weekly-report/
~/.config/agents/skills/weekly-report/     ← Kimi
~/.codebuddy/skills/weekly-report/
~/.comate/skills/weekly-report/
~/.trae-cn/skills/weekly-report/
... 还有 9 个
```

复制、粘贴、换下一个目录。改 15 次，漏掉一个，那个产品里的「我」就在用旧版技能干活。

作为工程师我忍不了这个。所以花了两个月业余时间写了 **agent-skill-manager**（命令 `askill`）：中央仓库放一份，其余全部自动同步。现在它对 15 个国产产品做了全量支持，这篇文章写写它怎么做的，以及踩过的坑。

## 先说结论

核心设计一句话：`~/.agents/skills/` 放唯一一份真身，其他所有产品目录全是指向它的链接。

```bash
pip install cn-skill-sync
askill status    # 看看你的技能散落在几端
askill sync      # 收拢到中央仓库并分发
askill watch     # 以后改一处，0.4 秒内全端同步
```

【此处插入 docs/demo.gif】

改动保存到全端同步完成，实测 0.4 秒左右。零第三方依赖，纯 Python 标准库，MIT。

## 国产产品的 skills 目录到底有多乱

做适配之前我把 15 个产品的目录约定全部摸了一遍，大概是三个流派：

**流派一：守规范。** `~/.agents/skills/` 是 Agent Skills 开放规范的目录约定。有意思的是 MiniMax Code 原生扫描的就是这个目录，对它什么都不用做，它自己就是「中央仓库」的一部分。

**流派二：各自为政。** Kimi 在 `~/.config/agents/skills/`，Trae CN 在 `~/.trae-cn/skills/`，Qoder CN 在 `~/.qoder-cn/skills/`，Comate 在 `~/.comate/skills/`……每家一个 dotdir，互不相认。

**流派三：没有文件系统。** DuMate（百度的）技能只能在 App 内通过 zip 包导入，根本没有可以链接的目录。对它只能换思路：`askill pack` 打包成 zip 让你上传。

还有几个摸底时发现的宝藏：

- **豆包工作**的技能目录在 `%LOCALAPPDATA%\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills`，从产品目录往下数 7 级。第一次顺着官方文档找到的时候有种寻宝成功的荒谬感。
- **Trae CN 和 TRAE SOLO CN 共用同一个技能目录**，Qoder CN 和 Qoder CN IDE 也共用。同步逻辑必须按目标路径去重，否则同一个链接会被建两次、删两次。
- **QwenWork 的 frontmatter 要求 `description_zh` 字段**。缺了它，技能装上了但加载不出来，而且产品侧不会告诉你原因。askill 现在会在安装时按产品检查 frontmatter，装之前就把这事拦下来。

## 为什么是 symlink / junction

思路定下来之后，关键技术选择就一个：链接怎么做。

macOS 和 Linux 都好办，`ln -s`。Windows 上有个绕不开的坑：**NTFS 的 symlink 创建需要管理员权限或开发者模式，junction 不需要**。

一个要分发给别人用的 CLI 工具，不能要求用户开管理员终端。所以 Windows 上用 `mklink /J` 建 junction：对技能目录这个场景，junction 和 symlink 行为几乎等价，还不需要任何特权。

链接创建失败时会自动降级为复制模式。有些环境处理不了链接（网盘同步盘、权限受限的公司机），复制至少保证能用。

## 最惊险的一个 bug：差点吃掉用户手动维护的技能

v0.13 之前，sync 遇到「产品目录里已存在同名目录」的处理是：删掉，建链接。

听起来没毛病？直到我想明白一种情况：你在某个产品里**手动**维护着一个技能（比如在 Trae 里直接调了提示词，还没来得及回收到中央仓库）。这时候那个目录是一个「真实目录」，内容和中央仓库已经分叉了。

一刀下去，你的修改没了。你甚至不知道发生了什么。

一个「帮你同步」的工具，最恶劣的失败模式就是静默删用户的东西。v0.13.0 加了冲突保护：目标是不带链接的真实目录、且内容和中央仓库不同 → 跳过 + 警告 + 提示用 `askill adopt` 收编回来，确认要覆盖得显式加 `--force`。

这条后来成了整个项目的设计底线：**工具永远不静默清掉用户手动维护的东西。**

## watch：把 3 秒轮询做成事件驱动

最早的 `askill watch` 是每 3 秒轮询一次目录快照、比对差异。能用，但改完保存总要等一下，而且大部分轮询是空转。

想在零依赖的前提下做文件监听，就是把三大平台的 API 各自包一遍：

- Windows：ReadDirectoryChangesW（ctypes 调用）
- Linux：inotify
- macOS：kqueue

编辑器一次保存会触发一串文件系统事件，去抖逻辑把它们合并成一次同步，只重同步真正变化的技能。事件模式下每 30 秒仍然做一次全量对账兜底，防的是队列溢出、目录被整体替换这类事件丢失的场景。原生事件不可用时自动退回轮询。

原则很简单：监听可以不先进，但不能断。

## 装别人的 skill 之前，先扫一遍

skill 不只是文档。SKILL.md 的正文会改变 agent 的行为，`scripts/` 里可能是要执行的代码。你从 GitHub 装一个陌生技能，等于把一段「会影响 AI 决策的文本」放进工作环境。安全社区已经有研究指出，仅修改 SKILL.md 的语义内容就可能操纵技能的发现与选择环节。

所以 `askill install` 默认跑一次静态安全评测：提示注入（"ignore all previous instructions" 这类）、危险代码（`curl | sh`、`shell=True`）、敏感信息（硬编码 API key、读取 `~/.ssh`）、混入的二进制文件。100 分起扣，A 到 F 评级，risky/dangerous 高亮警告。评测本身也全是标准库实现，不引入任何依赖。

装完还会按产品检查 frontmatter（就是上面说的 QwenWork 那个坑），别等装完加载不出来才排查。

## 现在到哪了

- 15 个国产产品全量支持，三种同步模式（symlink / native / pack）
- 288 个测试，GitHub Actions 三平台矩阵（ubuntu / windows / macOS）
- skills.sh 生态打通：`askill search`、`askill install owner/repo@skill`、`askill adopt` 把别的 CLI 装的技能收编进来
- `askill new` + `askill publish`：脚手架按产品要求预填 frontmatter，门禁校验后一键发布回 GitHub 生态
- MIT，零依赖，PyPI 包名 `cn-skill-sync`

下一步的优先级只有一条：**任何新的国产 agent 发布，一周内适配。** 这个产品列表自己会变长，工具跟着长。

## 最后

如果你也同时在用两三个以上的国产 AI Agent，值得花一分钟试试：

```bash
pip install cn-skill-sync
askill status    # 看看你的技能散落在几端
askill sync      # 收拢
askill watch     # 以后改一处，全同步
```

GitHub：**yxdwind/agent-skill-manager**（觉得有用的话求个 star，这对我很重要）

欢迎提 issue：你用的产品不在列表里？某个产品的路径变了？frontmatter 又加新要求了？这类一线信息对项目最有价值，也是这个工具能覆盖全的前提。
