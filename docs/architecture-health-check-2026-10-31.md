# agent-skill-manager 架构体检报告

- **日期**：2026-10-31　**基线**：v0.19.1（commit f15636c，工作区 clean）
- **方法**：源码走读（25 个 .py 全量）+ 门禁实测 + 历史缺口台账逐项核对
- **声明**：本报告为只读体检，未改动任何源码；所有结论附 file:line 证据

---

## 0. 总评

**总体评级：B+（健康，可放心继续演进）**

| 维度 | 评级 | 一句话 |
|------|:---:|--------|
| 分层与依赖方向 | A- | 五层无倒置；services 内有一处被惰性导入压制的模块级环 |
| 声明式产品模型 | A | 250 行声明驱动 15 产品 × 17 命令，配套 430 行一致性锁，是全项目最大亮点 |
| 缺口闭环能力 | A | product-matrix 台账 A1–A9 八项已闭环、一项部分修复（见 §6） |
| 模块规模与职责 | B- | cli/sync 双千行模块占全库 41%，sync 五职责集中，是最大的演进债 |
| 静态与类型 | A | ruff 全绿；mypy 23 文件全绿（watcher 豁免是文档化决定） |
| 测试架构 | A- | 309 passed；恶意样本 fixture 库 + 跨产品回归锁模式成熟 |
| 打包与仓库卫生 | A | completion 子包三处声明齐全；根目录 0 噪音；.gitignore 覆盖完备 |
| 文档与事实一致性 | A | 测试徽章与实测一致（309/309）；CHANGELOG 与 git log 一一对应 |

无红色项：不存在分层倒置、安全红旗或会导致运行故障的循环依赖。

---

## 1. 门禁基线（本次实测）

```
ruff  → All checks passed
mypy  → Success: no issues found in 23 source files
pytest → 309 passed (16.4s)
git   → working tree clean
```

watcher.py 的 mypy 豁免（pyproject exclude + overrides 双保险，附平台理由）是**记录在案的例外**而非失修，评 A 不扣分。

---

## 2. 演进速览（0.16.1 → 0.19.1，2026-10-09 → 10-12）

| 版本 | 架构意义 |
|------|---------|
| P0（8536d6a） | settings.json 原子写 + 锁定告警聚合 —— A3 收尾 |
| v0.18.0 | 命名交叉引用、wheel 内置补全、publish --target、UX |
| v0.18.1 | completion 合法子包化 + 单 PyPI 触发（打包架构修正） |
| v0.18.2 | CI 修复（RUF001 CJK 同形字符）—— 工具链升级的连带成本已消化 |
| v0.18.3 | 删除 skill 时清理死 junction |
| v0.19.0 | **watch 自愈产品侧链接丢失** —— watch 从“同步器”升级为“自愈守护进程”，架构角色变化 |

**解读**：四天 9 个提交全部是小步 feat/fix，无大重构；漏洞修复节奏健康，说明当前架构支撑得了快速迭代——这也意味着 §4 的拆分建议不紧急，但随新功能加入（每个新产品 ≈ +1 个分支）会持续恶化。

---

## 3. 分层与依赖

```
controllers/cli.py (1077)  ──→  config / services / utils
        │
services/  sync(1076) watch(390) publish(298) scaffold(191)
           sources(185) spec(181) registry(124) drift(88) audit(441) welcome(49)
        │                       │
        ├──→ config/products.py (250) ──→ models/product.py
        ├──→ models/report.py（audit/sync 消费）
        └──→ utils/ filesystem(219) watcher(553)   ← 零内部依赖，完全隔离 ✅
```

**方向健康**：config→models、controllers→{config,services,utils}、services→{config,models,utils} 均无倒置；utils 与 models 是纯叶子层。

### 🟡 发现 1：spec ⇄ sync 模块级环（唯一真实的环）

- `spec.py:16` —— **模块级** `from .sync import list_skills`
- `sync.py:453` —— 函数内 `from .spec import check_spec, product_frontmatter_issues`

运行时靠 sync 侧的惰性导入压制，一旦有人在 sync.py 顶层加 `from .spec import ...` 立即 ImportError。环的根因是 `list_skills`（目录枚举，本质是 filesystem 层能力）被放进了 sync 这个重型模块。

**建议**（低成本，30 分钟）：把 `list_skills` 下沉到 `utils/filesystem.py` 或独立 `inventory.py`，spec 改从那里导入，环即解除。

### 🟡 发现 2：sources ⇄ sync 双向惰性依赖

