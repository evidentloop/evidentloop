# Wave 4.3 外部试跑与 Wave 4.4 收口证据

日期：2026-07-13 至 2026-07-14

状态：多轮外部试跑已验证安装、discovery 与机械链路，并暴露 provenance、post-doctor 解释器、hidden-sibling 和宿主边界问题。`fc875c9` 的 Qoder 复跑使用模拟 raw analysis，只作为机械链路证据。产品契约已收口为一条宿主无关主链，隔离作为条件增强；prompt 为 `v0.5`，schema 为 `0.3`。Trae 手工集成 E2E 完成 4.3 后，`e6f3381` clean candidate 与 Codex 隔离增强回归通过，4.4 完成。

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

## `7d0bef6` 独立外部复跑：reviewer 上下文未建立

- 候选 commit：`7d0bef6a1cc5d405e4107995dd7aa035da10e4e8`
- source archive SHA-256：`569fe7fda6b37a990f16cf91d20360faedcecb7886000535c122824013855254`
- 固定 wheel SHA-256：`cf46af257f180fa67b345dbe413107bbf1d9f58790d4d9e6b4addb83afea9e69`
- 环境：macOS `14.0` / arm64 / Python `3.11.13` / uv `0.11.3` / Codex CLI `0.144.3` / Node.js `20.20.0` / skills CLI `1.5.16`
- provenance、隔离首次安装、兼容探针和 runtime discovery：通过；安装耗时记录值为 `4` 秒，未扫描用户目录，也未提出 editable install。
- reviewer：`203` 秒后失败收口；reviewer `thread.started`、最终 `agent_message` 与 `turn.completed` 均为 `0`，未执行 `finalize`，正式 `audit.json` / `audit.html` 为 `0`。
- 失败边界：本轮只证明外部环境没有建立有效 reviewer 上下文；不能从脱敏事件计数唯一定位宿主子进程的网络、认证、代理、CA 或启动配置根因。
- 清理：临时 HOME、`CODEX_HOME` 与工作目录现场无残留；reviewer 空目录后置断言未执行，EvidentLoop staging `.run/` 按失败诊断契约保留。
- harness 反馈：zsh 只读特殊变量 `status` 污染清理路径；该变量不在 tracked source 中，后续 runner 改用 `reviewer_rc` 并保存原始子进程退出码，不因此重建候选。
- 结论：`7d0bef6` 固定产物的安装与 discovery 缺口已关闭，但独立外部 reviewer 门禁未通过；4.3 保持待办。

## `7d0bef6` 维护者真实宿主冒烟验证：同源重建 wheel 走通

- source archive 与 Skill：精确匹配上述 `7d0bef6` 固定值。
- 实际 wheel SHA-256：`efb1e9fe7fd5df667f1b1a3f37887080536cde0922564cb9539fbaf2255d53aa`。它从同一 source archive 重建，与原冻结 `cf46af25…e9e69` wheel 的 `37` 个 ZIP entry 内容完全一致，仅 dist-info ZIP 时间戳不同；因此可证明 wheel 内容等价和功能链路，不冒充原固定 wheel 的字节 provenance。
- 宿主边界：这是一次真实 Codex CLI `0.144.3` E2E。当前 Codex Desktop 工具进程的默认 `workspace-write` 外层环境因网络 sandbox 阻止嵌套 reviewer；经用户明确授权，仅在无敏感内容的临时仓库放宽外层 sandbox 后通过。该事实不推广为 EvidentLoop 或其他 AI host 的通用要求。
- 记录耗时：隔离安装 `10` 秒，一句话到正式报告 `302` 秒。
- 报告：schema `0.3`，`complete / concerns`，风险分 `20`，open finding `1`，unscored finding `0`；样本中的 `count == 0` 除零问题被精确识别。
- 隔离证据摘要：orchestrator 与 reviewer thread ID 不同；reviewer 最终 `agent_message` `1`、`turn.completed` `1`、禁止事件 `0`；空工作目录未变化，临时 HOME、`CODEX_HOME` 与工作目录已删除。完整 reviewer 原始 JSONL 随临时目录清理，现有摘要支持手动试跑结论，但不能重新独立计算原始事件流。
- 正式产物：`audit.json` 与 `audit.html` 同目录；`runs[0].id`、`extensions.evidentloop.run_id` 与 locator 一致；最终目录不含 `.run/`。
- 试跑反馈：不得依赖未声明的 `jq`，统一使用已验证的 EvidentLoop Python 解释器和标准库解析 JSON/JSONL；报告不存在顶层 `run_id`。首次断言中断后完成了 Python 复核，因此本轮不是一次性无重试执行。
- 结论：真实宿主冒烟验证已通过；本轮由维护者执行且没有使用原冻结 wheel 字节，不能替代 4.3 的独立外部固定产物验收。

