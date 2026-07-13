# EvidentLoop 外部 Alpha 最小复跑清单

本轮在 macOS arm64、Python 3.11、Codex CLI `0.144.3` 上只复跑首次安装与一句话审计的产物 provenance 和耗时。`0.144.3` 的隔离链路已经验证并纳入支持范围；Codex CLI 版本只记录实测环境，不作为精确门禁，真正门禁是可观察的隔离信号和失败即停止的断言。

这是 Codex 专项 Alpha 验收清单，不是 EvidentLoop 的模型依赖契约。产品通用契约只要求 AI host 创建使用自身模型能力的隔离 reviewer 上下文；其他宿主应使用满足同一可观察门禁的原生隔离能力，不应启动 `codex exec`。Python 包不连接模型，也不包含模型 SDK 或 API key。

当前固定候选为：

- source commit：`2cb03afe5d8269b16a2a61541470fe5755974347`
- source archive：`source-2cb03af.tar`
- source archive SHA-256：`eef49d851b981a249978787d2a70f9a19cd49841f3d92e76f430b27a5342b461`
- wheel：`evidentloop-0.1.0a0-py3-none-any.whl`
- wheel SHA-256：`6dc755a75a055dd90c93d4e60498742a3537cc98d2cdbad84dcdd70089650b3d`

source archive 由上述 commit 直接执行 `git archive` 生成，wheel 从该 archive 的原样解包目录构建。不创建 tag，不使用 PyPI、移动分支或远程 Skill 安装。试用者必须安装维护者提供的固定 wheel 原件；即使现场重建 wheel 的内部文件内容相同，只要 SHA-256 不同，也不能替代上述固定产物。

候选 Skill 中的 Codex 隔离步骤标题保留首次实测版本 `0.144.1`，正文门禁并未比较 CLI 版本；本轮在 `0.144.3` 上执行相同能力探针。标题收口属于 4.4，不改变本次候选产物。

截至 2026-07-13，用户已认可无维护历史的 AI 执行者可作为本轮外部试用者，但不把它记录成外部真人可用性研究。上一候选的 attempt 1 在生成报告后才发现 post-doctor 解释器和 pre-finalize thread gate 未执行；attempt 2 因错误收窄 hidden-sibling 断言而在 prepare 后 fail closed。两次均为 strict failure。当前候选只明确这三个已有 Skill gate，等待新的 4.3 复跑。

## 试用者执行

1. 记录环境版本，不修改维护者提供的文件：

```bash
sw_vers
uname -m
PYTHON_PATH="$(command -v python3.11)"
test -n "$PYTHON_PATH"
"$PYTHON_PATH" --version
uv --version
codex --version
node --version
npx skills@1.5.16 --version
```

2. 核对 source archive 的 commit 与两个 SHA-256，再从该 archive 安装 CLI 和 Skill：

```bash
set -euo pipefail

SOURCE_COMMIT="2cb03afe5d8269b16a2a61541470fe5755974347"
SOURCE_TAR="/path/to/source-2cb03af.tar"
SOURCE_TAR_SHA256="eef49d851b981a249978787d2a70f9a19cd49841f3d92e76f430b27a5342b461"
WHEEL_PATH="/path/to/evidentloop-0.1.0a0-py3-none-any.whl"
WHEEL_SHA256="6dc755a75a055dd90c93d4e60498742a3537cc98d2cdbad84dcdd70089650b3d"
PYTHON_PATH="$(command -v python3.11)"

test -n "$PYTHON_PATH"
test "$(git get-tar-commit-id < "$SOURCE_TAR")" = "$SOURCE_COMMIT"
test "$(shasum -a 256 "$SOURCE_TAR" | awk '{print $1}')" = "$SOURCE_TAR_SHA256"
test "$(shasum -a 256 "$WHEEL_PATH" | awk '{print $1}')" = "$WHEEL_SHA256"
SOURCE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/evidentloop-alpha.XXXXXX")"
tar -xf "$SOURCE_TAR" -C "$SOURCE_DIR"

INSTALL_STARTED_AT="$(date +%s)"
uv tool install --force --python "$PYTHON_PATH" "$WHEEL_PATH"
npm_config_cache="$(mktemp -d "${TMPDIR:-/tmp}/evidentloop-npm.XXXXXX")" \
  npx skills@1.5.16 add "$SOURCE_DIR" \
  --skill evidentloop --agent codex -g --copy -y
EVIDENTLOOP_CLI="$(command -v evidentloop)"
case "$EVIDENTLOOP_CLI" in /*) ;; *) exit 1 ;; esac
DOCTOR_JSON="$(env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 "$EVIDENTLOOP_CLI" doctor --json)"
printf '%s\n' "$DOCTOR_JSON"
EVIDENTLOOP_PYTHON="$(printf '%s\n' "$DOCTOR_JSON" | "$PYTHON_PATH" -I -c 'import json, os, sys; value = json.load(sys.stdin)["python_executable"]; assert isinstance(value, str) and os.path.isabs(value); print(value)')"
test -x "$EVIDENTLOOP_PYTHON"
"$EVIDENTLOOP_PYTHON" -I -m evidentloop --help >/dev/null
INSTALL_SECONDS="$(( $(date +%s) - INSTALL_STARTED_AT ))"
printf 'install_seconds=%s\n' "$INSTALL_SECONDS"
```

