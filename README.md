# review-daily-ai-work

一个面向 Codex 的个人 Skill：复盘北京时间前一自然日的 Codex 与 Claude Code 本地对话，并生成一份以学习、问题诊断和后续行动为核心的中文“步伐”报告。

## 功能

- 从本机 Codex 与 Claude Code 日志中按消息时间筛选前一天的记录。
- 在本地完成过滤、去重、分级压缩和必要的局部回读。
- 用短篇幅概括每日工作，把主要篇幅留给学到的知识与认知变化。
- 用“观察事实 / 合理推断 / 待验证”分析困难和盲区，不进行人格或心理诊断。
- 总计推荐 1–3 项材料并对应高价值问题，说明学习内容、主要知识、实践产出与验证标准。
- 从尚未解决的知识缺口和判断中生成 3–5 个可直接复制给 AI 的问题。
- 原子刷新 `D:\Web\new_think\YYYY-MM-DD步伐.md`。

## 使用

在支持个人 Skills 的 Codex 中输入：

```text
$review-daily-ai-work
```

默认时区为 `Asia/Shanghai`，默认复盘运行日前一自然日。报告固定包含“每日做了什么”“学到了什么”“暴露的问题、盲区与困难”“定向补给”“我可以向 AI 提问的问题”。“每日做了什么”只作为背景，目标不超过约 300 个中文字符，但不限制事项数量。

## 环境与数据来源

- Windows
- Python 3.12，仅使用标准库
- Codex Desktop：`~\.codex\sessions` 与 `~\.codex\archived_sessions`
- Claude Code：`~\.claude\projects` 下的主会话 JSONL

Claude 网页版或桌面版云端聊天不在读取范围内。

## 隐私设计

原始日志始终在本机处理，不会直接进入联网查询。联网前会删除或替换代码、绝对路径、仓库与项目名、邮箱、账号、URL 查询参数、密钥、token 和其他凭据。若脱敏后主题失去意义，该项搜索会被放弃。

提取器默认把候选摘要限制在 80,000 字符以内，单次局部回读最多 6,000 字符。锁定、损坏、缺失或因体量限制未精读的内容保留在内部分析中；只有它们会实质影响结论时，才在报告末尾用 1–2 句话说明证据影响。

## 本地命令

查看提取器参数：

```powershell
python scripts\extract_daily_conversations.py extract --help
python scripts\extract_daily_conversations.py show --help
```

运行测试：

```powershell
python -X utf8 -m unittest discover -s tests -p "test_*.py"
```

测试全部使用合成日志，不读取真实个人对话。

## 目录结构

```text
review-daily-ai-work/
├── SKILL.md
├── README.md
├── agents/openai.yaml
├── references/report-contract.md
├── scripts/extract_daily_conversations.py
└── tests/test_extract_daily_conversations.py
```

`SKILL.md` 是 Codex 的执行入口；`README.md` 只用于人类阅读和 Git 仓库说明，不参与日常 Skill 调用。
