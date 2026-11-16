# 多产品一致性保障模型

> 建立日期：2026-11-15　对应版本：v0.25.0 + `doctor --fix`（P1-7）
> 目的：把本项目的差异化从「支持 15 个产品」重述为**一条可验证的本机一致性保障链**。
> 依据：[`market-analysis-2026-11-15.md`](market-analysis-2026-11-15.md) §5 / §7——路径清单会被上游补齐，机制组合不会。

---

## 一、一条链，五个环节

| # | 环节 | 机制 | 命令 / 实现 | 失败时的表现 |
|---|------|------|-------------|-------------|
| 1 | **唯一权威源** | 所有技能只存一份 `~/.agents/skills/` | `config/products.py:CENTRAL_DIR`、`services/inventory.py` | 产品目录与中央分叉 |
| 2 | **受保护的分发** | symlink / junction / 复制三级降级；同名真实目录冲突跳过，需 `--force` | `services/sync/engine.py`、`utils/filesystem.py` | 链接未建立、`settings.json` 未启用 |
| 3 | **常驻自愈** | 原生文件事件（inotify / kqueue / ReadDirectoryChangesW）+ 每 30s 补齐产品侧丢失链接 | `askill watch`、`utils/watcher.py` | 手动删链、链接丢失 |
| 4 | **诊断与修复** | 一次扫描回答「为什么不同步」，并给出可执行的修复计划 | `askill doctor` / `doctor --fix` | 死链、孤儿追踪、settings 锁、漂移 |
| 5 | **变更回退** | update / 重装前自动快照上一版 | `askill rollback --list`、`rollback <skill>` | 升级后技能损坏 |

链路方向是单向的：1 定事实 → 2 建链接 → 3 维持 → 4 诊断 → 5 兜底。任何环节都不会反向修改权威源。

---

## 二、`doctor --fix` 的边界

```bash
askill doctor                    # 只读诊断（原有行为不变）
askill doctor --fix              # 打印修复计划，dry-run，不改任何文件
askill doctor --fix --apply      # 执行且只执行下面两类 auto 动作
askill doctor --fix --json       # 机器可读的计划，供脚本/CI 消费
```

**`--apply` 只做两件事**（复用既有原语，不引入新写路径）：

| id | 触发条件 | 执行 |
|----|---------|------|
| `relink` | 死链的名字仍存在于中央仓库 | `askill sync`（重连） |
| `gc` | 死链的名字已不在中央仓库 | `askill sync --gc`（清残留） |

**永远只提示、不自动执行**：

- `settings.json` 被运行中的 IDE 锁住 → 关闭/重启 IDE 后重跑 `askill sync`
- 孤儿来源追踪条目 → 人工编辑 `.askill-sources.json`
- 真实目录 shadowing 中央技能 → `askill drift` / `adopt` / `sync --force`，由人决定归属
- 环境 FAIL（git 缺失、代理不可达）→ 修环境
- 可回滚快照 → `askill rollback --list`（回滚是有损决策，不自动做）
- 中央仓库不存在 → `askill install <source>`

**铁律**：真实目录（非链接）永不被 `--apply` 覆盖或删除。这是 v0.13.0 冲突保护以来的底线，也是 `drift` / `adopt` 的领地。

---

## 三、为什么不做一个「全自动守护进程」

1. **可逆性不对称**：重建链接是幂等的，删除目录、覆盖本地修改、回滚版本不是。把不可逆动作藏进自动流程，一次误判就是数据丢失。
2. **多数故障需要人的信息**：settings 锁需要用户关 IDE；漂移需要用户判断哪份是权威；代理不可达需要用户决定是开代理还是改配置。
3. **离线零依赖定位**：没有服务端、没有遥测、没有账号，因此也不该有「云端策略下发」。`doctor --fix` 的确定性来自 `products.py` 声明 + 本机目录扫描，任何时候都能复现。

`watch` 负责**无人值守的幂等维护**（补链接），`doctor --fix` 负责**有人在场的一次性治理**，两者互补，不互相替代。

---

## 四、可复现验证

```bash
# 干净仓库：计划应为 noop
askill doctor --fix

# 含死链的临时环境：计划应列出 relink / gc 两类动作
askill doctor --fix --json | python -m json.tool | head -40

# 回归测试
pytest tests/test_doctor_fix.py -q
```

退出码沿用项目契约：`0` 成功（含 dry-run / 空计划）、`1` 修复执行失败、`2` 用法错误（`--apply` 单独使用）。

---

*相关：[`product-matrix.md`](product-matrix.md) 逐产品能力 · [`optimization-report-2026-11-15.md`](optimization-report-2026-11-15.md) P1-7*
