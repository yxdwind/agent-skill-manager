# 我挨个扒了 15 个国产 AI Agent 的 skills 目录（2026-11 全表）

> <!-- 发布说明：掘金首发 · 约 3000 字 · 定位是工具书型长文，吃「XX skills 目录」类搜索词 · 数据基线 v0.20.1（2026-11-03），发布前建议抽查自家在用的 2-3 家路径是否仍准 · 上一篇文章见 marketing/01-launch-juejin.md，本篇刻意不重复它的踩坑叙事，走全表+注记路线 -->

维护一个要同步到 15 端的 skill 管理工具，副产品就是被迫把每家的目录约定都摸了一遍——直到把表拉全了我才发现，全网好像一直没有一张完整的对照表。这篇把它整理成一份可以收藏的速查表——15 个产品，覆盖 Windows / macOS / Linux 三个平台，数据基线是 v0.20.1（2026-11-03），以后每适配一个新产品我都会回来更新。

## 先上全表

| # | 产品 | 公司 | macOS / Linux | Windows | 接入方式 |
|---|------|------|--------------|---------|---------|
| 1 | AutoClaw2 | 智谱 | `~/.openclaw-autoclaw/skills` | 同左 | 目录链接 |
| 2 | Kimi | 月之暗面 | `~/.config/agents/skills`（另有 `~/.kimi-code/skills`） | 同左 | 目录链接 |
| 3 | MiniMax Code | MiniMax | `~/.agents/skills` | 同左 | 原生扫描 |
| 4 | WorkBuddy | 腾讯 | `~/.workbuddy/skills` | 同左 | 目录链接 + settings 开关 |
| 5 | Trae（国际版） | 字节跳动 | `~/.trae/skills` | 同左 | 目录链接 |
| 6 | Trae CN | 字节跳动 | `~/.trae-cn/skills` | 同左 | 目录链接 |
| 7 | TRAE SOLO CN | 字节跳动 | `~/.trae-cn/skills`（与 Trae CN 共用） | 同左 | 目录链接 |
| 8 | DuMate | 百度 | 无目录（App 内 zip 导入） | 无目录 | zip 打包 |
| 9 | CodeBuddy | 腾讯 | `~/.codebuddy/skills` | 同左 | 目录链接 + settings 开关 |
| 10 | Comate / 文心快码 | 百度 | `~/.comate/skills` | 同左 | 目录链接 |
| 11 | Qoder CN | 阿里 | `~/.qoder-cn/skills` | 同左 | 目录链接 |
| 12 | Qoder CN IDE | 阿里 | `~/.qoder-cn/skills`（与 Qoder CN 共用） | 同左 | 目录链接 |
| 13 | QwenWork / 千问办公 | 阿里 | `~/.qwenworkcn/skills` | 同左 | 目录链接 + frontmatter 要求 |
| 14 | 豆包工作 DoubaoWork | 字节跳动 | `~/.super_doubao/super-doubao-runtime/workspace/.user_skills` | 见下文 | 目录链接 |
| 15 | ZCode | ZCode | `~/.zcode/skills` | 同左 | 目录链接 |

Linux 说明：带 Linux 路径的只有 6 家（AutoClaw2、Kimi、MiniMax Code、CodeBuddy、Comate、ZCode，外加 zip 打包全平台可用的 DuMate），其余 8 家桌面/IDE 产品官方没发 Linux 版，此处留空是事实陈述不是遗漏。

豆包工作的 Windows 路径单独说，因为它值得单独说：

```text
%LOCALAPPDATA%\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills
```

从产品目录往下数 7 级，中间还夹着带空格的 `User Data`。第一次顺着文档找到它的时候，像完成了限时寻宝。

## 三种接入方式，外加一个辐射面

**目录链接（13 家）**：把技能目录做成链接指向中央仓库。Windows 上必须用 junction（`mklink /J`）而不是 symlink——后者要管理员权限，一个分发给用户的 CLI 工具不能提这种要求。

**原生扫描（1 家）**：MiniMax Code 扫的就是 `~/.agents/skills/`，对它什么都不用做。

**zip 打包（1 家）**：DuMate 没有 skills 目录，技能只能在 App 内通过 zip 包导入。对它的正确姿势是 `askill pack` 打包后上传，同步输出里永远看不到它——这是预期行为不是 bug。

**辐射面**：除了 MiniMax，AutoClaw2、ZCode、CodeBuddy CLI 除了自己的目录，还额外扫描 `~/.agents/skills/`。也就是说 Agent Skills 开放规范的通用目录约定，事实上已经被国产阵营的 4 家接受了——把技能装进这个目录，四家同时生效，这也是 askill 选它做中央仓库的原因。

