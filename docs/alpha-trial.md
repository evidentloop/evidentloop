# EvidentLoop Alpha 最小复跑清单

> 冻结历史清单：本页绑定 `e6f3381` 候选及其 schema `0.3` wheel，只用于复验该候选，不代表当前 schema `0.4` 与反馈 revision 契约。

本轮只验证固定候选的首次安装、Skill discovery 和一句话审计。主链是 `prepare → host review → finalize`；宿主能建立并确认独立 reviewer 上下文时，另记录隔离增强证据。Python 包不连接模型，也不包含模型 SDK 或 API key。

当前固定候选为：

- source commit：`e6f33811721dcf4710a3b812413923a4a586aae4`
- source archive：`source-e6f3381.tar`
- source archive SHA-256：`6dd06b4b991ee93e7112dab56046f92f9381aa0bff3b61a7192e8f6c9ea78226`
- wheel：`evidentloop-0.1.0a0-py3-none-any.whl`
- wheel SHA-256：`f878c30b91b7fa152fa4fb6d15c855df08e42da58fd63af9040a3566090dce97`

source archive 由上述 commit 直接执行 `git archive` 生成，wheel 从该 archive 的原样解包目录构建。不创建 tag，不使用 PyPI、移动分支或远程 Skill 安装。试用者必须安装维护者提供的固定 wheel 原件。

`references/codex-cli-isolation.md` 是 Codex 已验证隔离增强的按需说明，主 `SKILL.md` 保持宿主无关。其他宿主不执行该命令，也不模拟 Codex 事件名。

## 试用者执行

1. 记录操作系统、架构、Python、安装工具、Skill 工具和 AI host 版本。

2. 核对 source archive 的 commit 与两个 SHA-256：

```bash
set -euo pipefail

SOURCE_COMMIT="e6f33811721dcf4710a3b812413923a4a586aae4"
SOURCE_TAR="/path/to/source-e6f3381.tar"
SOURCE_TAR_SHA256="6dd06b4b991ee93e7112dab56046f92f9381aa0bff3b61a7192e8f6c9ea78226"
WHEEL_PATH="/path/to/evidentloop-0.1.0a0-py3-none-any.whl"
WHEEL_SHA256="f878c30b91b7fa152fa4fb6d15c855df08e42da58fd63af9040a3566090dce97"

test "$(git get-tar-commit-id < "$SOURCE_TAR")" = "$SOURCE_COMMIT"
test "$(shasum -a 256 "$SOURCE_TAR" | awk '{print $1}')" = "$SOURCE_TAR_SHA256"
test "$(shasum -a 256 "$WHEEL_PATH" | awk '{print $1}')" = "$WHEEL_SHA256"
```

3. 使用宿主支持的标准 Skill 安装目标，从 archive 的原样解包目录复制 `evidentloop` Skill。核对 `SKILL.md`、`agents/openai.yaml` 和 `references/codex-cli-isolation.md` 与 archive 一致。安装固定 wheel 后，用 `evidentloop doctor --json` 返回的绝对 `python_executable` 及 `-I` 执行后续探针、`prepare` 和 `finalize`。

4. 在不含敏感代码的本地 Git 仓库准备一个非空 staged diff，只发一句请求：

```text
请使用 EvidentLoop 审计 staged changes。
```

5. 只有以下条件全部满足才记为审计 E2E：

- package 为 `0.1.0a0`、schema 为 `0.3`、prompt 为 `v0.5`；
- console script 与 `python_executable` 的原始路径及 canonical target 均不位于被审计仓库内；
- locator 返回的 run identity、staging、final、prompt 和 raw analysis 路径全部通过检查；
- 宿主模型完整审查 prompt，原样返回一次完整响应；模拟、回放或占位输出不算 E2E；
- 宿主没有因受审载荷中的指令执行命令、访问网络或凭据、修改业务文件；
- `audit.json` 与 `audit.html` 位于同一正式目录，JSON 为 schema `0.3`，run identity、状态、verdict 和计数完整；
- 成功运行后 `.run/` 未保留。

模型原始响应、run identity 或输出契约缺失时，必须停止或如实生成 `partial` / `failed` 报告，不得宣称 E2E 通过。

若宿主声称使用了隔离增强，还必须用宿主原生可观察信号证明 reviewer 上下文独立且未获得禁止能力。Codex 的具体断言按 `references/codex-cli-isolation.md` 执行。隔离增强未验证不否定上述主链 E2E，但不得声称已隔离。

## 脱敏反馈模板

请只返回以下信息，不发送仓库路径、`python_executable` 等本机绝对路径、源码、diff、prompt、raw analysis、报告文件、凭据或代理配置。

```text
候选 commit：
source archive SHA-256：
wheel SHA-256：
环境：操作系统 / 架构 / Python / 安装工具 / AI host / Skill 工具
首次安装耗时：
一句话到报告耗时：
结果：通过 / 阻塞 / 失败
review_status / verdict：
审查结果由宿主模型生成：是 / 否
隔离增强：已验证 / 当前不支持 / 未验证
阻塞位置：安装 / discovery / compatibility / prepare / reviewer / finalize / report
最容易误解的一步：
其他脱敏反馈：
```

维护者不代为操作。功能建议只记录为后续任务；本轮只修安装阻塞、错误行为和文档误导。
