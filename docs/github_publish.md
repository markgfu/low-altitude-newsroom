# 获取项目与维护仓库

公开仓库：[markgfu/low-altitude-newsroom](https://github.com/markgfu/low-altitude-newsroom)。

## 在自己的电脑运行

可以在仓库选择 Code → Download ZIP 并解压，也可以克隆：

```powershell
git clone https://github.com/markgfu/low-altitude-newsroom.git
cd low-altitude-newsroom
```

把解压或克隆后的目录作为自己的 Codex 工作目录，按根目录 [START_HERE.md](../START_HERE.md) 执行。使用自己的账号、联网能力和授权；项目不迁移原作者的登录态或定时任务。

## 更新项目

克隆的工作副本可在确认本地改动已保存后执行 `git pull --ff-only`。两份 Excel 是版本快照，更新清单仍需保留 ID、历史说明和版本保护。

提交前运行单元测试与 `python scripts/check_repository.py`。`runtime/`、`output/`、账号配置及签名下载地址不进入 Git。保留远端历史，不强推覆盖他人改动。

项目尚未选定开源许可证；公开可见不等于自动授予全部再分发权限，第三方图片继续遵守原许可。
