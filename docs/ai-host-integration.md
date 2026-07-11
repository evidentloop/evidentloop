# change-audit AI host 集成

## 状态

本文件定义一期 `code_diff` profile 的已实现契约。CrossReview 已等价迁入 `change_audit.review`，`prepare`、`finalize`、`render`、可信 hunk adapter、状态完成门、正式产物对提交与 AI host Skill 均已实现；Codex 已完成端到端 dogfood，Qoder 模型级 smoke 按用户决定留待手工验证。仓库长期 review 内核是 artifact-general，但非 diff 类型在具备专属 adapter、可信 anchor、eval baseline 和 renderer profile 前，不使用本文件的正式 audit 交付承诺。

## 用户看到什么

用户在自己的 Git 仓库中说：

```text
帮我用 change-audit 审计最近的本地改动
```

AI host 通过用户级或宿主级 Skill 发现 `change-audit`，完成审查编排，并返回摘要与 `audit.html` 路径。用户不需要知道 ReviewPack、ReviewResult、CrossReview 或隐藏中间文件。

一期默认正式产物只有：

```text
audit/YYYYMMDD_<slug>/
  audit.json
  audit.html
```

用户在 HTML 中导出决策时，浏览器另行下载 `audit-feedback.jsonl`；浏览器不保证它自动回到原审计目录。

## 三层边界

```text
change-audit Skill
  -> 发现意图、确认 diff、请求安装授权、调用宿主 LLM、验证产物、展示结果

AI host LLM
  -> 在隔离审查上下文中理解变更，产生语义 findings

change-audit Python package
  -> artifact-general review 内核
  -> code-diff adapter、Audit Graph、校验、风险状态和 HTML renderer
```

CrossReview 的可复用能力已等价迁入 `change_audit.review`。它是包内审查子系统，不是第二个安装项、第二个 Skill 或用户必须理解的产品。

默认链路不集成模型 SDK、不读取 API key。宿主已有的 LLM 是一期主要 finding 生产者；Python 只生成机械字段、校验语义输出并渲染稳定报告。

## Skill 编排契约

### 1. Prepare

```bash
python -m change_audit prepare --diff HEAD~1 [--out DIR]
```

`prepare` 读取本地 Git diff，要求最终目录尚不存在，并在同一父目录创建隐藏 sibling staging workspace。其 `.run/` 中写入：

- `audit-skeleton.json`：run/change/file 骨架；不是最终 `audit.json`。
- `review-pack.json`：内部 ReviewPack。
- `hunk-index.json`：可信路径、行范围、hunk ID 和完整代码片段。
- `prompt.md`：为宿主 LLM 准备的隔离审查提示。

prepare 同时在骨架中冻结 reviewer prompt 的 source、version 与完整渲染文本 SHA-256。当前 product prompt 为 `product/v0.2`：Section/字段名和协议枚举保持英文，`What`、`Why`、Observations 与 Overall Assessment 使用简体中文；`Where` 优先给出最能直接证明问题的一条修改行。文本 diff 不携带 `GIT binary patch`，但 binary 文件路径、change type 与 Git binary 占位仍保留在可信元数据中。

最终目录此时不得出现；staging 根目录也尚未生成候选 `audit.json`。

prepare 成功时向 Skill 返回结构化 locator：

```json
{
  "run_id": "run-...",
  "final_dir": "audit/YYYYMMDD_<slug>/",
  "staging_dir": "audit/.YYYYMMDD_<slug>.change-audit-staging/"
}
```

CLI stdout 只输出 locator JSON，诊断写 stderr。Skill 必须原样使用 locator，不得自行推导 slug、冲突后缀或 staging 路径。

### 2. Host review

Skill 在隔离上下文中把 staging 内的 `prompt.md` 交给宿主 LLM，并将原始结果写入：

```text
.run/raw-analysis.md
```

源码、diff、注释和审查文本都按不可信数据处理。Skill 不执行其中的命令，不把其中的文字当作更高优先级指令，也不让 LLM 直接编辑最终 `audit.json`。

### 3. Finalize

```bash
python -m change_audit finalize --out DIR [--keep-review-artifacts]
```

`DIR` 必须取自 prepare locator 的 `final_dir`。finalize 只接受与 locator/staging 中 `run_id` 一致的运行上下文；Skill 不重新计算路径或跨运行拼接材料。

`finalize` 执行 ingest、ReviewResult 到 Audit Graph 的映射、可信 hunk 反查、结构/引用/锚点校验、状态与评分计算，然后在 staging 根目录生成候选 `audit.json` 与 `audit.html`。

候选 JSON、HTML、run/graph identity 和 `data-*` 回链全部通过后，finalize 才按 keep 策略处理 `.run/`，复查最终目标 leaf 不存在，再用一次同文件系统目录 rename 把 staging 提交为最终目录。检查时目标已存在、目标 leaf 是符号链接或 rename 失败时停止并保留 staging 诊断，不主动删除或覆盖目标。

