# ADR-001：采用 PyPI CLI 与标准薄 Skill

## 状态

已采纳

## 日期

2026-07-11

## 上下文

产品当前已有可运行的 Python 审计内核，但外部用户仍需要 clone、editable install 和手工 Skill 注册。自研 npm launcher、独立二进制或 Skill-first 平铺都会扩大维护面。分发架构不依赖最终产品名；活动身份由身份 ADR 决定。

## 决策

- Python package/CLI 是唯一 runtime 与产品版本真相源，通过 PyPI 发布，uv tool 为推荐安装方式，pipx 为 fallback。
- Agent Skill 是同仓库 `skills/<active-identity>/` 下的静态薄编排层，通过通用 `skills` CLI 安装；ADR-004 激活后的目标目录为 `skills/evidentloop/`。
- GitHub Pages 从 main 的 `docs/` 提供真实报告和 replay demo 的零安装入口；准确版本的脱敏 evidence bundle 作为 GitHub Release 资产发布。
- 每个公开 PyPI 版本必须对应不可变 main Git tag 与绑定该 source commit 的 evidence bundle。

## 理由

- 复用成熟包管理器，安装动作透明、可升级、可卸载。
- 不复制 Python 业务逻辑，不维护 npm、二进制或宿主目录适配。
- main 保持可独立构建；release tag 是唯一源码版本真相。
- 维护者只维护 Python package、薄 Skill、静态 Pages 与明确边界的 evidence bundle。

## 替代方案

- 自研 npm setup：拒绝。跨 npm/Python/Skill 编排增加信任与排障成本。
- 跨平台独立二进制：拒绝。签名、体积、平台矩阵不符合 Alpha 与个人维护边界。
- Skill-first 内嵌 Python：拒绝。复制内核并破坏测试、依赖和发布边界。
- 动态 `skill get core`：暂缓。当前静态编排足够。

## 影响

项目需要新增正式 console script、doctor、replay demo、标准 Skill、最小权限 publish workflow、Pages 入口和 PyPI Trusted Publishing。身份门禁完成前以 ADR-002 记录当前代码基线；ADR-004 激活后以其目标身份执行 clean break。main 与发布证据的内容边界遵循调整后的 ADR-003。
