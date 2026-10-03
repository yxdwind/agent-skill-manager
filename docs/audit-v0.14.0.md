# 代码审计报告：v0.13.x → v0.14.0（a55b436..0c0a2f0）

> 审计日期：2026-10-03　范围：12 个提交（P0 加固 → v0.14.0 发布），约 2300 行新增
> 方法：全量 diff 走读 + 行为实证（mock 计数 / capsys 捕获 / 端到端复现）+ 本地 ruff / mypy / pytest 验证
> 分级：**P1 = 功能 bug**、**P2 = 契约问题**、**P3 = 打磨项**

## 审计时验证通过的部分

- ruff、mypy、229 个测试本地全绿，与 CI 声明一致
- 并发 sync 设计正确：目录去重预留与 stdout 输出均在 `state_lock` 内原子完成；`pool.map` 保序；`max_workers=max(1, ...)` 兜底 adopt 的 PRODUCTS 置空场景
- `_write_json_atomic`（tempfile 同卷 + fsync + os.replace + 失败清理）实现标准
- 恶意样本黄金测试体系设计好：参数化 + 缺失 `EXPECTED_TRIGGERS` 条目 fail-loud + 按 summary 计数断言

## P1 — 已修复 ✅

| # | 问题 | 位置 | 修复 |
|---|------|------|------|
| 1 | `_print_sync` 调用了两次 `sync_skill`（mock 实证 quiet=True 时调用 2 次，verbose=[False, True]）：每次 sync 全量跑两遍、`-q` 完全失效、verbose 输出整段重复 | cli.py:261-262 | 删除重复调用；回归测试 `test_sync_runs_sync_skill_exactly_once` |
| 2 | `askill install`（缺 source）崩栈：`nargs="?"` 使缺参不触发 ArgumentError，`main()` 预留的帮助分支成死代码，`resolve_source(None)` 抛 AttributeError（已端到端复现） | cli.py main/install 分支、registry.py:87 | main() 检查 `args.source is None` → 打印 `_INSTALL_HELP` + `sys.exit(2)`；回归测试 `test_install_without_source_prints_help_and_exits_2` |

## P2 — 已修复 ✅

| # | 问题 | 位置 | 修复 |
|---|------|------|------|
| 3 | `status -q` 输出孤儿表头（header/分隔线不受 quiet 门控，数据行受门控；capsys 实证输出只有表头零数据行） | cli.py `_print_status` | quiet 剥离装饰（表头/分隔线/尾注）但保留数据行；回归测试 `test_status_quiet_prints_rows_without_header` |
| 4 | 退出码恒为 0：argparse 错误被吞、操作失败也 return None——`--json`/`-q` 面向脚本化，但脚本无法感知失败 | cli.py `main()` | usage 错误（缺必需参数、未知命令、非法标志）`exit 2`；`--help` 保持 0；操作类退出码维持现状（见开放项） |
| 5 | `--json` 契约不完整：`adopt` 的 json_mode 参数被接受但忽略；sync/install/remove/pack 也接受 `--json` 却从不输出 JSON——help 承诺 "machine-readable JSON" 但脚本拿到人类文本 | cli.py `_build_parser` | `--json` 只挂在真正支持 JSON 的子命令（status/list/products/audit/search/verify/update）；其余子命令 `--json` → usage 错误 exit 2（响亮失败优于静默说谎）；回归测试 `test_json_flag_rejected_on_non_json_command` |
| 6 | `search --json --install N` 越界时输出两个拼接的 JSON 文档，stdout 流不可解析 | cli.py `_cmd_search` | 越界校验前移到任何输出之前（错误文档替代结果文档）；回归测试 `test_search_json_invalid_install_single_document` + `test_search_json_valid_install_single_document` |

## P3 — 开放项（不阻塞，留待后续）

- **7.** `sync.py` 的 `[f.result() for f in futures]` 无异常兜底——单个 worker 意外异常会丢弃该 skill 全部结果（worker 内部已大量捕获，触发概率低）。建议 per-future try/except 返回 `(short, False, "error: ...")`
- **8.** 共享目录预留先于 `create_link`：primary 冲突时 secondary 仍报 `(True, "shared->primary")`，同一目录一败一成，报告矛盾
- **9.** ~~json_mode 下宽终端时每 skill 审计两遍~~ —— 已顺手修复（`show_score and not json_mode` 才计算行内评分）
- **10.** ruff 版本单向漂移：pre-commit 钉 `v0.5.0`，CI 装 `ruff>=0.5`（最新）——建议 CI 改为精确钉版
- **11.** `pyproject.toml` classifiers 仍列 Python 3.8/3.9，与 `requires-python = ">=3.10"` 矛盾，PyPI 页面误导
- **12.** mypy 配置实际很弱（`check_untyped_defs=false` + `allow_untyped_defs=true` + watcher.py 整体排除）——建议逐步收紧
- **13.** `_print_list` quiet 分支冗余判断；`products.py` 注释说 "Cast" 实际用 `type: ignore`
- **14.** `tests/fixtures/malicious/exe_payload/payload.exe`（4KB 真二进制）入库——企业 AV/托管策略可能拦截，建议 `.gitattributes` 标注

## 环境发现（审计过程中的重要副产品）

本地 `pytest` 曾长期**静默测试 site-packages 里的旧安装副本**而非仓库代码（本包 `package-dir = {"agent_skill_manager" = "src"}` 的映射只有 `pip install -e .` 能建立，`sys.path` 无法表达）。本次审计中该问题导致回归测试一度"全部失败"，实际是旧副本没有修复代码。已在本机执行 `pip install -e .` 对齐 CI。**贡献者请务必用 editable 安装跑测试**（README 已有说明）。

## 修复验证

- 新增回归测试 8 个（`tests/test_cli_flags.py::TestAuditRegressions`），全套 **235 passed**（watcher 2 个原生监听用例为已知 Windows 环境抖动，3 次复跑 2 过 1 挂，与本批改动无关，见 tests/test_watcher.py）
- ruff / mypy 保持全绿

## 已知行为变更（脚本用户注意）

1. `askill sync` 不再执行两遍；`-q` 现在真正静默
2. usage 错误退出码 0 → **2**（缺参/未知命令/非法标志）；操作失败仍为 0（后续可议）
3. `--json` 在不支持的子命令上从"静默忽略"变为 **exit 2**
4. `status -q` 从"只有表头"变为"只有数据行"