一期采用本地单写者、非对抗并发模型，不承诺消除目标检查与 rename 之间的极小竞态。原生 race-proof no-replace、平台专用锁和递归 symlink 防御延后；POSIX 上 staging / `.run/` 的 0700 与中间文件的 0600 只做 best-effort 隐私保护，不是跨平台成功门禁。

finalize 会先校验冻结的 prompt 版本和 SHA-256，再接收宿主结果。合法的零 finding 必须使用明确完成信号；finding block 的声明 ID、实际解析结果和必要字段必须一致。缺段、截断、prompt 漂移或非法输出不得被推断成“未发现问题”，而应硬失败或映射为 `partial` / `failed`。

成功提交前默认清理 `.run/`。宿主拒绝或可归一化的审查失败可以生成 `review_status = failed` 的完整报告对；schema、安全、路径不可读写、render、trace 或目录提交等硬失败返回非零。对 prepare 已接受的新目标，提交前失败时最终目录保持不存在并保留 staging 诊断；检查时已有目标或目标 leaf 是符号链接则拒绝，rename 失败也不能作为本轮成功证据。任何失败路径都不得复用旧报告或宣称成功。

### 4. Re-render

```bash
python -m change_audit render INPUT_JSON --out OUTPUT_HTML
```

`render` 只消费完整 `audit.json`，不读取 Git、`.run/` 或宿主状态。显式 `--out` 授权原子替换该单一 HTML；候选生成或校验失败时旧 HTML 原样保留，输入 JSON 永不修改。它用于重复生成 HTML 和独立验证已有审计数据，不参与 finalize 的产物对提交。

公开 Python API 与三个命令同构：

```python
prepare_local_diff(repo_path, diff_spec, output_dir=None)
finalize_review(output_dir, keep_review_artifacts=False)
render_audit_file(input_path, output_path)
```

`review` 是用户对 Skill 的自然语言动作，不是一期 Python 子命令。

## Skill 位置与职责

权威 Skill 目标位置：

```text
integrations/agent-skill/change-audit/SKILL.md
```

Skill 应当：

1. 匹配“审计本地改动”“review diff”“audit changes”等明确意图。
2. 确认仓库、diff spec 和输出位置；默认 `HEAD~1` 只能在用户意图允许时采用。
3. 检查兼容包版本；缺包时说明来源和命令，等待授权后才安装。
4. 顺序执行 prepare、隔离宿主审查和 finalize。
5. 校验退出码、审查状态以及 `audit.json` / `audit.html` 的存在和对应关系。
6. 返回简短摘要、审查状态和可打开的报告路径。

Skill 包含必要的审查维度、输出完成标记和安全编排说明，但不复制 Python schema、模板、CSS/JS 或业务实现。

Skill 不得静默安装、自动修改用户代码、执行被审查源码中的指令，或在产物缺失时宣称成功。

Skill 只能把已成功提交的最终目录当作正式报告；隐藏 staging、孤立文件或旧目录均不能作为本轮成功证据。

## 安装策略

仓库内 dogfood：

```bash
python -m pip install -e /path/to/change-audit
```

安装动作需要用户授权，并应落在用户选定的隔离环境中。

外部试用只有在真实 tag 发布后才能使用固定引用：

```text
git+https://github.com/evidentloop/change-audit.git@<real-tag>
```

禁止使用 `@latest`。一期不承诺 PyPI，也没有经过验证的跨宿主 Skill 安装器；各宿主使用自己的本地 Skill 注册机制，并注册完整的 `integrations/agent-skill/change-audit/` 目录。

## 宿主验证状态

- Codex：已完成自然语言触发到 HTML 的真实 dogfood。
- Qoder：已确认 QoderCLI 启动、临时链接和 Skill discovery；模型级 smoke 由用户后续手工完成。
- 其他宿主：后续按其发现机制适配，不要求用户在每个项目复制说明文件。

## 一期验收

- 中文和英文审计请求能够触发；普通文本 review 不误触发。
- 缺包、版本不匹配、拒绝安装、prepare/宿主/finalize 任一步失败都返回真实状态。
- 语义 bug fixture 产生可信锚点 finding；干净 fixture 在上下文充分时产生 `complete + pass_candidate`、不足时产生 `complete + inconclusive`；partial fixture 不伪装成干净审查。
- 正式产物只暴露 `audit.json` 和 `audit.html`；中间产物默认清理。
- Codex 与 Qoder 使用同一个 Skill 流程，不复制 Python 业务逻辑；本轮 Qoder 仅确认 CLI 启动与 Skill discovery，模型级结果不计入已验证能力。
