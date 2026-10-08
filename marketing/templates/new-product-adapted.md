# 新产品适配官宣模板

> 用法：每次新增产品支持后，Day 6–7 使用。`{{ }}` 为占位符。
> 掘金短文直接发布；即刻帖发「一起做产品」「AI 探索站」圈。

## 掘金短文（600–900 字）

# {{产品名}} 用户的 skill 管理方案来了：askill 已支持（第 {{N}} 端）

[一两句产品背景：谁家的、什么形态、什么时候发布。]

{{产品名}} 的技能存放在 `{{路径}}`，{{一句话机制说明：symlink 直链 / 原生扫描 central / zip 导入}}。

现在 agent-skill-manager（`pip install cn-skill-sync`）已完整支持：中央仓库改一处，{{产品名}} 自动同步，和其余 {{N-1}} 个国产 AI Agent 一起管理。

```bash
pip install cn-skill-sync   # 升级到 v{{版本}}
askill sync                 # {{产品名}} 的技能一次性收拢并分发
askill watch                # 以后改完保存，全端自动同步
```

{{如有特殊适配点，写一段：frontmatter 要求 / 共享目录 / settings 开关等，这是搜索流量的关键词位}}

适配清单已到 {{N}} 个产品：{{追加的产品名高亮，其余列 short 名}}。

你的产品不在列表里？[提个 issue](https://github.com/yxdwind/agent-skill-manager/issues/new?template=new-product-support.md)，目标一周内支持。

---

GitHub：yxdwind/agent-skill-manager ｜ MIT ｜ 零依赖 ｜ 三平台 CI

## 即刻帖（120 字内）

{{产品名}} 用户看过来👀

askill 现在支持 {{产品名}} 了，第 {{N}} 端。

装一次 cn-skill-sync，所有国产 AI Agent 的 skill 一起管：改一处，全端同步。

不支持的产品的？issue 区见，一周内安排。

#AI编程 #AgentSkills