`sources.py:169` 与 `sync.py:640` 互相函数内导入。当前无害，但 install 流程的“装完登记来源”逻辑横跨两个模块，后续拆分时需一起考虑。

### 🟢 惰性导入作为一致模式

cli.py 内 7 处（:103/:296/:426/:474/:745/:847/:916/:986）+ services 内 8 处，均为启动提速或环规避。模式一致、注释到位——可接受，但 §4 的拆分会消化掉其中大半。

---

## 4. 模块规模与职责

| 模块 | LOC | 占比 | 评估 |
|------|----:|-----:|------|
| controllers/cli.py | 1077 | 20.4% | 🟡 17 命令的 parser 构建 + if/elif 大 dispatch；尚可但逼近上限 |
| services/sync.py | 1076 | 20.4% | 🟡 **五职责集中**：sync / install / adopt / settings_io / pack |
| utils/watcher.py | 553 | 10.5% | 🟢 三平台原生事件，内聚合理，豁免有据 |
| services/audit.py | 441 | 8.4% | 🟢 |
| 其余 14 个模块 | 2124 | 40.3% | 🟢 均在 400 行以内 |

- **cli.py**：千行里大半是 `_build_parser`（argparse 声明天然冗长）+ dispatch。低风险的改进是表驱动 dispatch（`{cmd: handler}` 映射），可消掉 40 行 if/elif 链并让 17 命令一目了然。**优先级低**。
- **sync.py（主要演进债）**：sync_engine / install（含 registry+sources 钩子）/ adopt / settings_io / pack 五个子域共享一个文件，互相之间只有 2-3 个共享工具函数。**建议**在下次大功能前拆为子包（`services/sync/` 下分模块），预计每个子模块 150-350 行；`tests/` 已按行为组织（test_adopt/test_watch 等），拆分对测试几乎无感。
- 测试/实现 LOC 比 ≈ 0.78（4089/5271），对 CLI 工具属良好水位。

---

## 5. 声明式模型与一致性锁（架构最大亮点）

`products.py` 250 行声明式定义（路径/平台矩阵/sync_method/settings/frontmatter/共享目录/extra_dirs）驱动全部 17 个命令；`test_matrix.py` 430 行从声明推导断言。**新增一个产品 = 只改一个文件 + 一条声明**，且 CI 自动校验声明完整性——这正是 onboarding-new-product.md 承诺“一周适配”的架构底气。保持住“产品逻辑不进代码、只进声明”的纪律即可。

---

## 6. 历史缺口台账核对（product-matrix.md v0.13.0 基线 → v0.19.1 现状）

| # | 缺口 | 现状 | 证据 |
|---|------|------|------|
| A1 | USAGE 产品清单停在 6 个 | ✅ 已修 | 硬编码清单已删除（grep "Supports:" 无匹配），动态生成 |
| A2 | 平台无路径时输出裸 n/a | 🟡 **部分修复** | 人类可读输出已带原因 `skip (no windows build)`（sync.py:303），但机器可读的 StatusEntry 仍是裸 `"n/a"`（sync.py:94/:306），`status --json` 消费者拿不到原因 |
| A3 | settings 按 WorkBuddy 硬编码 | ✅ 已修 | 通用 `_enable_in_settings`（sync.py:746）+ 声明式 settings_file + 原子写 + 锁定告警聚合（sync.py:339-357）；watch.py:37 复用 `_disable_in_settings` |
| A4 | 无按产品 frontmatter 校验 | ✅ 已修（v0.13.0） | `product_frontmatter_issues` 进入 publish 门禁（sync.py:453） |
| A5 | 共享目录重复同步 | ✅ 已修（by-design） | `synced_dirs` 预留 + `shared->traecn` 报告（sync.py:307-313） |
| A6 | sync 静默覆盖真实目录 | ✅ 已修（v0.13.0） | `create_link` 返回 conflict → `SKIP conflict` 无条件打印（sync.py:325-331） |
| A7 | adopt 死代码块 | ✅ 已修 | `adopt_from_platform` 仅 1 def + 1 调用 + 1 注释（sync.py:917 / cli.py:20,301） |
| A8 | pack 产品 status 恒为 manual | ✅ 已修 | manual/packed/stale 三态（sync.py:139-152） |
| A9 | 未安装产品也建目录 | ✅ 已修 | `product_set_up` 门卫进 extra_dirs 与 settings 两条路径（sync.py:349-365） |

**8/9 闭环，A2 是唯一残余**——修复成本约 15 分钟：给 StatusEntry 加 `reason` 字段（或把 n/a 改为 `n/a (no windows build)`），同步 test_matrix 断言。

