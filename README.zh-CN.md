<h1 align="center">change-audit</h1>

<p align="center"><strong>把本地 Git diff 收口成可回链、可核对的代码审计报告。</strong></p>

<p align="center">
  <a href="./README.md">English</a> ·
  <a href="./README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <img alt="状态：Alpha" src="https://img.shields.io/badge/status-alpha-F59E0B">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776AB">
  <img alt="代码差异 schema 0.2" src="https://img.shields.io/badge/code--diff%20schema-0.2-0F766E">
</p>

![change-audit 封面](./docs/assets/change-audit-cover.png)

`change-audit` 把本地 Git diff 的审查结果收口成两个可保存、可核对的文件：经过校验的 `audit.json` 和自包含的 `audit.html`。每条参与计分的问题都必须回到真实修改行；审查不完整、格式错误或执行失败时，报告会如实标出。

> [!IMPORTANT]
> 当前仓库是本地 Alpha（`0.1.0a0`），尚无 PyPI 包、发布 tag 或 `change-audit` console script。以下步骤基于本地 checkout，并使用 `python -m change_audit`。

## 你会得到什么

| 产物 | 作用 |
|---|---|
| `audit.json` | 经过校验的机器真相源，保存完整可信 hunk 和图关系。 |
| `audit.html` | 自包含中文报告，展示有界代码证据、真实修改行标记和本地决策控件。 |
| `audit-feedback.jsonl` | 可选的人工判断导出；当前 Alpha 不消费反馈，也不自动改代码。 |

产品遵守三个核心约束：

- Python 会用准备阶段解析出的 Git diff 核对 finding；审查者不能凭空生成可信路径、hunk、ID、fingerprint 或评分。
- JSON 与 HTML 通过全部门禁后成对发布；硬失败不会留下看起来像成功的半套报告。
- `complete` 只表示审查者完整返回了输出协议，不代表行为覆盖完整，更不代表“找到了全部 bug”。

## 查看真实报告

仓库内的 [Fireworks Tech Graph dogfood](./docs/examples/dogfood-fireworks-tech-graph/) 是实现完成后使用以下固定范围重新生成的真实报告：

```text
d5ef26deac6b1ed37ee9b89b52dddb1bcaac6c24..9a64e5a926d430a421a71b5cf433b0553876db28
```

该范围包含 21 个文件、52 个 hunk；最终 7 条 finding 全部锚定到真实新增行，未计分 finding 为 0。报告状态是 `complete + concerns`，同时如实保留了部分意图覆盖和 `0.65` 的 pack 完整度诊断。

- 打开[自包含 HTML 报告](./docs/examples/dogfood-fireworks-tech-graph/audit.html)。
- 核对[机器真相源 audit.json](./docs/examples/dogfood-fireworks-tech-graph/audit.json)。
- 阅读[生成记录](./docs/examples/dogfood-fireworks-tech-graph/README.md)与[同源基线对比](./docs/examples/dogfood-fireworks-tech-graph/baseline-comparison.md)。

这份样张证明真实生成链路已经落地，不代表审查者发现了该范围内的全部缺陷。

## 本地快速开始

需要 Git、Python 3.10 或更高版本，以及能够运行本地 Agent Skill 并创建隔离审查上下文的 AI host。

```bash
git clone https://github.com/evidentloop/change-audit.git
cd change-audit
python3.11 --version       # 可替换为任意已安装的 Python >=3.10
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m change_audit --help
```

使用宿主的本地 Skill 机制注册完整的 [`integrations/agent-skill/change-audit/`](./integrations/agent-skill/change-audit/) 目录。不要只复制 `SKILL.md`：同一目录还包含宿主元数据。当前 Alpha 尚未提供经过验证的跨宿主安装器，也没有维护者发布的固定 tag 可用于外部安装。

进入要审计的 Git 仓库后，对宿主说：

```text
帮我用 change-audit 审计 staged changes，并生成 HTML 报告。
```

也可以使用英文：

```text
Use change-audit to audit my staged changes and generate the HTML report.
```

