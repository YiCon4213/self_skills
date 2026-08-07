# 当天日报与每日 AI 步伐发布设计

## 目标

创建一个面向当天工作的 `daily-report`，融合原 `daily-summary` 的简洁输出、朋友版 `daily-report` 的多源归并，以及 `review-daily-ai-work` 的证据、隐私和数据缺口机制。Claude Code 与 Codex 共用同一份 skill 文件，并分别通过各自的 Notion 连接发布。同步优化 `review-daily-ai-work`，让它复用相同的提取与发布契约，但继续保持深度复盘定位。

## 范围

- 停用 `C:\Users\1324gcws\.claude\skills\daily-summary`，保留可恢复备份，不直接删除。
- 在 `C:\Users\1324gcws\.agents\skills\daily-report` 创建唯一真实副本。
- 在 `C:\Users\1324gcws\.claude\skills\daily-report` 创建指向真实副本的 Windows 目录联接。
- 继续以 `C:\Users\1324gcws\.agents\skills\review-daily-ai-work` 为复盘 skill 的唯一真实副本，并为 Claude 创建同名目录联接。
- 为 Claude Code 配置用户级 Notion MCP；Codex 使用已安装并授权的 Notion 插件。
- 在 Notion 建立一个数据库，用同一数据库保存“工作日报”和“AI 步伐”两种记录。

不纳入本次范围：OpenCode、Kimi Code、自动定时运行、公开 OAuth 应用、团队多工作区发布。

## 用户体验

### daily-report

- 默认日期：当前 `Asia/Shanghai` 自然日。
- 支持显式日期、今天、昨天和前天。
- 默认生成本地/聊天日报，不产生外部写入。
- 用户明确提出“发送到 Notion”“发布”或传入 `--publish` 时执行发布。
- `--no-notion` 明确禁止发布，并覆盖其他隐式发布判断。
- 输出目标为 4–8 条；数据不足时允许更少，不填充。
- 按项目分组，组内按业务主题合并；主句写成果，必要时用从句说明过程。
- 每条必须根据最终答复、验证动作或文件动作判断为完成、部分完成或受阻，不能仅凭用户请求写成完成。

### review-daily-ai-work

- 默认日期继续是前一自然日。
- 六节报告契约保持不变。
- 增加可选 `--publish` 发布阶段；默认仍只刷新本地 Markdown。
- 借用业务主题合并、成果动词、真正卡点和边角项目省略规则，但不受 4–8 条日报上限约束。
- 发布失败不得影响已经通过隐私和结构检查的本地报告。

## 架构

### 共享数据提取器

扩展现有 `extract_daily_conversations.py`，继续读取 Codex 本地 sessions、archived sessions 与 Claude Code 主会话。保留紧凑 JSON、局部回读、去重、截断、锁文件容错和隐私摘要。新增适合当天日报的稳定字段：项目标识、目标摘要、动作证据、最终结果摘要、状态候选和卡点候选。

Codex 应用聊天只能由 Codex Desktop 的任务工具采集，因此它保持为运行时可选增强：Codex 可补采，Claude 必须明确披露该来源不可用，不能声称三源完整覆盖。

### 报告契约分离

- `references/daily-report-contract.md`：当天简报的分组、合并、状态、格式和长度规则。
- `references/report-contract.md`：保留每日 AI 步伐的六节深度复盘契约，并吸收与证据不冲突的归并规则。
- 两个 skill 都引用 `references/notion-publishing.md` 中同一套发布语义；物理文件各自保存，测试保证关键契约一致，避免跨 skill 相对路径失效。

### Notion 发布适配

skill 不硬编码具体 MCP 工具名、Notion token、代理端口、页面 ID 或数据库 ID。

运行时先发现当前客户端提供的 Notion 连接能力：

- Codex：使用已安装的 Notion 插件。
- Claude Code：使用用户级 `https://mcp.notion.com/mcp` OAuth 连接。

发布目标为 `每日 AI 记录` 数据库，建议属性：

