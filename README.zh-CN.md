<h1 align="center">EvidentLoop</h1>

<p align="center"><strong>把本地 Git diff 变成有证据、可回链的审计报告</strong></p>

<p align="center">
  <a href="https://github.com/evidentloop/evidentloop/blob/main/README.md">English</a> ·
  <a href="https://github.com/evidentloop/evidentloop/blob/main/README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <img alt="状态：Alpha" src="https://img.shields.io/badge/status-alpha-F59E0B">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776AB">
  <img alt="代码差异 schema 0.4" src="https://img.shields.io/badge/code--diff%20schema-0.4-0F766E">
</p>

![EvidentLoop 从 Git diff 到人工判断的产品路径](https://raw.githubusercontent.com/evidentloop/evidentloop/v0.1.0a1/docs/assets/evidentloop-cover.png)

EvidentLoop 把本地 Git diff 变成一份单文件 HTML 报告。纳入风险评分的问题都会定位到真实修改行；你可以核验、作出裁定，再让编程助手更新同一份报告，不重新审查代码，也不修改业务代码。

## 快速开始

需要 Git、Python 3.10 或更高版本、uv、用于安装 Skill 的 Node.js/npx，以及支持 Skill 的编程助手。

```bash
# 体验离线 demo
uvx evidentloop demo

# 安装 CLI 与 Skill
uv tool install evidentloop
npx skills@latest add evidentloop/evidentloop --skill evidentloop -g
evidentloop doctor
```

CLI 也可以通过 `pipx install evidentloop` 安装。

进入要审计的 Git 仓库后，对编程助手说：

```text
帮我用 EvidentLoop 审计 staged changes，并生成 HTML 报告。
```

## 审计产物

| 文件 | 作用 |
|---|---|
| `audit.json` | 经过校验的审计记录，保存 Git 变更片段、问题及其对应关系。 |
| `audit.html` | 单文件报告，展示问题附近的代码证据和浏览器本地决策。 |
| `audit-feedback.jsonl` | 可选的机器可读裁定导出；报告主入口会复制同一内容给编程助手。 |

| Schema 0.4 报告总览 | 人工裁定与复制给 AI 流程 |
|---|---|
| [![Schema 0.4 报告总览](https://raw.githubusercontent.com/evidentloop/evidentloop/v0.1.0a1/docs/assets/evidentloop-report-overview.png)](https://raw.githubusercontent.com/evidentloop/evidentloop/v0.1.0a1/docs/assets/evidentloop-report-overview.png) | [![人工裁定与复制给 AI 流程](https://raw.githubusercontent.com/evidentloop/evidentloop/v0.1.0a1/docs/assets/evidentloop-report-feedback.png)](https://raw.githubusercontent.com/evidentloop/evidentloop/v0.1.0a1/docs/assets/evidentloop-report-feedback.png) |

HTML 可以直接在本地打开，也可以脱敏后放到静态网站。待更新反馈只保存在每位访问者的浏览器中，复制或下载后才能传递；报告可以分享，但不是多人协作服务。

记录裁定后，点击 **复制给 AI 更新报告**，在保存原始 `audit.json` 的工作区中把机器块粘贴给已启用 EvidentLoop 的编程助手。默认 `revise` 只更新原目录中的 `audit.json` 和 `audit.html`，其他文件保持不变；只有显式 `--out` 才另存副本。过期、冲突或无法唯一定位的反馈会停止处理，不自动猜测或合并；报告修订不会修改业务代码，也不会触发模型复审。

EvidentLoop 使用编程助手已有的模型，不会执行 diff 或模型输出中的命令。

## 工作原理

[![EvidentLoop 从宿主审查到校验产物对的生成架构](https://raw.githubusercontent.com/evidentloop/evidentloop/v0.1.0a1/docs/assets/evidentloop-architecture.png)](https://raw.githubusercontent.com/evidentloop/evidentloop/v0.1.0a1/docs/assets/evidentloop-architecture.png)

`complete` 表示宿主返回了有效、完整的审查结果。能发现多少问题，仍取决于宿主模型和输入上下文。

## Alpha 范围

| 支持 | 不支持 |
|---|---|
| 本地 Git staged、unstaged、ref 和 range diff | Folder diff、无 diff 文件审查或远程 PR URL |
| 新增、修改、删除、重命名与二进制文件元数据 | 自动修复或执行命令 |
| Schema `0.4`、报告 revision、问题精确回链修改行 | 根据反馈自动修复或触发模型复审 |
| 原路径反馈修订、JSON/HTML 成对回滚与显式另存副本 | 自动合并过期反馈或跨工作区搜索报告 |
| 完整、部分、失败和不确定状态 | Git diff 之外的审查目标 |

## 集成与开发

通过 Skill 即可独立使用 EvidentLoop，不需要接入其他工作流。

EvidentLoop 也可以向工作流提供可验证的审计结果：`diff_version` 标识被审计的 Git diff，`report_version` 标识正式 `audit.json` 的版本。[Sopify](https://github.com/evidentloop/sopify) 是首个接入这项能力的工作流，也欢迎其他工作流使用同一套公开接入契约。

集成方可以按 [AI host 集成](https://github.com/evidentloop/evidentloop/blob/main/docs/ai-host-integration.md) 使用 `prepare -> external review -> finalize` 路径；公共 Python API 位于 `evidentloop.api`。

本地开发验证：

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m ruff check .
python -m build
```

参考：[Pages 与样例报告](https://evidentloop.github.io/evidentloop/) · [v0 范围](https://github.com/evidentloop/evidentloop/blob/main/docs/v0-scope.md) · [数据模型](https://github.com/evidentloop/evidentloop/blob/main/docs/data-model.md) · [AI host 集成](https://github.com/evidentloop/evidentloop/blob/main/docs/ai-host-integration.md)

欢迎通过 [GitHub Issues](https://github.com/evidentloop/evidentloop/issues) 提交 Alpha 使用反馈与缺陷。

## License

本项目采用 [MIT License](https://github.com/evidentloop/evidentloop/blob/main/LICENSE)。