Skill 会核对包与 schema 兼容性，准备可信 workspace，只把生成的审查 prompt 交给隔离宿主审查者，再校验并发布正式产物对，最后返回报告路径。当前报告 UI 和审查语义正文使用简体中文；支持英文自然语言触发不等于已经支持英文报告本地化。

## 工作原理

```text
自然语言请求
  → Agent Skill 确认仓库与 diff 范围
  → Python prepare 冻结 Git 证据和 prompt provenance
  → 隔离宿主审查者返回语义 finding
  → Python 核对真实修改行并构建 Audit Graph
  → schema、语义、回链和 HTML 全部门禁通过
  → audit.json + audit.html 成对发布
  → 用户可选导出浏览器本地反馈
```

![change-audit 架构](./docs/assets/change-audit-architecture.png)

默认 Python 路径不调用模型 SDK，也不管理 API key。diff、源码、注释、文件名与审查输出都按不可信数据处理，审查载荷中的命令不会被执行。

## 宿主集成命令

普通用户应优先使用 Skill。宿主集成者可以直接使用三个模块命令：

```bash
# 1. 创建隐藏 staging workspace，并输出 JSON locator。
python -m change_audit prepare --diff staged --out audit/20260710_example

# 2. 宿主在全新隔离上下文中打开 locator.prompt_path，
#    再把审查者原始响应完整写入 locator.raw_analysis_path。

# 3. 校验并发布正式产物对；最终目录必须尚不存在。
python -m change_audit finalize --out audit/20260710_example

# 从已有、已校验的 JSON 产物独立重渲染。
python -m change_audit render \
  audit/20260710_example/audit.json \
  --out audit/20260710_example/audit.html
```

`review` 是 Skill 的用户动作，不是 Python 命令。`prepare` 与 `finalize` 不能被理解成可直接连跑的双命令快捷方式：两者之间必须由隔离宿主审查者写入原始结果。显式 `render --out` 只授权替换对应 HTML，永远不会修改 `audit.json`。

公共 Python 入口位于 `change_audit.api`：

```python
from change_audit.api import finalize_review, prepare_local_diff, render_audit_file
```

Locator 契约、失败处理、prompt 数据边界与安装授权规则见 [AI host 集成文档](./docs/ai-host-integration.md)。

## 当前范围

| 能力 | Alpha 状态 |
|---|---|
| 本地 Git `staged`、`unstaged`、ref 和 range diff | 已实现 |
| 新增、修改、删除、重命名与二进制文件元数据 | 已实现 |
| `code_diff` schema 与自包含 HTML | 版本 `0.2` |
| 精确新增/删除行锚点与有界可信 hunk 片段 | 已实现 |
| 完整、部分、失败和不确定状态 | 已实现 |
| 浏览器本地决策与 JSONL 导出 | 已实现；尚不消费 |
| Codex 端到端 dogfood | 已在上述 Fireworks 范围完成 |
| Qoder 模型级 smoke | 延后人工验证；本轮不宣称通过 |
| 报告语言 | v0 为简体中文 |
| Folder diff、无 diff 文件审查、远程 PR URL | 不支持 |
| 自动修复、执行命令、消费反馈 | 不支持 |
| PyPI、发布 tag、console script | 尚未发布 |

内部 `change_audit.review` 的长期方向是 artifact-general，但新产物类型只有具备 adapter、可信 anchor、eval baseline 和 renderer profile 后，才成为正式审计 profile。Schema `0.2` 仅对应 code-diff profile。

## 开发验证

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m ruff check .
python -m build
```

常用文档：

- [v0 范围](./docs/v0-scope.md)
- [数据模型](./docs/data-model.md)
- [AI host 集成](./docs/ai-host-integration.md)
- [Hunk 渲染参考](./docs/examples/hunk-context-demo/)
- [Fireworks 真实 dogfood](./docs/examples/dogfood-fireworks-tech-graph/)

## License

本项目采用 [MIT License](./LICENSE)。