## 五个值得单独记的坑

### 坑一：一个目录，多个产品

Trae CN 和 TRAE SOLO CN 共用 `~/.trae-cn/skills/`，Qoder CN 和 Qoder CN IDE 共用 `~/.qoder-cn/skills/`。两家官方的 product.json 里 dataFolderName 相同，是刻意设计。坑在于：如果你给两个产品各建一次链接，同一个路径会被建两次、删两次，删技能时还会出现重复报告。处理方式是按目标路径去重，第二个产品只报告「共享目录」。

### 坑二：一个产品，多个目录

Kimi 的主目录是 `~/.config/agents/skills/`，但它还会扫描 `~/.kimi-code/skills/`。只同步主目录的话，装在副目录的技能就成了「我看得到、它看不到」的悬案。Kimi 是目前唯一声明了副目录的产品，但别赌其他家没有。

### 坑三：链接建好了，技能还是不显示

两种原因。其一是**产品要重启**：多数桌面产品只在启动时扫一次技能目录。其二是 **settings.json 开关**：WorkBuddy 和 CodeBuddy 的 `settings.json` 里有一张 `{"skills": {名字: true}}` 的开关表，链接建好但开关没开，产品就是不加载。而且这个文件经常被正在运行的 IDE 锁着（Windows 上是 WinError 5），写入会失败——所以同步工具要在最后汇总告诉你「这几个产品的技能建了链但没启用」，而不是把失败埋在某一行输出里。

### 坑四：frontmatter 各家要求不一样

最典型的是 QwenWork：SKILL.md 的 frontmatter 必须有 `name`、`version`、`description`、`description_zh` 四个字段。缺 `description_zh` 的后果是技能装上了但加载不出来，而且产品侧不报错。我的处理是在安装时就按产品声明逐项检查，缺什么装之前就说清楚。

### 坑五：旧路径还在网上流通

产品改名会留下毒药教程。Qoder 旧版用 `~/.qoderwork/skills/`，现在是 `~/.qoder-cn/skills/`；AutoClaw 第一代用 `~/.openclaw/skills/`，第二代是 `~/.openclaw-autoclaw/skills/`。搜到的旧教程如果让你往这些目录里放东西，大概率是白放。判别方法很简单：看产品当前版本实际扫描哪里，别信两年前的帖子。

## 官方文档不写时，怎么自己找

上面这张表是踩出来的，但产品会更新，你也可能遇到表外的新产品。三个办法，按成本排序：

1. **看产品安装目录里的 product.json**。桌面产品普遍带一个产品描述文件，里面的 `dataFolderName` 字段直接写着数据目录名——Trae CN 和 TRAE SOLO CN 共用目录就是这么实锤的。
2. **在配置根目录里搜 `skills` 关键词**。豆包工作那种 7 级深路径，就是这么顺着 `.doubaowork` 一层层挖出来的。
3. **装完一个技能看它去哪了**。产品自己的技能商店装一个，看文件落在哪，那个目录就是它的扫描路径。

另外提醒一个 Windows 特有的判定坑：判断某个目录是不是链接，`os.path.islink()` 对 junction 返回 False，得用 `fsutil reparsepoint query` 或者 ctypes 读属性。想用脚本批量核对自己机器上的目录状态，别在这个判断上翻车。

## 这张表是怎么保持不过时的

老实说，手维护一张表必死——产品一改名就烂。所以这张表在 askill 里不是文档，是代码：`products.py` 里 250 行声明式定义（路径、平台矩阵、frontmatter 要求、共享目录、settings 开关），外加 400 多行一致性测试锁，每次 CI 都会验证声明完整、行为和声明一致。新增产品只改一个文件，测试自动覆盖。

发现表里哪条和你的机器对不上了？两个入口：直接提 [issue](https://github.com/yxdwind/agent-skill-manager/issues/new?template=new-product-support.md)（有现成模板，填产品名和路径就行），或者自己顺手改了提 PR——路径这种事，一线用户的实测比我的推断值钱。

## 收尾

如果你同时在用两三个以上的国产 AI Agent，这张表配合工具用价值最大：

```bash
pip install cn-skill-sync
askill status    # 看你的技能散落在几端
askill sync      # 收拢到 ~/.agents/skills 并分发
```

GitHub：**yxdwind/agent-skill-manager**（MIT，零依赖，300 多个测试三平台 CI，具体数字以仓库 badge 为准）。

觉得这张表有用的话，收藏加 star，下一个产品适配时你会第一时间看到更新。