## `7d0bef6` 用户认可的 AI 外部试用：strict gate 未通过

- 执行者资格：用户明确认可无维护历史、只接收固定产物与清单的 AI 执行者可计作本轮外部试用者；证据不把它写成外部真人，也不据此声称已完成真人可用性研究。
- 固定 provenance：commit、source archive SHA-256 `569fe7f…5254`、原冻结 wheel SHA-256 `cf46af2…9e69` 与 tar 内 Skill 来源全部匹配。环境为 macOS `14.0` / arm64 / Python `3.11.13` / uv `0.11.3` / Codex CLI `0.144.3` / Node.js `20.20.0` / skills CLI `1.5.16`；transport capability probe 通过。
- attempt 1：首次安装 `171` 秒，一句话到正式报告 `410` 秒。正式报告为 schema `0.3`、`complete / inconclusive`，风险分未评分，finding/open/unscored 均为 `0`；线程事后复核为非空且不同，reviewer 禁止事件 `0`、空目录未变化、临时目录已清理。strict failure 是宿主在 `doctor` 后仍用系统 Python 执行六段断言，且只在 `finalize` 后比较两条 thread ID；正确产物不能倒推 finalize 前门禁已执行。
- 唯一重试：developer-instructions capability probe 与 reviewer transport probe 均通过；原冻结 wheel 安装 `190` 秒，宿主只使用 verified Python，并取得与外层 JSONL 一致的非空 `CODEX_THREAD_ID`。宿主随后把“同父目录且 basename 以 `.` 开头的 hidden sibling”错误收窄为 basename 必须精确等于 `.` 加 final basename，因合法 `.20260713_staged.evidentloop-staging` 不满足该错误断言，在 `241` 秒时 fail closed；reviewer 未启动，`finalize` 未执行，正式报告未生成，所以审计耗时为 `null`。
- 清理与证据：两次 trial 的 HOME、`CODEX_HOME`、样本仓库、source、cache 与 reviewer 临时目录均已删除；原始 JSONL、报告副本和机器摘要保存在本地固定产物证据目录，不含认证内容，未 commit/push。
- 结论：4.3 strict 验收不通过且本轮不再重试。已决定只明确 post-doctor verified Python、hidden-sibling 与 pre-finalize thread 三个已有 Skill gate；`7d0bef6` 因 Skill 变化不再作为下一轮候选。不得把本轮失败改写为通过，也不得进入 4.4。

## `2cb03af` Qoder 外部试跑：机械链路通过，隔离审查阻塞

- 环境：macOS `15.6.1`（`24G90`）/ arm64 / Python `3.11.15` / uv `0.11.28` / Codex CLI `0.144.3` / skills CLI `1.5.16`；实际执行宿主为 Qoder。
- provenance：source commit、archive SHA-256 与固定 wheel SHA-256 全部匹配；首次安装 `3` 秒，一句话到诊断产物 `86` 秒。
- 已验证：doctor 返回仓库外绝对解释器；package `0.1.0a0`、schema `0.3`、prompt `v0.4`；prepare locator、hidden sibling、run identity、finalize 机械链路、正式目录和 `.run/` 清理均符合预期。
- 阻塞：Qoder 当前未提供可确认独立 reviewer 上下文及禁止能力的原生方法；`codex exec`、thread ID、JSONL 和临时 HOME 不是 Qoder 必须复制的门禁。执行者已识别宿主能力限制，却仍写入 raw analysis 并调用 `finalize`，违反现有 Skill 的 pre-finalize fail-closed 规则。
- 诊断产物：`partial / inconclusive`，不能作为真实审计 E2E。`review_status=partial` 表示输出未满足 completion contract；`raw_findings_count=0` 且 `pack_completeness=0.65` 使内部 `advisory_verdict=inconclusive`，而正式 `verdict` 在 review status 非 complete 时直接保持 `inconclusive`。隔离状态不参与这些判定；原先将结果归因于 `**f-001**` 格式敏感是未经验证的错误判断。未保留可复核 raw output，因此无法进一步确定缺失的输出元素。
- 结论：本次作为 Qoder 受限兼容性证据，4.3 保持待办。后续纠偏不新增宿主 adapter、模型 SDK 或隔离证明协议；产品只分清通用能力契约、宿主证据映射和 Python runtime 责任。

