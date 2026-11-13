# 即刻碎片 · 注意力预算（配合第 4 篇，周二发长文后当日转发）

## 主碎片（约 280 字）

给自己的 30 个 agent 技能算了笔账：description 常驻成本约 2166 token，agent 每条消息都在付这笔房租，不管用不用这些技能。

更扎心的是发现中文技能更贵：token 估算里中文 1 字 = 1 token，英文约 4 字符 = 1 token。一个 219 字的中文 description 顶一个 1014 字符的英文 description（185 vs 253 token）。中文写 description 每个字都在实打实烧上下文。

做了个排行命令（借鉴 asm 的 attention budget 概念）：30 个技能里 2 个超长要精简、12 个太短会失灵——贵的在烧钱，短的在失灵，两头都得修。

长文已发掘金（链接见评论），命令一行：askill audit --residency

## 短碎片（跟评用）

「200k 窗口还差这两千 token？」——差的是除法：200 条消息的会话，每条消息摊到的预算只有 1000 级。常驻成本要按每条消息重复支付来算。

## 数据锚点（评论区置顶）

- 长文：掘金《我给 30 个 agent 技能算了笔账：每条消息都在交房租》
- 本机实跑数据：30 技能 / 2166 token / 2 超长 / 12 过短
- 命令：askill audit --residency（--json 给脚本用）
- 上篇对标文 + 仓库：github.com/yxdwind/agent-skill-manager