3. 在不含敏感代码的本地 Git 仓库准备一个非空 staged diff。发送请求前记录 `date +%s`，正式报告生成后再次记录并计算耗时，然后只发一句请求：

```text
请使用 EvidentLoop 审计 staged changes。
```

4. 只有以下条件全部满足才记为走通。thread、事件和目录检查必须实际执行断言并在不满足时返回失败；注释、目测或仅打印计数不能替代断言。从 `doctor` 输出取得 `EVIDENTLOOP_PYTHON` 后，所有 Python 驱动的 JSON、JSONL、路径、文件和报告断言都使用该精确路径与 `-I`，不再调用系统 Python，也不依赖未声明的 `jq`：

- package 为 `0.1.0a0`、schema 为 `0.3`、prompt 为 `v0.4`；
- `doctor --json` 返回非空绝对 `python_executable`，该路径可以用 `-I -m evidentloop` 驱动后续兼容探针、`prepare` 与 `finalize`；
- console script 与 `python_executable` 的原始路径及 canonical target 均不位于被审计仓库内；
- `staging_dir` 与 `final_dir` 的 canonical parent 相同，且 staging basename 以 `.` 开头；不得额外假设 staging basename 必须精确等于 `.` 加 final basename；
- orchestrator 与 reviewer 的 `thread.started` ID 非空且不同，且该比较必须在 `finalize` 前实际断言；
- reviewer JSONL 恰有一个最终 `item.completed.item.type == "agent_message"` 和 `turn.completed`，最终文本从 `item.text` 提取，没有工具、命令、文件修改或协作事件；
- reviewer 的空工作目录没有产生文件；
- 临时 HOME、`CODEX_HOME` 和工作目录已在 `finalize` 前删除；
- `audit.json` 与 `audit.html` 位于同一正式目录，JSON 为 schema `0.3`、`review_status=complete`，状态与计数完整；`runs[0].id` 和 `extensions.evidentloop.run_id` 均等于 locator run ID，不假设存在顶层 `run_id`；
- 成功运行后 `.run/` 未保留。若任一隔离信号不可见或不满足，应停在 `finalize` 前并记录阻塞。

## 脱敏反馈模板

请只返回以下信息，不发送仓库路径、`python_executable` 等本机绝对路径、源码、diff、prompt、raw analysis、报告文件、凭据或代理配置。

```text
候选 commit：
source archive SHA-256：
wheel SHA-256：
环境：macOS / arm64 / Python / uv / Codex / skills CLI
首次安装耗时：
一句话到报告耗时：
结果：通过 / 阻塞 / 失败
review_status / verdict：
隔离证据：thread ID 是否不同；禁止事件数；空目录是否不变
阻塞位置：安装 / discovery / compatibility / prepare / reviewer / finalize / report
最容易误解的一步：
其他脱敏反馈：
```

维护者不代为操作。功能建议只记录为后续任务；本轮只修安装阻塞、错误行为和文档误导。