## `2cb03af` 已退役候选

- source commit：`2cb03afe5d8269b16a2a61541470fe5755974347`
- source archive：`source-2cb03af.tar`
- source archive SHA-256：`eef49d851b981a249978787d2a70f9a19cd49841f3d92e76f430b27a5342b461`
- wheel：`evidentloop-0.1.0a0-py3-none-any.whl`
- 固定 wheel SHA-256：`6dc755a75a055dd90c93d4e60498742a3537cc98d2cdbad84dcdd70089650b3d`
- Skill 必须从该 source archive 复制，其 SHA-256 为 `708f7001f7cfc77416f3ccc6779c429008b70b6192f3bb476be8350ef0e8d723`。外部试用者必须安装上述固定 wheel 原件，不得现场重建或静默替换 SHA。
- 新 wheel 的 `37` 个 ZIP entry 与 `7d0bef6` 原冻结 wheel 内容完全一致；变化仅在 source archive 内的 Skill 和静态契约测试，不把本次修复扩张成 runtime 变更。
- 独立 `codex exec` 只是一种宿主证据映射，不是产品通用协议。其他宿主使用自身原生能力满足通用隔离契约；Python 包不连接模型，也不包含模型 SDK 或 API key。
- 4.3 已取得独立 AI 试用反馈但 strict gate 未通过。以上固定值只保留为历史 provenance，不得继续用于公开复跑。4.4 未开始。

## `fc875c9` 已退役候选

- source commit：`fc875c95eb8a2afdb8a6246a694b277d034c7d29`
- source archive：`source-fc875c9.tar`
- source archive SHA-256：`3f2e02ffac57941155d1a870d34061dd73cc552d7e7dcb78b7f28a92306e3744`
- wheel：`evidentloop-0.1.0a0-py3-none-any.whl`
- 固定 wheel SHA-256：`a192c7d626d7b639126d184b723df063f0f5d1023529754f1c8c97e798bd4161`
- 构建来源：archive 内 commit ID 与 source commit 一致；wheel 从该 archive 的原样解包目录构建。tar 内 `SKILL.md`、`agents/openai.yaml` 与 `references/codex-cli-isolation.md` 齐全，Skill 目录与候选提交逐文件一致。
- 本地验证：固定 wheel 原件在 Python 3.11 隔离环境安装成功；doctor、module CLI、依赖完整性与 package `0.1.0a0` / schema `0.3` / prompt `v0.4` 均通过；安装后 wheel SHA-256 未变。
- 验证基线：Python `328 passed`、Ruff、feedback JavaScript、Skill 规范校验与 diff check 通过。后续宿主契约收口与 prompt `v0.5` 使该候选退役，不得继续用于 4.3。

## `fc875c9` Qoder 外部复跑：固定候选机械链路通过

