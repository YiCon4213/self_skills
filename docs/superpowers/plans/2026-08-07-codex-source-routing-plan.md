# Codex 会话来源分流 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `daily-report` 与 `review-daily-ai-work` 默认支持 Codex CLI、Codex VS Code 插件和 Claude Code 本地会话，同时仅在能力可用或用户显式要求时补采 Codex Desktop 应用聊天。

**Architecture:** 保持本地提取器不变，在两个 skill 的指令层建立同一套来源路由：本地日志是必需基线，Codex 应用聊天是运行时能力驱动的可选增强。通过契约测试锁定默认降级、显式参数警告和报告统计条件，再更新各自参考文档与界面描述。

**Tech Stack:** Markdown Agent Skills、Python `unittest`、Codex skill validator、Git worktree、Windows 目录联接。

## Global Constraints

- 默认来源必须是 `~/.codex/sessions`、`~/.codex/archived_sessions` 与 `~/.claude/projects`。
- Codex Desktop 工具不可用时默认静默跳过，不构成数据缺口。
- `--include-codex-app` 强制尝试；工具不可用时继续生成并返回短警告。
- 只有实际尝试应用聊天采集时，才披露该来源的覆盖或缺口。
- 不修改提取算法、Notion 幂等发布、隐私、证据状态和报告结构契约。
- 两个 skill 继续以 `.agents\skills` 为唯一真实副本，Claude 通过目录联接共用。

---

### Task 1: 修正 daily-report 的来源路由

**Files:**
- Modify: `C:\Users\1324gcws\.agents\skills\daily-report\tests\test_skill_contract.py`
- Modify: `C:\Users\1324gcws\.agents\skills\daily-report\SKILL.md`
- Modify: `C:\Users\1324gcws\.agents\skills\daily-report\references\codex-app-chat-collection.md`
- Modify: `C:\Users\1324gcws\.agents\skills\daily-report\agents\openai.yaml`

**Interfaces:**
- Consumes: existing `extract_daily_conversations.py extract` output and current Notion/report contracts.
- Produces: instruction contract for local baseline collection plus optional `--include-codex-app` collection.

- [ ] **Step 1: Write the failing contract tests**

Add a test that reads the real skill and reference, then verifies these independently defined outcomes:

```python
def test_codex_local_sources_are_default_and_app_chat_is_optional(self):
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    app_chat = (ROOT / "references" / "codex-app-chat-collection.md").read_text(encoding="utf-8")
    for phrase in ("Codex CLI", "VS Code", "Claude Code 本地会话", "--include-codex-app"):
        self.assertIn(phrase, skill)
    self.assertIn("默认静默跳过", skill + app_chat)
    self.assertIn("不构成数据缺口", skill + app_chat)
    self.assertIn("显式", app_chat)
```

Also assert the obsolete unconditional wording is absent:

```python
for phrase in ("在 Codex Desktop 中，完整阅读", "在 Claude Code 中标明该来源不可用"):
    self.assertNotIn(phrase, skill)
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python -m unittest tests.test_skill_contract.DailyReportContractTests.test_codex_local_sources_are_default_and_app_chat_is_optional -v`

Expected: FAIL because the current workflow requires Desktop collection and has no `--include-codex-app` contract.

- [ ] **Step 3: Write the minimal skill and reference changes**

Update the parameter section to define `--include-codex-app`. Rewrite source collection as:

1. Always extract Codex local sessions/archived sessions and Claude Code local sessions.
2. Detect whether task/thread listing and reading tools are available.
3. Read the app-chat reference only if tools exist or the explicit flag is present.
4. Silently skip unavailable optional capability by default; with the explicit flag, warn and continue.

Add the same applicability gate at the top of `codex-app-chat-collection.md`. Update `openai.yaml` to describe local Codex/Claude reporting without implying Desktop is required.

- [ ] **Step 4: Run focused and full daily-report tests**

Run:

```powershell
python -m unittest tests.test_skill_contract -v
python -m unittest discover -s tests -v
```

Expected: all daily-report tests PASS.

- [ ] **Step 5: Validate the skill candidate**

Run the installed Codex skill validator against the staged `daily-report` directory and expect exit code 0.