| 属性 | 类型 | 规则 |
|---|---|---|
| 标题 | title | `YYYY-MM-DD 工作日报` 或 `YYYY-MM-DD 步伐` |
| 日期 | date | 报告自然日 |
| 类型 | select | `工作日报` 或 `AI 步伐` |
| 状态 | select | `草稿` 或 `已发布` |
| 来源 | multi-select | `Codex 编程任务`、`Codex 应用聊天`、`Claude Code` |
| 完整性 | select | `完整` 或 `部分缺失` |

幂等键为“日期 + 类型”。发布时先查同键记录：不存在则创建，存在则更新属性和正文。不得追加重复日报。数据库不存在时，仅在用户首次明确发布时创建；如果工作区有多个同名数据库，停止并让用户选择。

## 安全与隐私

- 原始日志、代码、绝对路径、仓库名、账号和凭据不发送到 Notion。
- Notion 正文只使用已经通过报告隐私检查的最终文本。
- 不保存 `NOTION_TOKEN`，不读取 Kimi/OpenCode 配置，不保留直接 REST API fallback。
- Notion 不可用、未授权或写入失败时，保留本地报告并返回短错误；不得循环重试外部写入。
- 停用旧 skill 采用重命名备份，确保可恢复。

## 文件布局

### daily-report

```text
daily-report/
├── SKILL.md
├── agents/openai.yaml
├── references/daily-report-contract.md
├── references/notion-publishing.md
├── scripts/extract_daily_conversations.py
├── tests/test_extract_daily_conversations.py
└── tests/test_skill_contract.py
```

### review-daily-ai-work

```text
review-daily-ai-work/
├── SKILL.md
├── agents/openai.yaml
├── references/codex-app-chat-collection.md
├── references/notion-publishing.md
├── references/report-contract.md
├── scripts/extract_daily_conversations.py
├── tests/test_extract_daily_conversations.py
└── tests/test_skill_contract.py
```

## 安装与停用策略

1. 在可写工作区构建候选目录并完成测试。
2. 将 Claude 的旧 `daily-summary` 原子重命名为带日期的 `.disabled-2026-08-07` 备份。
3. 将新的真实副本安装到 `.agents\skills`。
4. 为 `.claude\skills` 创建目录联接，不复制第二份内容。
5. 使用 `claude.cmd mcp add --transport http --scope user notion https://mcp.notion.com/mcp` 配置 Claude；OAuth 必须由用户在 `/mcp` 中完成。
6. Codex 继续使用当前已连接的 Notion 插件。

## 测试设计

### 提取器测试

- 当天边界按 `Asia/Shanghai` 计算。
- Codex sessions、archived sessions 和 Claude 主会话均可提取。
- 重复事件、子代理记录、系统注入和工具噪声被剔除。
- 完成、部分完成和受阻只从可验证结果推断。
- 锁定、畸形和缺失来源被量化披露。

### skill 契约测试

- 两个 `SKILL.md` 仅含可跨客户端识别的 frontmatter。
- `daily-report` 默认当天；`review-daily-ai-work` 默认昨天。
- 只有明确发布意图才允许 Notion 写入。
- 两个 skill 都要求“日期 + 类型”幂等 upsert。
- 两个 skill 都禁止 token、硬编码工具名和重复追加。
- daily-report 保持简报契约，review 保持六节深度报告契约。

### 安装验证

- Codex skill 校验器通过。
- Python 单元测试全部通过。
- Claude 目录联接指向 `.agents\skills` 真源。
- 旧 `daily-summary` 不再位于可发现路径。
- Claude MCP 列表包含 Notion；若 OAuth 未完成，明确报告待用户授权。
- 对 Notion 只做无破坏性的连接和目标查找验证；首次数据库创建及测试发布需用户明确执行发布命令。

## 验收标准

- Claude 与 Codex 都能发现并调用同一个 `daily-report`。
- 两端对同一组合成日志生成等价的核心日报条目。
- `daily-report` 不会把请求意图误写成已完成成果。
- 两端都具备 Notion 发布路径，且重复发布同日同类型时更新原记录。
- `review-daily-ai-work` 保持现有隐私、证据、六节结构与本地原子发布能力，并增加可选 Notion 发布。
- 任一外部连接失败都不会损坏或阻止本地报告生成。