- 环境：macOS `15.6.1`（`24G90`）/ arm64 / Python `3.11.15` / uv `0.11.28` / skills CLI `1.5.16`；实际执行宿主为 Qoder，首次安装 `2` 秒。
- provenance 与 Skill 安装：source commit、source archive SHA-256、固定 wheel SHA-256 全部匹配；CLI 与 doctor 返回的解释器均位于被审计仓库外。skills CLI 在隔离 HOME 中完整安装 `SKILL.md`、`agents/openai.yaml` 和 `references/codex-cli-isolation.md`，三项与 source archive 逐文件一致；本项不证明 Qoder 已识别或触发该 Skill。
- 已验证机械链路：doctor、兼容版本、prepare locator、hidden sibling、prompt provenance、run identity、finalize 原子发布、schema `0.3`、自包含 HTML 和 `.run/` 清理均符合预期。
- reviewer 门禁：Qoder 当前未提供可确认独立 reviewer 上下文及禁止能力的原生方法。阻塞源于宿主当前能力无法满足通用契约，并非产品要求 `codex exec`、thread ID、JSONL 或临时 HOME 等 Codex 专属信号。
- 诊断产物：执行者在 reviewer 门禁不满足后注入模拟 raw analysis 并调用 `finalize`，违反现有 Skill 的 pre-finalize fail-closed 规则，因此不构成真实审计 E2E。`review_status=partial` 源于输出未满足 prompt `v0.4` completion contract；`raw_findings_count=0` 且 `pack_completeness=0.65` 使内部 `advisory_verdict=inconclusive`，正式 `verdict` 则因 review status 非 complete 保持 `inconclusive`；隔离状态不参与这些判定。
- 结论：本次只作为 Qoder 机械链路证据，不构成端到端审计。`fc875c9` 已退役，4.3 保持待办，4.4 未开始。

## 2026-07-14 宿主契约收口

- 产品只保留 `prepare -> host review -> finalize` 一条主链，不定义两种产品模式或两种正式产物。
- 宿主把完整 prompt 交给模型审查；模拟、回放或占位输出不构成端到端审计。
- 宿主能建立并确认独立 reviewer 上下文时使用隔离增强。隔离不是正式报告的前置条件，不进入产物，也不影响 `review_status` 或 `verdict`。
- prompt 升为 `v0.5`，public schema 保持 `0.3`。不新增 attestation、receipt、adapter、SDK、宿主注册表或 verdict 降级规则。
- 新候选冻结后，先由 Qoder 或 Trae 复跑主链，再由 Codex 回归隔离增强。Trae 主链结果已满足 4.3，Codex 回归转入 4.4。

## `00bfac7a` Wave 4.3 固定候选

- source commit：`00bfac7a4cbf1acdb1d637ef833feed165a77c04`
- source archive：`source-00bfac7a.tar`
- source archive SHA-256：`7f8df8a71aa4c806b902a024daa7dc3537a6b1cf9d0d3c3f9b64184636368fe7`
- wheel：`evidentloop-0.1.0a0-py3-none-any.whl`
- 固定 wheel SHA-256：`d0bdc57f0b065791bb7a4998c191bf7f5b3e338317f7851f8362ca7904ef8fd1`
- 构建来源：archive 内 commit ID 与 source commit 一致；wheel 从该 archive 的原样解包目录构建。
- 本地验证：Python `328 passed`、Ruff、feedback JavaScript、Skill 规范、SVG/XML 与 diff check 通过。固定 wheel 在 Python `3.11.15` 隔离环境安装成功；doctor、module CLI、demo、依赖完整性与 package `0.1.0a0` / schema `0.3` / prompt `v0.5` 全部通过；安装后 wheel SHA-256 未变。
- Skill 验证：标准 skills CLI `1.5.16` 在隔离 HOME 完整复制 `SKILL.md`、`agents/openai.yaml` 和 `references/codex-cli-isolation.md`，安装目录与 archive 逐文件一致。
- 状态：Trae 手工集成 E2E 通过，4.3 完成；4.4 clean candidate 已更新为 `e6f3381`。

## `00bfac7a` Trae 外部复跑：手工集成 E2E 通过

