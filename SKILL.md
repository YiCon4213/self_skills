---
name: review-daily-ai-work
description: Use when reviewing the previous calendar day's Codex Desktop and Claude Code local conversations, requests, learning, difficulties, blind spots, or generating a dated Chinese 步伐 reflection report.
---

# 每日 AI 步伐

把前一自然日的本地 AI 对话压缩为一份有证据、可行动、20 分钟内可读完的中文复盘。原始日志始终留在本机；只有脱敏后的短搜索摘要可以用于联网查询。

## 参数与发布意图

- 无日期参数：默认复盘 `Asia/Shanghai` 的前一自然日。
- 支持显式 `YYYY-MM-DD` 日期。
- 默认不写入 Notion；仅在用户明确要求发送/发布到 Notion 或传入 `--publish` 时发布。
- `--no-notion` 禁止发布，优先级高于其他发布意图。

## 工作流

1. 以 `Asia/Shanghai` 计算前一自然日 `YYYY-MM-DD`，创建临时目录。
2. 从本 skill 目录运行：

   ```powershell
   python scripts/extract_daily_conversations.py extract --date YYYY-MM-DD --timezone Asia/Shanghai --output <临时目录>\extract.json
   ```

3. 只读取紧凑 JSON，先检查 `stats`、`warnings` 和覆盖来源。不要直接批量读取原始 JSONL。随后完整阅读 [Codex 应用聊天采集](references/codex-app-chat-collection.md)，补充 Codex 应用聊天索引。
4. 按目标合并重复工作，标记完成、部分完成或受阻。把结论分别标成观察事实、合理推断或待验证。
5. 只有当任务结果或盲区缺少证据时，使用消息定位符局部回读；每次最多 6000 字符，不得批量展开：

   ```powershell
   python scripts/extract_daily_conversations.py show --source <codex|claude> --session-id <id> --message-id <id> --max-chars 6000
   ```

6. 联网前只采用用户请求中的 `search_brief`，或重新生成不超过 240 字符的等价脱敏摘要。不得把原始提问、聊天正文、代码、绝对路径、仓库名、账号或凭据放入搜索查询。
7. 联网核验并推荐 1–4 个最高价值资源。技术内容可优先官方文档、原始论文或项目仓库；当天出现思维、决策、习惯或生活问题时，可选书籍具体章节、文章或实践材料，不得默认把所有问题转成技术清单。每项写明解决的问题、推荐理由、预计阅读/试用时间和链接。检查本机及当前上下文中的 skill/plugin 可用状态；只推荐，不安装。
8. 起草前完整读取 [references/report-contract.md](references/report-contract.md)，严格使用其中六个章节，目标 3500–5500 个中文字符；数据不足时宁可更短，不得填充或虚构。
9. 把草稿写入临时 `.md`，验证文件非空、标题日期正确、六节齐全、链接可用，并扫描绝对路径、私有标识与凭据。任何检查失败都不得动已有报告；全部通过后，使用 Python `os.replace` 原子刷新（允许替换）`D:\Web\new_think\YYYY-MM-DD步伐.md`。
10. 仅在明确发布时，完整阅读 [references/notion-publishing.md](references/notion-publishing.md)，把已经通过全部检查的最终报告幂等发布到 Notion。发布发生在本地原子刷新之后；失败不得回滚或损坏本地报告。
11. 删除临时提取文件和草稿。若来源缺失、锁定、损坏或被截断，继续生成报告并在“数据缺口”中量化披露；若没有有效记录，生成简短透明的空日报告。

## 快速判断

复盘前必须分别检查 **Codex 编程任务**（本地提取）、**Codex 应用聊天**（上述参考流程）和 **Claude Code**（本地提取）；统计与数据缺口也必须分别披露，不能把任一来源笼统写成 Codex 完整覆盖。

| 情况 | 处理 |
|---|---|
| 紧凑摘要已支持结论 | 不回读原文 |
| 结论或困难缺证据 | 只 `show` 对应消息 |
| 脱敏后主题失去意义 | 放弃该项联网搜索 |
| skill/plugin 状态无法验证 | 标记“可用性待验证” |
| 报告未通过隐私检查 | 不发布，先修订 |
| Notion 不可用或未授权 | 保留本地报告，输出短警告 |

## 常见错误

- 把工具输出、思考过程或子代理日志当成用户目标。
- 把重复聊天次数当成工作量或问题严重程度。
- 从一次提问推断人格、心理状态或固定能力。
- 为凑长度添加泛化建议，或推荐未核验链接。
