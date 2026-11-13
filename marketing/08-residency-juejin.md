# 我给 30 个 agent 技能算了笔账：每条消息都在交房租

> 首发：掘金 · agent-skill-manager 系列 第 4 篇 · 计划周二发布
> 数据口径：本机中央仓库实跑 `askill audit --residency`，2026-11-13 快照；token 数是启发式估算，用于排行不做计费。

## 一、一条消息的隐藏成本

先说结论：我的中央仓库里躺着 30 个 agent 技能，它们全部加载时的 description 常驻成本约为 **2166 token**。也就是说，agent 每一条消息的系统提示词里，都躺着这两千多个 token——不管这条消息用不用到这些技能。

100 条消息的会话，就是 20 万 token 的「房租」。而其中相当一部分，是我在为根本不会触发的技能付的。

这个概念的出处是 [luongnv89/asm](https://github.com/luongnv89/asm) 的 README，它管这叫 attention budget（注意力预算）：磁盘便宜，上下文不便宜。每个技能的 frontmatter description 都会进 agent 的系统提示词，每条消息、每次对话、不管用不用。装技能的时候人人爽快，装完没人再看过一眼成本。

我在[上一篇对标文](https://github.com/yxdwind/agent-skill-manager)里把这个机制借了过来，做成了 `askill audit --residency`。

## 二、中文技能更贵，这是个被忽视的事实

写完才发现一个对中文用户特别扎心的细节：**token 估算里 CJK 字符按 1 字 1 token 计，其他文字约 4 字符 1 token**。中文 description 的单位成本是英文的 4 倍。

实跑数据里最直观的对比：

| 技能 | description 字符数 | 估算 token |
|------|---:|---:|
| microsoft-foundry（英文） | 1014 | 253 |
| english_memory_method（中文） | 219 | 185 |

前者字符数是后者的 4.6 倍，token 只差 36%。因为后者是纯中文。**中文技能写 description，每多一个字都在实打实地烧上下文**——而我们写中文往往比写英文更啰嗦。

## 三、排行榜长什么样

`askill audit --residency` 的输出（本机 30 技能，截取头部）：

```
skill              desc   ~tok  lines    kb  suggestion
microsoft-foundry  1014    253    186   540.1  consider trimming
english_memory_method 219  185    143    21.2  ok
archify             652    163    121  5889.3  consider trimming
daily-speak         212    161    114     7.9  ok
...
```

三列信息：字符数（口径）、估算 token（排序键）、目录体积。建议列分四档：超规范上限（必须精简）、偏长（consider trimming）、正常、太短（弱触发，反向问题——description 太短 agent 根本想不起来用它）。

我的 30 个技能里：2 个建议精简（microsoft-foundry 的 1014 字符 description 是我当初无脑粘贴产品文档的结果），**12 个太短**。两头都有问题：贵的在烧钱，短的在失灵。

## 四、为什么这不是雕花

有人会说：2166 token 才多大点上下文，现代模型 200k 窗口，犯得着吗？

三个理由：

1. **它是每条消息重复支付的**。200k 窗口除以 200 条消息的会话，每条消息的可用预算其实只有 1000 token 级别，2000 多 token 的技能常驻就是双倍开销。
2. **技能库只增不减**。技能装的顺手删的少，三个月后这个数字只会长。没有度量就没有治理。
3. **真正的成本在信噪比**。常驻描述里塞满与当前任务无关的触发词，是在稀释 agent 对真正相关技能的注意力。

## 五、怎么用

一条命令，零配置，纯静态读取不联网：

```bash
askill audit --residency          # 人读的排行表
askill audit --residency --json   # 喂给脚本或 agent
```

处置路径：偏长的精简 description（中文尤其值得）；太短的补触发词；装了不用的直接 `askill remove`。精简前后可以各跑一次对比总量变化。

## 六、诚实备注

token 估算是启发式（CJK 1:1、其他 1:4），不同模型的 tokenizer 有差异，数字用于排行和趋势，不做计费依据。仓库 300 多个测试（准确数以 README badge 为准）。这个机制借鉴自 asm 的 residency audit，实现是自己的，链接在文末。

---

仓库：https://github.com/yxdwind/agent-skill-manager （`pip install cn-skill-sync`）
上篇：对标拆解文（marketing/06，已发掘金与知乎）
对标来源：https://github.com/luongnv89/asm