- 环境：macOS arm64 / Python `3.11.15` / pip / Trae CLI（GLM-5.2）；固定 wheel 安装约 `30` 秒，一句话到报告约 `2` 分钟。
- provenance：source commit、source archive SHA-256 和 wheel SHA-256 与当前固定候选一致；隔离 venv 的安装记录包含精确 wheel SHA-256。
- 主链：`prepare → host review → finalize` 通过，审查结果由 Trae 模型生成，未使用模拟、回放或占位输出。执行者确认未因受审载荷执行命令、访问网络或凭据、修改业务文件。
- 正式产物：schema `0.3`，`complete / inconclusive`，`risk_score=null`，finding/open/unscored/fix 计数均为 `0`；`pack_completeness=0.65` 与 advisory rationale 一致。run identity、节点与边计数、`.run/` 清理、自包含 HTML 和独立重渲染均已复核，重渲染结果字节一致。
- 宿主状态：本次手工读取候选 `SKILL.md` 编排，Trae 原生 Skill discovery 保持未验证；隔离增强为当前不支持或未验证。正式产物不声称隔离。
- 结论：用户确认手工集成已满足本轮外部宿主试跑目标，4.3 完成。Skill discovery 作为支持矩阵独立状态保留，不新增产品模式或证明字段。

## Wave 4.4 收口：clean candidate 与 Codex 隔离增强通过

- 候选 provenance：commit `e6f33811721dcf4710a3b812413923a4a586aae4`；source archive SHA-256 `6dd06b4b991ee93e7112dab56046f92f9381aa0bff3b61a7192e8f6c9ea78226`；wheel SHA-256 `f878c30b91b7fa152fa4fb6d15c855df08e42da58fd63af9040a3566090dce97`；sdist SHA-256 `dc1be864f2ca55b50e7caf3ebfc3d615538ebe6997d76812a872c5c378c3ebe9`。
- 完整门禁：Python `328 passed`、Ruff、feedback JavaScript、Markdown shell 语法、Skill 规范、SVG/XML 与 diff check 全部通过。
- 安装验证：macOS `15.6.1` / arm64 / Python `3.11.15` 下，wheel 通过 uv `0.11.28`、sdist 通过 pipx `1.15.0` 在仓库外隔离安装；doctor、module CLI、依赖、6 项 package resources、demo、package `0.1.0a0` / schema `0.3` / prompt `v0.5` 全部通过。archive 内三项 Skill 文件与候选 commit 一致。
- Codex 隔离增强：Codex CLI `0.144.3` 使用全新 HOME、临时 CODEX_HOME、空工作目录、只读 sandbox 和关闭全部工具的 reviewer。验收采用第二轮持久化 JSONL；reviewer thread 与 orchestrator 不同，只有一个最终 `agent_message` 和一个 `turn.completed`，无工具、命令、文件修改或协作事件。WebSocket 超时后回退 HTTPS，最终响应完整；空工作目录未变化，临时目录在 finalize 前清理。
- 正式报告：`complete / concerns`，风险分 `40`，`billing.py:7` 精确锚定 1 条 high finding；run identity、schema、计数、自包含 HTML、`.run/` 清理和独立重渲染通过，重渲染结果字节一致。
- 结论：4.4 完成。未修改 runtime、Skill、prompt 或 schema，未新增宿主模式、adapter 或隔离证明字段。

## 已退役的最小复跑候选

- source commit：`74c7d16887a69de5c5f1f6e8ada6ac3ff9427088`
- source archive：`source-74c7d168.tar`
- source archive SHA-256：`ad3cc339da7d15281143518513790d84e13910dc43caa7695447a2c9222116dc`
- wheel：`evidentloop-0.1.0a0-py3-none-any.whl`
- wheel SHA-256：`a12e26fb311513901fb8c56dbc4a12ce6f02c977d37a41248baff1fe75112c18`
- 本地预检：archive commit ID、Skill、prompt、wheel 完整性、隔离安装、兼容探针、doctor、module CLI 与 demo 均通过。
- 外部状态：已执行但未通过；固定 provenance 正确，安装与 discovery 阻塞，4.3 保持待办。

`74c7d16`、`7d0bef6`、`2cb03af` 与 `fc875c9` 只保留为退役证据；当前固定候选以 `00bfac7a` 四值为准。后续若修改 runtime 或 Skill，必须重新冻结，不得把 dirty tree 构建物冒充固定产物。

## 隐私边界

本记录不包含试用仓库路径、`python_executable` 等本机绝对路径、源码、diff、prompt、raw analysis、报告文件、凭据、代理配置或完整 thread ID。
