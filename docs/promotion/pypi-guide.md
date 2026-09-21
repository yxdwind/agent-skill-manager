# PyPI 上架：已完成（2026-09-21）

> **cn-skill-sync 0.7.0 已上线**：https://pypi.org/project/cn-skill-sync/
> 首发已完成；以下为后续发版参考。


> 目标：让用户 `pip install askill` 一键安装。包名 `askill` 已确认可用（2026-09-21 查询）。
> 本地已构建好 `dist/askill-0.7.0.tar.gz` 和 `dist/askill-0.7.0-py3-none-any.whl`（twine check PASSED）。

## 第一步：注册 PyPI 账号（约 3 分钟）

1. 打开 https://pypi.org/account/register/ ，邮箱注册并验证
2. 开启两步验证（2FA）：https://pypi.org/manage/account/ → Two factor authentication
   （PyPI 新账号上传必须开 2FA）

## 第二步：生成 API Token（约 2 分钟）

1. https://pypi.org/manage/account/token/ → Add API token
2. Token name：`askill-upload`；Scope：**Entire account**（首次上传项目还没建，先选 entire account）
3. 复制生成的 token（`pypi-` 开头，只显示一次）

## 第三步：上传（二选一）

### 方式 A：命令行临时 token（最快）

在 `D:\pythonproject\agent-skill-manager` 目录执行（替换 `<你的token>`）：

```powershell
D:\ProgramData\anaconda3\python.exe -m twine upload dist/askill-0.7.0* `
  -u __token__ -p "<你的token>"
```

### 方式 B：.pypirc 配置（一次配置长期用）

在 `C:\Users\yxdwi\.pypirc` 写入：

```ini
[pypi]
username = __token__
password = pypi-xxxxxxxxxxxxxxxx
```

然后执行：

```powershell
D:\ProgramData\anaconda3\python.exe -m twine upload dist/askill-0.7.0*
```

## 第四步：验证

- 打开 https://pypi.org/project/askill/ 确认页面渲染正常
- 新环境试装：`pip install askill` → `askill version` → `askill products`

## 以后发新版本的三步

```bash
# 1. 改 pyproject.toml 的 version
# 2. 构建 + 检查
python -m build && python -m twine check dist/*
# 3. 只上传新版本
python -m twine upload dist/askill-<新版本>*
```

## 注意事项

- 包名 `askill`，import 名仍是 `agent_skill_manager`（发行名与导入名分离，CLI 工具常见做法）
- PyPI 项目名一经发布无法改名/删除，只能弃用（yank）——首发前确认元数据
- README 会自动渲染为项目主页（long_description 已配置）
- 上传后 `pip install askill` 立即可用，无需审核
- **把 token 存到密码管理器，不要提交到任何仓库**
