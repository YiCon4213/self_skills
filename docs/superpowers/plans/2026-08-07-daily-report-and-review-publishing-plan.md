# Daily Report and Review Publishing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install one cross-runtime `daily-report`, enhance `review-daily-ai-work`, and provide safe idempotent Notion publishing from both Claude Code and Codex.

**Architecture:** Keep each skill self-contained but synchronize the proven Python extractor and the Notion publishing contract. Store the canonical skills under `~/.agents/skills` and expose them to Claude through directory junctions; use capability-based Notion instructions so Codex uses its plugin and Claude uses the hosted OAuth MCP.

**Tech Stack:** Python 3.12 standard library, `unittest`, Markdown Agent Skills, Windows directory junctions, Claude Code MCP, Codex Notion plugin.

## Global Constraints

- Use `Asia/Shanghai`; `daily-report` defaults to today and `review-daily-ai-work` defaults to yesterday.
- Do not store Notion tokens, hard-code MCP tool names, proxies, usernames, project mappings, page IDs, or database IDs.
- Publish only when the user explicitly requests Notion or passes `--publish`; `--no-notion` always wins.
- Upsert by `日期 + 类型`; never append a duplicate same-day same-type record.
- Raw logs, code, absolute paths, repository names, accounts, and credentials stay local.
- A Notion failure must not damage or block a validated local report.
- Preserve existing user files and disable `daily-summary` through a recoverable rename.

---

### Task 1: Establish the versioned baseline and isolated workspace

**Files:**
- Track: `SKILL.md`, `agents/openai.yaml`, `references/*.md`, `scripts/extract_daily_conversations.py`, `tests/*.py`
- Create: `.gitignore` entry `.worktrees/`

**Interfaces:**
- Consumes: current untracked `review-daily-ai-work` files.
- Produces: a clean Git baseline and branch `codex/daily-report-notion` in `.worktrees/daily-report-notion`.

- [ ] **Step 1: Run the existing test suite**

Run:

```powershell
python -X utf8 -m unittest discover -s tests -p "test_*.py"
```

Expected: all current extractor and contract tests pass before any behavior change.

- [ ] **Step 2: Commit the current skill baseline without altering contents**

```powershell
git add .gitignore README.md SKILL.md agents references scripts tests
git commit -m "chore: capture review skill baseline"
```

- [ ] **Step 3: Ignore and create the isolated worktree**

```powershell
Add-Content .gitignore ".worktrees/"
git add .gitignore
git commit -m "chore: ignore skill worktrees"
git worktree add .worktrees/daily-report-notion -b codex/daily-report-notion
```

- [ ] **Step 4: Re-run baseline tests in the worktree**

Run the Step 1 test command inside the worktree. Expected: the same passing test count.

### Task 2: Create the cross-runtime daily-report skill with contract-first tests

**Files:**
- Create: isolated repository `C:\tmp\daily-report-skill\SKILL.md`
- Create: `C:\tmp\daily-report-skill\agents/openai.yaml`
- Create: `C:\tmp\daily-report-skill\references/daily-report-contract.md`
- Create: `C:\tmp\daily-report-skill\references/notion-publishing.md`
- Create: `C:\tmp\daily-report-skill\scripts/extract_daily_conversations.py`
- Create: `C:\tmp\daily-report-skill\tests/test_extract_daily_conversations.py`
- Create: `C:\tmp\daily-report-skill\tests/test_skill_contract.py`

**Interfaces:**
- Consumes: `extract_daily_conversations.py extract --date DATE --timezone ZONE --output FILE` and `show` from the review skill.
- Produces: a self-contained `daily-report` using the same CLI and compact JSON schema.

- [ ] **Step 1: Write failing contract tests**

```python
class DailyReportContractTests(unittest.TestCase):
    def test_today_and_explicit_publish_contract(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        publishing = (ROOT / "references/notion-publishing.md").read_text(encoding="utf-8")
        self.assertIn("Asia/Shanghai", skill)
        self.assertIn("默认今天", skill)
        self.assertIn("--publish", skill)
        self.assertIn("--no-notion", skill)
        self.assertIn("日期 + 类型", publishing)
        self.assertIn("存在则更新", publishing)
        for forbidden in ("NOTION_TOKEN", "notion_API-post-search", "127.0.0.1", "Users/25818"):
            self.assertNotIn(forbidden, skill + publishing)
```

- [ ] **Step 2: Run the contract test and verify RED**

Run:

```powershell
python -X utf8 -m unittest tests.test_skill_contract -v
```

Expected: failure because the new skill files do not exist.

- [ ] **Step 3: Initialize the isolated repository, then write the minimal skill and references**

Run `git init -b main C:\tmp\daily-report-skill`, then define the workflow in this order: resolve date and flags, extract compact JSON, optionally collect Codex app chats, group by project and business outcome, classify evidence, format 4–8 concise items, validate privacy, optionally publish through the Notion capability contract.

- [ ] **Step 4: Copy the proven extractor and its synthetic tests**

Copy exact files first so extractor behavior is unchanged. Do not copy README, Node dependencies, `query.js`, `notion.js`, Kimi, or OpenCode code.

