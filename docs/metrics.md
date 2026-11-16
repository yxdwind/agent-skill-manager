# 可观测基线（手工更新，无遥测）

> 建立：2026-11-15　用途：给 `market-analysis-2026-11-15.md` §7 的三情景判断提供**先行指标**，
> 替代没有一手数据支撑的 TAM / 渗透率推测。
> **本项目不内置任何遥测**（与 `PRIVACY.md` 的离线定位一致）；本文件全部数字都来自公开接口，可外部复核。

## 一、2026-11-15 基线

| 指标 | 基线 | 口径 / 注意 |
|------|------|-------------|
| GitHub stars / forks / issues | 2 / 1 / 0 | 瞬时快照 |
| PyPI 非镜像累计下载 | 3,073 | `without_mirrors`，2026-09-21 → 11-14；**仍含 CI 与自测流量** |
| 近 30 天 / 日均 | 1,023 / 36.5 | 同上 |
| 月度分布 | 9月 465 · 10月 1,814 · 11月(至14日) 794 | 同上 |
| 单日峰值 | 245（11-13） | 恰为 0.23/0.24/0.25 三版本发布日 → **峰值由发版自测驱动，非自然增长** |
| skills.sh 收录 | 1 skill / 2 installs | `skills.sh/yxdwind/agent-skill-manager` |
| 发版节奏 | 25 releases / 53 天 | 0.7.0 (9-21) → 0.25.0 (11-13) |
| 产品 / 命令 / 测试 | 15 / 21 / 396 | `askill products` · `grep -c add_parser` · `pytest -q` |
| 上游国产覆盖 | npx skills 9 行；DSH 7 行 | `scripts/check_upstream_paths.py` 对 2026-11-15 快照 |
| 上游 PR | [vercel-labs/skills#2763](https://github.com/vercel-labs/skills/pull/2763) OPEN | 5 个 agent 定义，见 `docs/upstream/` |

## 二、复现命令（全部只读）

```bash
# GitHub
curl -s https://api.github.com/repos/yxdwind/agent-skill-manager \
  | python -c "import json,sys; d=json.load(sys.stdin); print(d['stargazers_count'], d['forks_count'], d['open_issues_count'])"

# PyPI 下载量（recent 含镜像，overall 可取 without_mirrors）
curl -s https://pypistats.org/api/packages/cn-skill-sync/recent
curl -s https://pypistats.org/api/packages/cn-skill-sync/overall \
  | python -c "import json,sys; d=json.load(sys.stdin)['data']; print(sum(r['downloads'] for r in d if r['category']=='without_mirrors'))"

# 项目自身
pytest -q
grep -c add_parser src/controllers/cli.py
askill products --json | python -c "import json,sys; print(len(json.load(sys.stdin)))"

# 上游路径覆盖（离线可传 --agents FILE --dsh FILE）
python scripts/check_upstream_paths.py --json
```

## 三、月度记录

| 月份 | 日期 | stars | 非镜像月下载 | 非发版日基线 | skills.sh installs | 上游国产条目 | 备注 |
|------|------|------:|-------------:|--------------|-------------------:|-------------:|------|
| 2026-11 | 11-15 | 2 | 794（至 14 日） | 36.5（含发版） | 2 | 9 | 基线；PR #2763 发出 |
| 2026-11 | 11-16 | — | — | — | 2 | 9 | **PR #2763 被 antfu 关闭**，明确推荐 `.agents/skills` 统一路径 → Bear 信号已观测 [A15]（见 `market-analysis` §7）；同日发布 **v0.26.0** |

> 每月更新一行即可。**「非发版日基线」**是关键指标：把发版当天的自测下载剔除后，才能看出真实用户是否增长。
> 若该值连续两月不涨，而上游国产条目数持续上升 → Bear 情景（标准收敛）正在发生，应把重心从路径同步迁到审计/门禁。

## 四、情景先行指标对照

| 信号 | Bear | Base | Bull |
|------|------|------|------|
| 上游国产条目数 | 快速接近 15 | 缓慢补齐 | 本项目成为上游数据源（PR 被合并/引用） |
| 非发版日下载基线 | 持平或下降 | 缓慢上升 | 明显上升 |
| skills.sh installs | 个位数 | 两位数 | 三位数以上 |
| 上游 PR / 引用 | 无回应 | 有 review | 合并 + 第三方引用 `products --json --paths` |

> 这些是**判断依据**，不是预测值。任何数字变化都要回到本文件的复现命令核验，不引用未标注来源的二手数据。