---

## 7. 打包与仓库卫生

- ✅ **completion 子包**（v0.18.1）：packages / package-dir / package-data 三处声明齐备（pyproject），`COMPLETION_DIR` 常量暴露安装路径——wheel 内资源引用的正确做法
- ✅ **根目录 0 噪音**：8 天前还存在的 4 个 egg-info、dist080、50+ 个 .pytest-tmp-* 已全部清理，且 .gitignore 对 `.pytest-tmp*/`、`*.egg-info/`、`dist080/` 全覆盖，不会复发
- ✅ **测试 fixtures**：tests/fixtures/malicious/ 下的 grab.py / run.py / clean.py 是安全测试的恶意样本（credential_grab、exec、rm_rf_root、shell_true），命名扎眼但合规，勿误删
- ✅ PyPI 名与 repo 名分离有明确文档（cn-skill-sync vs agent-skill-manager，CHANGELOG/README 双处）

---

## 8. 文档健康

- ✅ **README 测试徽章与实测一致**：双语 badge 均为 Tests-309（README.md:16 / README.en.md:13），与 v0.19.1 的 309 个测试同步——发版同步徽章的纪律在 0.18/0.19 两次发版中都保持了
- ✅ CHANGELOG 与 SemVer 纪律良好（0.19.1 条目与 git log 一一对应）

---

## 9. 行动建议（按收益/成本排序）

| # | 行动 | 成本 | 收益 |
|---|------|------|------|
| 1 | 轮换 2026-09 提交中引用过的 PyPI 上传 token（已由安全提交 022eee0 从工作区移除；按泄漏处置流程仍应轮换） | 5 分钟 | 消除在案凭据风险 |
| 2 | A2 收尾：StatusEntry 的 n/a 附原因 + test_matrix 断言 | 15 分钟 | 补齐 8/9 → 9/9 缺口闭环 |
| 3 | `list_skills` 下沉解 spec⇄sync 环 | 30 分钟 | 消除唯一模块级环，惰性导入 -1 |
| 4 | sync.py 拆子包（sync/install/adopt/settings/pack） | 半天-1 天 | 消化最大演进债；建议放在下一个大功能（如第 16 个产品）之前 |
| 5 | cli dispatch 表驱动 | 1 小时 | 可读性优化，可与 4 同批做 |

**不建议现在做**：watcher.py 去豁免（平台代码，mypy 无法建模，当前双保险隔离是正确姿势）；引入任何第三方依赖（零依赖是核心卖点，已被 README/推广物料反复引用）。

---

## 10. 复检记录