---

### Task 2: 修正 review-daily-ai-work 的来源与报告契约

**Files:**
- Modify: `tests/test_skill_contract.py`
- Modify: `SKILL.md`
- Modify: `references/codex-app-chat-collection.md`
- Modify: `references/report-contract.md`
- Modify: `agents/openai.yaml`

**Interfaces:**
- Consumes: Task 1 的相同来源命名和条件路由语义。
- Produces: 六节复盘报告中按实际尝试来源披露统计的契约。

- [ ] **Step 1: Write failing tests for optional app-chat coverage**

Replace the unconditional three-source assertion with:

```python
def test_local_sources_are_required_and_codex_app_chat_is_optional(self):
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    app_chat = (SKILL_ROOT / "references" / "codex-app-chat-collection.md").read_text(encoding="utf-8")
    report = (SKILL_ROOT / "references" / "report-contract.md").read_text(encoding="utf-8")
    for phrase in ("Codex CLI", "VS Code", "Claude Code 本地会话", "--include-codex-app"):
        self.assertIn(phrase, skill)
    self.assertIn("默认静默跳过", skill + app_chat)
    self.assertIn("不构成数据缺口", skill + app_chat + report)
    self.assertIn("只有实际尝试", report)
```

Retain the unrelated recommendation and report-structure assertions in their own test.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python -m unittest tests.test_skill_contract.SkillContractTests.test_local_sources_are_required_and_codex_app_chat_is_optional -v`

Expected: FAIL because the current skill and report contract require three-source disclosure.

- [ ] **Step 3: Implement the minimal conditional workflow**

Update `SKILL.md` parameter and workflow sections with the same source routing as Task 1. Rename the baseline source from `Codex 编程任务` to `Codex 本地会话（CLI/VS Code）`. Keep `Codex 应用聊天` in the document only as a conditional source.

In `report-contract.md`, require the two local baseline statistics and require app-chat statistics only after successful or explicit attempted collection. In the app-chat reference, define capability detection, default silent skip, explicit warning, and attempted-failure disclosure. Update `openai.yaml` accordingly.

- [ ] **Step 4: Run focused and full review tests**

Run:

```powershell
python -m unittest tests.test_skill_contract -v
python -m unittest discover -s tests -v
```

Expected: all review-daily-ai-work tests PASS.

- [ ] **Step 5: Validate and commit the review skill**

Run the Codex skill validator, inspect `git diff`, then commit only the Task 2 files with message `fix: make Codex app chats optional`.

---

### Task 3: 安装、交叉验证与兼容性检查

**Files:**
- Install staged Task 1 files into `C:\Users\1324gcws\.agents\skills\daily-report`
- Verify junction: `C:\Users\1324gcws\.claude\skills\daily-report`
- Verify junction: `C:\Users\1324gcws\.claude\skills\review-daily-ai-work`

**Interfaces:**
- Consumes: verified candidates from Tasks 1 and 2.
- Produces: installed cross-client skill pair with unchanged Notion publishing behavior.

- [ ] **Step 1: Install the staged daily-report files**

Copy only the four modified Task 1 files into the canonical `.agents\skills\daily-report` directory. Do not copy `.git`, temporary output, caches, or test artifacts.

- [ ] **Step 2: Re-run both complete suites from canonical locations**

Run `python -m unittest discover -s tests -v` once in each canonical skill directory. Expected: all tests PASS with zero errors.

- [ ] **Step 3: Run both skill validators**

Validate both canonical directories. Expected: both validators return success.

- [ ] **Step 4: Verify source-routing mutations**

Inspect both installed `SKILL.md` files and references to confirm:

- removing the capability check would fail a contract test;
- changing default skip into a data gap would fail a contract test;
- removing `--include-codex-app` would fail a contract test;
- no unconditional Desktop requirement remains.

- [ ] **Step 5: Verify shared Claude installation**

Resolve both Claude paths and confirm each points to its `.agents\skills` canonical directory. Do not alter Claude MCP or Notion configuration.

- [ ] **Step 6: Final repository review**

Confirm the review repository contains only intended commits and no temporary files. Report the remaining pre-existing worktree separately; do not delete it without user direction.
