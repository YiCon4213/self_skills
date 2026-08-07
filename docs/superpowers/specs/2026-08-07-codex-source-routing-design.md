# Codex 会话来源分流设计

## 背景与目标

现有 `daily-report` 和 `review-daily-ai-work` 已能从本地日志提取 Codex 与 Claude Code 会话，但工作流把“Codex 应用聊天”写成了必查来源。这会让 Codex CLI、VS Code 插件和 Claude Code 错误依赖 Codex Desktop 专有的任务读取工具。

本次调整把本地日志定义为跨客户端基线，把 Codex Desktop 应用聊天定义为能力存在时的可选增强。Notion 发布、报告结构、隐私和证据判断保持不变。

## 来源模型

### 必需基线来源

- `Codex 本地会话（CLI/VS Code）`：读取 `~/.codex/sessions` 与 `~/.codex/archived_sessions`。提取器不按 `source` 元数据限制客户端，因此当前 VS Code 会话与未来 Codex CLI 会话使用同一路径。
- `Claude Code 本地会话`：读取 `~/.claude/projects`。

两个 skill 默认只依赖这两类本地来源。在 Codex CLI、Codex VS Code 插件或 Claude Code 中，缺少 Codex Desktop 任务工具不构成数据缺口，也不得产生误导性警告。

### 可选增强来源

`Codex 应用聊天` 仅在当前运行环境实际暴露可列出并读取 Codex 任务/聊天的工具时自动采集。当前环境没有这类能力时默认跳过，不影响报告生成，也不降低本地来源的完整性结论。

用户传入 `--include-codex-app` 时，skill 必须显式尝试采集：

- 能力可用：按参考流程采集并披露覆盖数量与时间窗。
- 能力不可用：继续使用本地基线生成报告，并给出简短警告，说明仅未包含应用聊天。

此参数不改变原始日志留在本地、只把脱敏成品发布到 Notion的规则。

## 工作流变更

两个 `SKILL.md` 都采用相同的来源路由顺序：

1. 运行本地提取器，读取 Codex CLI/VS Code 与 Claude Code 本地会话。
2. 检查 `stats`、`warnings` 和本地来源覆盖。
3. 仅当当前工具能力支持，或用户指定 `--include-codex-app` 时，读取 `references/codex-app-chat-collection.md` 并尝试补采应用聊天。
4. 生成报告；只有实际尝试过应用聊天采集时，才在统计或数据缺口中说明其成功、缺失或失败情况。

`references/codex-app-chat-collection.md` 保留，但开头增加适用条件和不可用时的降级行为，防止终端客户端误执行 Desktop 专属步骤。

## 报告与发布契约

- 来源名称统一使用 `Codex 本地会话（CLI/VS Code）`、`Claude Code 本地会话`，以及条件性的 `Codex 应用聊天`。
- 日报和复盘的默认统计只要求披露本地基线来源。
- 只有成功采集或显式尝试 `Codex 应用聊天` 时，报告才增加该来源的覆盖统计或数据缺口。
- Notion 的幂等键、发布触发条件和失败降级不变；发布内容如包含来源属性，按本次实际使用的来源填写。
- 未来 Codex Desktop 提供任务工具时，不需要修改提取器；能力检查会自动启用可选增强。

## 文件范围

- `daily-report/SKILL.md`
- `daily-report/references/codex-app-chat-collection.md`
- `daily-report/tests/test_skill_contract.py`
- `review-daily-ai-work/SKILL.md`
- `review-daily-ai-work/references/codex-app-chat-collection.md`
- `review-daily-ai-work/references/report-contract.md`
- `review-daily-ai-work/tests/test_skill_contract.py`
- 两个 skill 的 `agents/openai.yaml`（仅在描述与新来源模型不一致时更新）

提取器当前已覆盖本地目录且不限制 `source`，因此本次不修改提取算法。

## 错误处理

- 本地来源缺失、损坏或被锁定：继续按现有规则生成，并量化为数据缺口。
- Desktop 工具默认不可用：静默跳过，不记为缺口。
- `--include-codex-app` 且工具不可用：继续生成，返回一条短警告。
- Desktop 工具可用但采集失败：继续生成，并把失败记入可选来源数据缺口。

## 测试与验收

先添加失败的契约测试，再修改 skill 文档：

- 两个 skill 明确支持 Codex CLI、Codex VS Code 插件与 Claude Code 本地会话。
- 两个 skill 都把本地来源列为默认基线。
- `Codex 应用聊天` 只在能力可用或指定 `--include-codex-app` 时尝试。
- 默认环境缺少 Desktop 工具时不记数据缺口；显式参数失败时会警告。
- 旧的“必须补充 Codex 应用聊天”或“Claude 中必须标记该来源不可用”表述不存在。
- 两套原有单元测试和 skill 校验器全部通过。
- Claude 的目录联接仍指向 `.agents\skills` 中的唯一真实副本。

验收完成后，Codex CLI、VS Code 插件与 Claude Code 无需 Codex Desktop 即可生成日报和复盘；未来 Codex Desktop 仍能按能力自动补充应用聊天。
