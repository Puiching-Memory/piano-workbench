# 发布到 GitHub

本目录是独立 Git 仓库；发布包包含代码、文档、原创测试曲及已标注来源的试听，不包含模型、SF2 或用户歌曲。

已于 2026-10-26 推送至私有仓库 [Puiching-Memory/piano-workbench](https://github.com/Puiching-Memory/piano-workbench)。当前 CI 结果见该仓库的 Actions；私有内容仅对有访问权限的账户可见。

## 本地先检查

```powershell
python -m pip install -e .
piano-workbench doctor
python -m unittest discover -s tests -v
git status --short
git diff --check
```

可选依赖不齐时部分集成测试会明确跳过，不能把跳过记成通过。详见 `verification.md`。

## 创建远程仓库

GitHub CLI 需要你自己的有效登录。登录与授权由用户完成；本项目不保存凭据。

```powershell
gh auth login
gh repo create piano-workbench --private --source . --remote origin --push
```

以上命令用于首次发布到自己的账户，现有远程无需重复创建。示例先创建私有仓库。若你已决定公开，可使用 `--public`。发布后检查 GitHub Actions 对应提交的运行结果。

本地初始提交使用 `Piano Workbench contributors` 的自动化标识。如果希望提交归到自己的账户，先配置本仓库的 `user.name` / `user.email`，再按需要调整初始提交作者。

## 发布范围

- GitHub 源码包：完整文档、测试和原创示例。
- Python wheel：CLI 与模块，不附带演奏、音源、模型或示例音频。
- 模型权重仍遵循上游单独许可；公开代码不代表获得模型商业授权。
- 对照页是静态页面；直接下载后打开，或自行配置 GitHub Pages。当前版本没有托管服务和上传入口。