- **2026-11-01**：§6 A2 已闭环 —— 新增 `StatusEntryDetail.reason`（models/report.py），`get_status` 在 n/a 行写入 `no <platform> build`（services/sync.py），`askill status --json` 行与人类表格脚注均携带原因；§3 spec⇄sync 模块级环已解除 —— `list_skills` 下沉至 `services/inventory.py`（带可选 central 参数），`spec.py` 改从 inventory 导入，`check_all_specs(central)` 由 CLI 传入接缝感知的 `CENTRAL_DIR`，sync 保留薄包装维持 `patch sync.CENTRAL_DIR` 测试接缝。门禁：ruff 全绿、mypy 24 文件全绿、pytest 309 passed（watcher 原生事件测试在全量并发下偶发一次时序抖动，单跑与全量复跑均通过，判定非回归）。
- **2026-11-01**：§6 A2 已闭环 —— 新增 `StatusEntryDetail.reason`（models/report.py），`get_status` 在 n/a 行写入 `no <platform> build`，`askill status --json` 行与人类表格脚注均携带原因；§3 spec⇄sync 模块级环已解除 —— `list_skills` 下沉至 `services/inventory.py`（带可选 central 参数），`spec.py` 改从 inventory 导入，`check_all_specs(central)` 由 CLI 传入接缝感知的 `CENTRAL_DIR`，sync 保留薄包装维持 `patch sync.CENTRAL_DIR` 测试接缝。门禁：ruff 全绿、mypy 24 文件全绿、pytest 309 passed。
- **2026-11-03**：§9 #4/#5 落地。**sync.py（1076 行）拆为 `services/sync/` 包**：__init__ 34（接缝 facade）/ engine 449 / install 270 / adopt 174 / settings_io 110 / audit_report 75 / pack 43，全部 <500 行；接缝机制 = 包属性 `CENTRAL_DIR`/`PRODUCTS` + 子模块经 `_pkg.X` 调用时晚绑定，实测补丁目标全集 **6 个**：`CENTRAL_DIR`、`PRODUCTS`、`get_product_path`、`is_symlink_or_junction`、`_install_from_url`、`_sync_one_product`（后两个分别由 test_drift/registry 与 test_matrix 的红灯揪出，证明“只信全量测试”是对的）；`git mv` 保留文件历史；spec 与 sync 彻底解耦。**cli dispatch 表驱动**：17 分支 if/elif → `_HANDLERS` 表 + `--version`/welcome 前置 + quiet/json_mode 归一化到 namespace。门禁：ruff 全绿、mypy 30 文件全绿、pytest 309 passed，端到端冒烟（version / status --json 435 行 / drift --json / verify）全通。诚实备注：cli.py 净 +17 行（1083→1094，适配器与表头注释 > 删掉的分支链），换取的是 17 命令一张表可读性；sync 包总行数 1155 > 原 1076（每模块 docstring/导入头的结构性开销）。提交：9da8144（sync 包拆分）+ 2ae993e（dispatch 表）。
- **2026-11-03（同日追加）**：0.20.0 发布事故——干净 venv 实装冒烟抓到 `services.sync` 子包未进 wheel（pyproject `packages` 白名单漏了新子包，仓库内 CI 天然无法发现），PyPI 0.20.0 对新装用户不可用。处置：f9cc30d 修白名单 + 6713cc7 给 release.yml 加「发布前 wheel 冒烟安装」守门（导入失败则 job 失败，产物到不了 PyPI）+ 4e9bef2 发 0.20.1；干净 venv 实装 0.20.1 验证通过（askill version / services.sync 导入全净）。教训入册：**拆包/新增子包必须同步改 setuptools packages 白名单；发布链路的验证必须包含 wheel 实装，仓库内测试不能替代**。0.20.0 待维护者在 PyPI 上 yank。

- **2026-11-12**：0.21.0（竞品借鉴轮）复检。新增 `services/manifest.py`（零依赖，只依赖 config/products + inventory + sources + sync.install 的 `_install_from_url`）与 `audit_report.residency_report`（挂在 sync.audit_report 命令层，安全分析器零改动）——两处均未新增模块环，分层约束保持。门禁：ruff 全绿、mypy 31 文件全绿、pytest 320 passed。**wheel 冒烟守门首次实战通过**：release.yml 在 PyPI 上包前实装 0.21.0 wheel，manifest/residency 模块可导入（0.20.0 式事故未重演）。端到端：PyPI 实装 → `askill install yxdwind/skills@askill-ops --sync` 全产品 ok（DuMate manual 属设计内）。流程备注：本次 `cz bump --changelog` 静默未执行（打印了计划但未改文件、未建提交），改用手动 bump（pyproject 两处 version：项目 + [tool.commitizen] 需同步改）；tag 需在 bump 提交落位后建，第一次手建 tag 指在了未 bump 提交上已删重建。另一个环境发现：全局 gitconfig 的 http.proxy=127.0.0.1:7897 在代理未运行时会让 `askill install`（内部 git clone 走 HTTPS）报难懂的错误，临时用 GIT_CONFIG_GLOBAL 空文件绕过——产品侧可考虑失败提示中点名代理问题。提交：6799393 / a73e828 / 76a4110 / 1a03769，tag v0.21.0，PyPI 0.21.0 实装验证通过。

- **2026-11-12（晚）**：0.22.0（引用层轮）复检。新增 `services/get.py`（只读预览，克隆通道复用 install.py 新提取的 `_shallow_clone`/`_report_clone_failure`，代理不可达时输出可操作提示而非裸 stderr——源自本机 gitconfig 代理未开时的真实故障）；新增 `_install_from_archive`（zip/.skill，zip-slip 防护 + frontmatter 名字段防路径逃逸双保险）。分层约束保持，测试 patch 目标无新增。门禁：ruff 全绿、mypy 32 文件全绿、pytest 336 passed。发布链路：手动 bump（cz 跳过风险已知，直接绕过）→ tag 后推 → release.yml 冒烟守门二次实战通过 → PyPI 0.22.0 上架（/simple/ 索引 CDN 传播有几分钟延迟，JSON API 先可见）→ 干净 venv 实装 + `get --list` 真实网络测试通过。信任基建：Dependabot + CodeQL（周更）+ CoC + 3 个 issue 模板（bug/feature/audit 误报申诉）。内容线：marketing/06 对标拆解文 + 07 即刻碎片。提交：1b457a3 / a39c960 / ec72e63 / 1c6e8e6 / 8079b9c，tag v0.22.0。踩坑入册：venv 内 pip 装包必须 `PIP_USER=false`（工具链全局 PIP_USER=1），本次首次安装还被 /simple/ 传播延迟误导以为包不存在。

