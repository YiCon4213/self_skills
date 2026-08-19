# Diagnostic-First Daily Review Implementation Plan

> 历史说明：本文档描述第一轮实施计划，已被当前报告契约取代。后续修改与验收一律以 `references/report-contract.md` 为准。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebalance the daily AI reflection toward evidence-backed limitations and precisely matched learning resources while making overview, learning, and data-gap sections conditional.

**Architecture:** Keep extraction, privacy, local atomic publishing, optional Codex app enrichment, and optional Notion publishing unchanged. Change the behavior contract in `references/report-contract.md`, mirror its core decisions in `SKILL.md`, and enforce the new output shape through contract tests plus a fresh-context report-shape evaluation.

**Tech Stack:** Markdown skill instructions, Python `unittest`, existing conversation extraction script, Codex subagent forward-test.

## Global Constraints

- Fixed core sections: `做了什么`, `暴露的问题、盲区与困难`, `定向补给`.
- Conditional sections: `昨日概览`, `学到了什么`, `数据缺口`.
- Target report length: 2500–4000 Chinese characters; shorter is allowed when evidence is insufficient.
- `做了什么` receives about 10%–15%; problem diagnosis receives about 40%–50%; targeted learning receives about 30%–40%.
- Every diagnosis states how a limitation constrained reasoning and questions.
- Every learning resource states its mapped problem, main learning content, main knowledge, practice output, and verification standard.
- Do not infer personality, motivation, or fixed ability from a single interaction.
- Keep local-source checks, privacy protections, atomic local replacement, and optional Notion publication behavior unchanged.

---

### Task 1: Encode the New Report Shape as Failing Contract Tests

**Files:**
- Modify: `tests/test_skill_contract.py`
- Test: `tests/test_skill_contract.py`

**Interfaces:**
- Consumes: UTF-8 text from `SKILL.md` and `references/report-contract.md`.
- Produces: contract assertions that distinguish three fixed core sections from three conditional sections and require the diagnosis/supply fields.

- [ ] **Step 1: Replace the legacy recommendation-only test with diagnosis-first tests**

Add these test methods to `SkillContractTests` while retaining unrelated source-routing and Notion tests:

```python
def test_report_contract_prioritizes_diagnosis_over_activity_log(self):
    contract = (SKILL_ROOT / "references" / "report-contract.md").read_text(encoding="utf-8")
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

    for phrase in (
        "固定核心章节",
        "条件章节",
        "10%–15%",
        "40%–50%",
        "30%–40%",
        "2500–4000",
    ):
        self.assertIn(phrase, contract + skill)

    self.assertNotIn("且只使用六个一级内容章节", contract)
    self.assertNotIn("必须分别说明", contract)

def test_problem_items_require_a_complete_reasoning_chain(self):
    contract = (SKILL_ROOT / "references" / "report-contract.md").read_text(encoding="utf-8")
    for phrase in (
        "当时的理解或默认假设",
        "局限类型",
        "如何限制推理与提问",
        "反证与待验证",
        "下一步验证动作",
        "看待和理解问题的视角局限",
        "工作流与方法局限",
        "认知模型或知识缺口",
    ):
        self.assertIn(phrase, contract)

def test_targeted_learning_closes_the_problem_learning_loop(self):
    contract = (SKILL_ROOT / "references" / "report-contract.md").read_text(encoding="utf-8")
    for phrase in (
        "对应问题",
        "主要学习内容",
        "主要知识",
        "实践产出",
        "验证标准",
        "1–3",
    ):
        self.assertIn(phrase, contract)
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
python -m unittest tests.test_skill_contract.SkillContractTests.test_report_contract_prioritizes_diagnosis_over_activity_log tests.test_skill_contract.SkillContractTests.test_problem_items_require_a_complete_reasoning_chain tests.test_skill_contract.SkillContractTests.test_targeted_learning_closes_the_problem_learning_loop -v
```

Expected: FAIL because the current contract still requires six sections and does not contain the complete reasoning-chain and learning-loop fields.

- [ ] **Step 3: Commit the failing tests**

```powershell
git add tests/test_skill_contract.py
git commit -m "test: define diagnostic-first review contract"
```

---

### Task 2: Implement the Diagnosis-First Report Contract

**Files:**
- Modify: `references/report-contract.md`
- Modify: `SKILL.md`
- Test: `tests/test_skill_contract.py`

**Interfaces:**
- Consumes: compact extraction JSON, optional targeted message reads, and sanitized search briefs exactly as before.
- Produces: a 2500–4000-character report with three fixed core sections, conditional supporting sections, complete diagnosis chains, and mapped learning resources.

- [ ] **Step 1: Replace the fixed six-section contract with the approved conditional structure**

Make `references/report-contract.md` state this exact section policy:

```markdown
## 章节结构与篇幅

### 固定核心章节

- `做了什么`：约 10%–15%。
- `暴露的问题、盲区与困难`：约 40%–50%。
- `定向补给`：约 30%–40%。

### 条件章节

- `昨日概览`：一句话能显著帮助理解当天主线时才出现，最多三句话。
- `学到了什么`：存在明确学习证据且不能自然并入问题分析时才出现。
- `数据缺口`：缺口会实质影响诊断可信度时才出现。

目标长度为 2500–4000 个中文字符；证据不足时允许更短。
```

