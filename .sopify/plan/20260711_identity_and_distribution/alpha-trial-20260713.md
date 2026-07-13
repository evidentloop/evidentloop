# Wave 4.3 外部 Alpha 试跑证据

日期：2026-07-13

状态：首次试跑的核心审计链路通过但 provenance 不一致；随后固定产物复跑通过 provenance 核对，却在首次安装和自然语言 discovery 暴露阻塞。4.3 未关闭，`74c7d16` 候选已退役，新候选须在最小修复 commit 后重新冻结。

## 首次试跑：核心链路通过但 provenance 不一致

- 候选 commit：`e05db143e4f3ee540b7d788f40b99f316369c991`
- wheel SHA-256：`3c108b4081393e8b30e8acd6e4dd5da855e6164942c21e63548d1939e411370a`
- 环境：macOS `15.6.1`（`24G90`）/ arm64 / Python `3.11.15` / uv `0.11.28` / Codex CLI `0.144.3` / Node.js `20.20.2` / skills CLI `1.5.16`
- 首次安装耗时：未使用独立计时器；CLI 与 Skill 的落盘完成时间相差约 13 秒，该值不代表完整安装耗时。
- 一句话到报告耗时：未记录端到端起始时间；隔离 reviewer JSONL 完成到正式报告落盘约 21 秒。
- 结果：核心链路通过；Codex CLI `0.144.3` 的隔离能力已接受，4.3 只因候选产物 provenance 与精确耗时缺口保持未关闭。
- `review_status / verdict`：`complete / inconclusive`
- 报告计数：风险分未评分，finding `0`，open finding `0`，unscored finding `0`
- 隔离证据：orchestrator 与 reviewer thread ID 非空且不同；禁止事件 `0`；最终 `agent_message` `1`；`turn.completed` `1`；reviewer 空工作目录未变化；临时 HOME、`CODEX_HOME` 与工作目录在 `finalize` 前删除。
- 正式产物：`audit.json` 与 `audit.html` 同目录；schema `0.3`；run ID 与 locator 一致；最终目录不含 `.run/`，隐藏 staging 已删除。
- 阻塞位置：产品审计链路无阻塞。当前受限宿主默认 npm cache 不可写，复查 skills CLI 时改用临时 cache 后成功；该问题未影响已安装 Skill 的审计。
- 最容易误解的一步：隔离验证示例把检查条件写成注释但没有执行断言；同时 Codex JSONL 的最终文本位于 `item.text`，不是顶层 `text`，原提取命令会失败。
- 其他脱敏反馈：`codex 0.144.3` 在关闭全部工具、插件、MCP、浏览器、计算机使用、图像生成与多智能体后可完成独立 reviewer；运行中出现模型列表刷新超时日志，但 reviewer 和正式报告仍成功完成。

## 固定产物复跑：provenance 通过但 discovery 阻塞

- 候选 commit：`74c7d16887a69de5c5f1f6e8ada6ac3ff9427088`
- source archive SHA-256：`ad3cc339da7d15281143518513790d84e13910dc43caa7695447a2c9222116dc`
- wheel SHA-256：`a12e26fb311513901fb8c56dbc4a12ce6f02c977d37a41248baff1fe75112c18`
- 环境：macOS `14.0` / arm64 / Python `3.11.13` / uv `0.11.3` / Codex CLI `0.144.3` / Node.js `20.20.0` / skills CLI `1.5.16`
- 固定产物：通过；commit、archive SHA-256 与 wheel SHA-256 全部匹配。
- 首次安装：原命令未绑定已经记录的 Python 3.11，uv 误选 Python `3.9.7` 后阻塞；补 `--python 3.11` 重试后 7 秒安装成功。该 7 秒是重试安装耗时，不伪称原命令首次成功。
- 一句话审计：74 秒后停在 discovery；orchestrator thread 已存在，reviewer 未启动，正式 `audit.json` / `audit.html` 为 `0`，`.run/` 为 `0`。
- 根因：Skill 声明全程使用同一 `<PYTHON>`，但没有解释器解析规则，宿主转而使用系统 `python3`；失败分支随后扫描用户目录并提议从维护仓库 editable install，破坏固定产物 provenance。
- 最容易误解的一步：记录 Python 3.11 不代表 uv 会自动选择它，Skill 也不能假设系统 `python3` 是 uv tool 的解释器。
- 修复边界：安装命令绑定实际 Python 3.11；Skill 从 PATH 的仓库外 console script 启动 doctor，清除 Python import-path 覆盖；`doctor --json` 返回当前 `sys.executable`，后续以原始虚拟环境路径和 `-I` 运行 module CLI；禁止扫描用户目录或推断 editable source。
- 结论：4.3 未通过，`74c7d16` 候选退役；先完成最小修复并冻结新产物，再由外部试用者复跑。不得勾选 4.3，也不得进入 4.4。

## 修复输入（尚未进入 Wave 4.4）

1. 将隔离事件检查实现为失败即停止的脚本，不再只保留注释。
2. 按 `item.completed.item.type == "agent_message"` 提取 `item.text`，并强制校验只有一个最终消息和一个 `turn.completed`。
3. 在试跑脚本中自动记录首次安装及一句话到正式报告的端到端耗时。
4. Codex CLI `0.144.3` 已纳入支持范围；`0.144.1` 只保留为历史实测证据。Skill 和集成文档改为 capability gate，不精确要求某个 Codex CLI 版本，也不把两个离散实测版本包装成连续版本区间。
5. 区分受限宿主的 npm cache 权限问题与产品安装问题；需要时允许为版本探针指定临时 cache。

## 已退役的最小复跑候选

- source commit：`74c7d16887a69de5c5f1f6e8ada6ac3ff9427088`
- source archive：`source-74c7d168.tar`
- source archive SHA-256：`ad3cc339da7d15281143518513790d84e13910dc43caa7695447a2c9222116dc`
- wheel：`evidentloop-0.1.0a0-py3-none-any.whl`
- wheel SHA-256：`a12e26fb311513901fb8c56dbc4a12ce6f02c977d37a41248baff1fe75112c18`
- 本地预检：archive commit ID、Skill、prompt、wheel 完整性、隔离安装、兼容探针、doctor、module CLI 与 demo 均通过。
- 外部状态：已执行但未通过；固定 provenance 正确，安装与 discovery 阻塞，4.3 保持待办。

新候选必须来自包含最小修复的准确 source commit；dirty tree 构建物不得作为固定候选。source commit、archive SHA-256 与 wheel SHA-256 需在修复 commit 和 clean build 后另行记录。

## 隐私边界

本记录不包含试用仓库路径、`python_executable` 等本机绝对路径、源码、diff、prompt、raw analysis、报告文件、凭据、代理配置或完整 thread ID。