- **2026-11-13**：0.23.0（可支持性轮）复检。新增 `services/doctor.py`（只读诊断：git/代理 TCP 可达性探测/中央仓含孤儿追踪/产品断链与 shadowing 漂移候选/settings 锁 r+b 探测）。实现中修正：get_product_path 运行时返 str（类型标注靠 cast），doctor 内强制转 Path；drift 候选判据收紧为「真实目录名与中央同名」消除纯复制产品误报；测试加 autouse 夹具隔离真机代理（维护者 gitconfig 代理不可达会污染所有未隔离用例）。bug 模板接入 doctor --json。**doctor 首跑即发现真机 9 条死链（全是 e2e-watch-probe 测试夹具残留 + doubaowork 死 agent-skill-manager 链）与 2 条孤儿追踪——已清理；同时暴露产品缺口：sync 不回收产品侧死链（GC 缺失，列入下轮候选）**。门禁：ruff 全绿、mypy 33 文件全绿、pytest 347 passed。发布：手动 bump → PyPI 0.23.0 → 干净 venv 实装 doctor --json 验证。提交：499def5 / afb6494，tag v0.23.0。下轮候选：doctor 点名断链清单、sync --gc 死链回收、e2e 测试夹具隔离到临时目录。

- **2026-11-13（晚）**：0.24.0（定向同步轮，第二轮对标落地）复检。新增：`sync_skill`/`install_skill` 的 `only` 参数（按 short 过滤 PRODUCTS，非法 short 报错列全表——学 tech-leads-club -a）；update_skill 快照 + `rollback_skill`/`list_rollbackable`（快照存中央仓库外 `~/.agents/.askill-versions/`，inventory 永不可见；update 失败不再丢技能；学 FrancyJGLisboa quarantine/rollback）。接缝纪律保持：引擎内 PRODUCTS 两处迭代均改用过滤后的局部 `products`，测试 patch 目标不变；sources 的 sync_skill 惰性导入照旧，测试 patch sync 包命名空间即可。README 数字口径纪律落地（15 产品声明带复现命令），zh 标题锚点 `#支持的产品` 有徽章引用故口径进正文不动标题——**改标题前必查锚点引用，这条应入册**。P4 收录跟踪修正：awesome 收录真实状态 = JackyST0/awesome-agent-skills #74 于 8-18 因 64 星门槛关闭（此前 checkpoint 写 VoltAgent #122 open 是失真）；skills-hub.ai 为自动镜像无自助入口。门禁：ruff 全绿、mypy 33 文件全绿、pytest 354 passed。提交：edd09ce / d3b9a27，tag v0.24.0。

- **2026-11-13（深夜）**：0.25.0（清洁轮）复检。新增：`sync --gc` 死链回收（只删目标不存在且名字不在中央的链接；中央同名死链留给正常 sync 重连；真实目录永不触碰——drift/adopt 的领地）；doctor 的 scan 返回 `broken_names` 并在报告里点名，断链检查同时给出两条出路（sync 重连 / sync --gc 删残留）；`get` 支持本地目录（与仓库流相同的只读语义）。测试基建发现：`_create_junction` 对不存在的目标会回退成复制（shutil 直接炸），测试造悬空 junction 必须 `cmd /c mklink /J` 且目标须为【本地卷】上不存在的路径（Z: 这类不存在卷会报 Local volumes required）。另核实：真机 9 条 e2e-watch-probe 死链非测试产生，是 watch 功能开发期的手动探针残留——测试无罪，GC 是正确治本。门禁：ruff 全绿、mypy 33 文件全绿、pytest 362 passed；真机 GC 实跑 no-op（清理后预期）。提交：1ad8eb0 / 72ebf9c，tag v0.25.0，PyPI 0.25.0 + venv 实装（sync --gc / get 本地路径）验证通过。发布链路备忘：PyPI JSON API 先可见、/simple/ 索引滞后 1-3 分钟，venv 冒烟遇 No matching distribution 先重试再怀疑发布失败。

---

*体检人：MOE · 证据均来自 f15636c 工作区实测 · 复检建议：下一个 minor 发版前重跑 §1 基线 + §6 台账*