- [ ] **Step 5: Run daily-report tests and skill validation**

```powershell
python -X utf8 -m unittest discover -s tests -p "test_*.py"
python -X utf8 C:\Users\1324gcws\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
```

Expected: all tests pass and validator prints `Skill is valid!`.

- [ ] **Step 6: Commit the verified daily-report skill**

```powershell
git add SKILL.md agents references scripts tests
git commit -m "feat: create cross-runtime daily report skill"
```

### Task 3: Add publishing and stronger outcome grouping to review-daily-ai-work

**Files:**
- Modify: `SKILL.md`
- Modify: `references/report-contract.md`
- Create: `references/notion-publishing.md`
- Modify: `tests/test_skill_contract.py`

**Interfaces:**
- Consumes: the existing six-section local report and the shared Notion publishing semantics.
- Produces: optional `--publish` after local report validation, with no change to the default local-only behavior.

- [ ] **Step 1: Write failing review contract tests**

```python
def test_optional_idempotent_notion_publish_contract(self):
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    publishing = (SKILL_ROOT / "references/notion-publishing.md").read_text(encoding="utf-8")
    self.assertIn("--publish", skill)
    self.assertIn("默认不写入 Notion", skill)
    self.assertIn("日期 + 类型", publishing)
    self.assertIn("AI 步伐", publishing)
    self.assertIn("发布失败不得影响", publishing)
```

```python
def test_outcome_grouping_keeps_evidence_status(self):
    contract = (SKILL_ROOT / "references/report-contract.md").read_text(encoding="utf-8")
    for phrase in ("业务主题", "成果动词", "完成证据", "真正受阻"):
        self.assertIn(phrase, contract)
```

- [ ] **Step 2: Run tests and verify RED**

Expected: missing publishing reference and contract phrases cause failures.

- [ ] **Step 3: Add the minimal publishing stage and grouping rules**

Place publishing after local atomic replacement. Require explicit publish intent, privacy-clean final Markdown, target type `AI 步伐`, and upsert by date and type.

- [ ] **Step 4: Run all review tests and validator**

Expected: all tests pass and `quick_validate.py` succeeds.

- [ ] **Step 5: Commit the review skill implementation**

```powershell
git add SKILL.md agents references tests
git commit -m "feat: add review skill Notion publishing"
```

### Task 4: Install canonical skills and retire daily-summary safely

**Files:**
- Install: `C:\Users\1324gcws\.agents\skills\daily-report`
- Update: `C:\Users\1324gcws\.agents\skills\review-daily-ai-work`
- Create junction: `C:\Users\1324gcws\.claude\skills\daily-report`
- Create junction: `C:\Users\1324gcws\.claude\skills\review-daily-ai-work`
- Rename: `C:\Users\1324gcws\.claude\skills\daily-summary` to `daily-summary.disabled-2026-08-07`

**Interfaces:**
- Consumes: verified review worktree and the verified `C:\tmp\daily-report-skill` repository.
- Produces: one canonical copy of each skill under `.agents/skills`, visible to both runtimes.

- [ ] **Step 1: Verify exact installation targets**

Resolve each path and confirm no target leaves the two named skill roots. If a disabled backup already exists, add a numeric suffix rather than overwrite it.

- [ ] **Step 2: Perform recoverable retirement and installation**

Use native PowerShell `Move-Item`, `Copy-Item`, and `New-Item -ItemType Junction`. Do not use recursive deletion.

- [ ] **Step 3: Verify junction targets and skill discovery files**

```powershell
Get-Item C:\Users\1324gcws\.claude\skills\daily-report | Select-Object LinkType,Target
Get-Item C:\Users\1324gcws\.claude\skills\review-daily-ai-work | Select-Object LinkType,Target
Test-Path C:\Users\1324gcws\.claude\skills\daily-summary
```

Expected: both are junctions to `.agents\skills`; old active path is absent.

### Task 5: Configure and verify Notion connectivity without publishing user data

**Files:**
- Update through Claude CLI: user-scoped MCP settings in `~/.claude.json`.
- Create through Notion only on explicit publish: database `每日 AI 记录`.

**Interfaces:**
- Consumes: Claude hosted MCP URL and the already connected Codex Notion plugin.
- Produces: both runtimes can locate the publishing destination; actual report writes remain user-triggered.

- [ ] **Step 1: Add Claude user-scoped Notion MCP**

```powershell
claude.cmd mcp add --transport http --scope user notion https://mcp.notion.com/mcp
```

- [ ] **Step 2: Verify Claude MCP registration**

```powershell
claude.cmd mcp get notion
```

Expected: HTTP transport and `https://mcp.notion.com/mcp`; OAuth may still require the user to run `/mcp` interactively.

- [ ] **Step 3: Verify Codex Notion connection read-only**

Search for `每日 AI 记录`; do not create or update content during installation verification.

- [ ] **Step 4: Run final verification**

Run both complete Python suites, both skill validators, forbidden-string scan, junction checks, retired-skill check, and Claude MCP registration check. Read the full output and report any remaining interactive OAuth or first-publish database creation step.