Keep the title format and preserve the existing ordering when optional sections are present.

- [ ] **Step 2: Replace the activity-log recipe with a compact result index**

Require each `做了什么` item to contain only:

```markdown
- **状态：** 完成、部分完成或受阻。
- **目标与结果：** 一句话写目标，一句话写可验证结果或未完成点。
```

Keep business-theme merging and completion-evidence rules, but remove instructions that expand implementation process into separate paragraphs.

- [ ] **Step 3: Add the complete diagnosis-chain recipe**

Require 2–4 high-value problems, each with these labeled fields in order:

```markdown
- **观察事实：**
- **当时的理解或默认假设：**
- **局限类型：** 看待和理解问题的视角局限 / 工作流与方法局限 / 认知模型或知识缺口。
- **如何限制推理与提问：**
- **造成的影响：**
- **反证与待验证：**
- **下一步验证动作：**
```

Add selection rules favoring transferable, evidence-rich, improvable limitations over isolated tool errors or unsupported deep-sounding claims.

- [ ] **Step 4: Add the targeted-learning closure recipe**

Require 1–3 verified resources, each with:

```markdown
- **对应问题：** 问题编号。
- **材料：** 类型、可点击标题、已核验链接。
- **匹配理由：** 它针对的具体局限。
- **主要学习内容：** 材料覆盖的主题、方法或章节。
- **主要知识：** 应形成的概念、判断框架或操作方法。
- **实践产出：** 清单、模板、决策记录、实验或练习。
- **验证标准：** 下次如何确认推理、提问或工作流得到改善。
- **投入：** 预计阅读或试用时间。
```

- [ ] **Step 5: Mirror the core behavior in `SKILL.md` without duplicating the full contract**

Change the workflow so it says:

```markdown
起草前完整读取 `references/report-contract.md`。固定输出“做了什么”“暴露的问题、盲区与困难”“定向补给”；仅在满足契约条件时加入“昨日概览”“学到了什么”“数据缺口”。目标 2500–4000 个中文字符。
```

Change source-gap handling so routine statistics remain internal and only materially conclusion-affecting gaps appear in the report. Change resource recommendations from 1–4 to 1–3 and require a problem mapping plus learning content, knowledge, practice output, and verification standard.

- [ ] **Step 6: Run the focused tests and verify GREEN**

Run the same focused command from Task 1.

Expected: all three tests PASS.

- [ ] **Step 7: Run the complete test suite**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: all existing extraction, source-routing, privacy, Notion, and report-contract tests PASS.

- [ ] **Step 8: Commit the implementation**

```powershell
git add SKILL.md references/report-contract.md
git commit -m "feat: prioritize diagnosis in daily review"
```

---

### Task 3: Validate Skill Metadata and Forward-Test Report Behavior

**Files:**
- Inspect: `agents/openai.yaml`
- Inspect: `SKILL.md`
- Inspect: `references/report-contract.md`
- Input fixture: `D:\Web\new_think\2026-08-12步伐.md`

**Interfaces:**
- Consumes: the revised skill plus one real prior report as the fact source.
- Produces: validation evidence that the skill is structurally valid and changes report shape in a fresh context.

- [ ] **Step 1: Run the skill validator**

Run:

```powershell
python C:\Users\1324gcws\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Users\1324gcws\.agents\skills\review-daily-ai-work
```

Expected: validation succeeds with no frontmatter or naming errors.

- [ ] **Step 2: Check UI metadata for drift**

Read `agents/openai.yaml` and confirm its display name, short description, and default prompt still match the daily reflection trigger. Regenerate only if the output promise contradicts the diagnosis-first behavior.

- [ ] **Step 3: Run a fresh-context forward-test with the revised skill**

Dispatch a fresh agent with this request:

```text
Use $review-daily-ai-work at C:\Users\1324gcws\.agents\skills\review-daily-ai-work to rewrite D:\Web\new_think\2026-08-12步伐.md as a diagnostic-first reflection. Treat the existing report as the available fact source; do not invent new evidence and do not publish to Notion. Save the candidate only in a temporary location.
```

- [ ] **Step 4: Score the candidate against observable acceptance criteria**

Confirm all of the following:

```text
1. 做了什么 is a compact result index, not the longest section.
2. Routine overview and coverage statistics are absent unless they affect a conclusion.
3. Each problem includes fact, default assumption, limitation type, reasoning/question restriction, impact, counterevidence, and a verification action.
4. Each resource maps to a problem and explains main learning content, main knowledge, practice output, and verification standard.
5. No personality diagnosis, private path, project identifier, credential, or invented link appears.
```

- [ ] **Step 5: Refactor wording only if the forward-test exposes a loophole**

If any acceptance criterion fails, add the smallest positive recipe to `references/report-contract.md`, rerun the focused tests and the forward-test, and keep all prior tests green.

- [ ] **Step 6: Run final verification and inspect repository state**

```powershell
python -m unittest discover -s tests -v
python C:\Users\1324gcws\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Users\1324gcws\.agents\skills\review-daily-ai-work
git diff --check
git status --short
```

Expected: tests and validation pass; `git diff --check` is clean; no temporary candidate remains in the repository.
