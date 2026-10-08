# 新产品适配 SOP（适配 SLA：发布后 1 周内支持）

> 目标：任何新的国产 AI Agent 产品发布后，**7 天内**进入 askill 支持列表并官宣。
> 本文档是把适配时间压到一周的流程资产。按步骤走，不需要重新发明。

## 为什么 SLA 值得投入

每新增一个产品 = 新增一个搜索入口（"XX skills 目录"）+ 一批新用户的自然到达 +
一篇官宣内容的由头。15 端会自己长成 25 端，工具跟着生态长，这就是本项目的复利杠杆。

## Day 0：发现与建档（当天）

1. 从任一渠道确认新产品发布：官方文档 / 用户 issue（用下面的 issue 模板）/ 社区讨论
2. 建档，回答四个问题：
   - **skills 目录路径**：macOS / Windows / Linux 各自在哪？（读官方文档 + product.json / 安装目录实测）
   - **同步方式**：能 symlink/junction？原生扫 central？还是只能 zip（pack 模式）？
   - **frontmatter 特殊要求**：有没有额外必填字段（参照 QwenWork 的 `description_zh`）？
   - **settings.json 开关**：技能要不要在 settings 里登记启用？（参照 WorkBuddy/CodeBuddy 的 `{"skills": {name: bool}}`）
3. 用户 issue 里已有部分答案的，直接引用；缺的字段补测或在 issue 里追问

## Day 1–2：声明式接入（只改 products.py + 测试）

接入是**声明式**的，正常情况下只动一个文件：

```python
# src/config/products.py — PRODUCTS 列表追加：
{
    "name": "新产品名",
    "short": "newprod",
    "macos_path": HOME / ".newprod" / "skills",
    "windows_path": HOME / ".newprod" / "skills",
    "linux_path": HOME / ".newprod" / "skills",   # 无 Linux 版则省略
    "sync_method": "symlink",                      # symlink | native | pack
    # 按需：
    # "settings_file": HOME / ".newprod" / "settings.json",
    # "settings_mode": "skills-switch",
    # "required_frontmatter": ["name", "version", "description_zh"],
    # "extra_dirs_macos": [], "extra_dirs_windows": [], "extra_dirs_linux": [],
    # "note": "共享目录等特殊情况说明",
}
```

然后：

1. `pytest tests/test_matrix.py -q` —— 一致性断言自动覆盖新产品（声明不全这里会红）
2. 检查共享目录：新产品与现有产品共用技能目录时，确认输出去重逻辑覆盖（参照 traecn/traesolo 先例）
3. `ruff check src tests` + `mypy src` + `pytest tests -q` 三件套全绿

## Day 3–4：实测与文档

1. **至少一台真机实测**（Windows 优先——junction 行为最特殊）：`askill sync` / `status` / `remove` 各跑一遍，确认链接生效、产品能加载技能
2. 更新三处文档：
   - `README.md` / `README.en.md` 支持矩阵加行（徽章数 15→16 记得同步，grep 旧数字）
   - `docs/product-paths.md` 加路径参考
   - `docs/product-matrix.md` 能力矩阵加行
3. `completion/` 补全脚本无需改（从 `products --json` 实时拉取）

## Day 5：发布

1. Conventional Commits：`feat(products): add <NewProduct> support`
2. `cz bump`（minor）→ push → GitHub Release 自动或手动创建
3. `pip publish` 或 `python -m build` + `twine upload` 发新版到 PyPI

## Day 6–7：官宣（见模板）

用 `marketing/templates/new-product-adapted.md` 出掘金短文 + 即刻帖，
标题打「XX 用户的 skill 管理方案来了」——对这家的用户说话，转化率最高。

## 用户提需求：issue 模板

`.github/ISSUE_TEMPLATE/new-product-support.md` 已配好，用户填了就能直接进 Day 0 建档。
宣传物料的角落可以带一句：*你的产品不在列表里？提个 issue，一周内支持。*

## 已知坑速查（历史教训）

| 坑 | 先例 | 处理 |
|----|------|------|
| Windows symlink 要管理员权限 | 全项目 | 永远用 junction（`mklink /J`） |
| 共享技能目录重复建链 | Trae CN/SOLO、Qoder CN/IDE | sync 按目标路径去重，输出单行 |
| 产品目录已有同名真实目录 | v0.13 冲突保护 | 跳过+警告，绝不静默覆盖 |
| frontmatter 缺中文字段装完加载不出 | QwenWork `description_zh` | 声明 `required_frontmatter`，装前拦截 |
| 无文件系统的产品 | DuMate | `sync_method: pack`，提示 `askill pack` |
| 深层路径带空格 | 豆包工作 7 级路径 | 声明完整路径即可，filesystem.py 已处理 |
