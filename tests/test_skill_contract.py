import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    @staticmethod
    def _assert_in_order(test_case, text, phrases):
        positions = [text.index(phrase) for phrase in phrases]
        test_case.assertEqual(positions, sorted(positions))

    def test_local_sources_are_required_and_codex_app_chat_is_optional(self):
        self.assertTrue((SKILL_ROOT / "references" / "codex-app-chat-collection.md").is_file())

        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        app_chat = (SKILL_ROOT / "references" / "codex-app-chat-collection.md").read_text(
            encoding="utf-8"
        )
        report_contract = (SKILL_ROOT / "references" / "report-contract.md").read_text(
            encoding="utf-8"
        )

        for phrase in (
            "Codex CLI",
            "VS Code",
            "Claude Code 本地会话",
            "--include-codex-app",
        ):
            self.assertIn(phrase, skill_text)

        self.assertIn("默认静默跳过", skill_text + app_chat)
        self.assertIn("不构成数据缺口", skill_text + app_chat + report_contract)
        self.assertIn("只有实际尝试", report_contract)

        for obsolete in (
            "复盘前必须分别检查",
            "三源覆盖与完整性",
        ):
            self.assertNotIn(obsolete, skill_text + report_contract)

    def test_report_contract_prioritizes_learning_and_diagnosis_over_activity_log(self):
        contract = (SKILL_ROOT / "references" / "report-contract.md").read_text(encoding="utf-8")
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        readme = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
        publishing = (SKILL_ROOT / "references" / "notion-publishing.md").read_text(
            encoding="utf-8"
        )

        for phrase in (
            "固定章节",
            "核心章节",
            "辅助章节",
            "学到了什么",
            "我可以向 AI 提问的问题",
            "2200–3600",
        ):
            self.assertIn(phrase, contract)
            self.assertIn(phrase, skill)

        headings = (
            "每日做了什么",
            "学到了什么",
            "暴露的问题、盲区与困难",
            "定向补给",
            "我可以向 AI 提问的问题",
        )
        self._assert_in_order(self, contract, headings)
        self._assert_in_order(self, skill, headings)
        section_requirements = contract.split("## 章节要求", 1)[1]
        actual_sections = re.findall(r"(?m)^### (.+?)(?:（.+?）)?$", section_requirements)
        self.assertEqual(list(headings), actual_sections[:5])

        self.assertIn("约 300 个中文字符", contract)
        self.assertIn("不限制事项数量", contract)
        self.assertNotIn("最多 3 项", contract + skill + readme)
        self.assertNotIn("`昨日概览`", contract + skill + readme + publishing)
        self.assertNotIn("`数据缺口`", contract + skill + readme + publishing)
        self.assertNotIn("且只使用六个一级内容章节", contract)
        self.assertNotIn("`昨日概览` 和 `数据缺口` 必须分别说明", contract)
        self.assertNotIn("标题、六节、链接", publishing)

    def test_low_evidence_reports_keep_structure_without_fabrication(self):
        contract = (SKILL_ROOT / "references" / "report-contract.md").read_text(encoding="utf-8")
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        publishing = (SKILL_ROOT / "references" / "notion-publishing.md").read_text(
            encoding="utf-8"
        )
        for phrase in (
            "有效证据充足时",
            "问题不足 2 个",
            "没有可核验材料",
            "无法负责任地生成可追问问题",
        ):
            self.assertIn(phrase, contract)
        self.assertIn("不得为了满足数量要求虚构", contract + skill)
        self.assertIn("有效证据充足时", skill)
        self.assertIn("低证据报告按契约中的退化规则", skill)
        self.assertIn("低证据报告按报告契约的退化规则", publishing)
        self.assertIn("不强制正常数量", publishing)

    def test_publish_gate_checks_the_full_learning_contract(self):
        contract = (SKILL_ROOT / "references" / "report-contract.md").read_text(encoding="utf-8")
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        publishing = (SKILL_ROOT / "references" / "notion-publishing.md").read_text(
            encoding="utf-8"
        )
        for phrase in (
            "学习链四要素",
            "问题诊断链",
            "补给字段",
            "AI 问题数量",
            "回指关系",
            "证据说明",
        ):
            self.assertIn(phrase, contract)
            self.assertIn(phrase, skill)
            self.assertIn(phrase, publishing)

    def test_human_docs_do_not_conflict_with_the_current_contract(self):
        readme = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
        ui_metadata = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        old_design = (
            SKILL_ROOT / "docs" / "superpowers" / "specs" / "2026-08-15-diagnostic-review-design.md"
        ).read_text(encoding="utf-8")
        old_plan = (
            SKILL_ROOT / "docs" / "superpowers" / "plans" / "2026-08-15-diagnostic-review-plan.md"
        ).read_text(encoding="utf-8")

        self.assertIn("总计推荐 1–3 项材料", readme)
        self.assertNotIn("为每个高价值问题匹配 1–3 项材料", readme)
        self.assertIn("已被当前报告契约取代", old_design)
        self.assertIn("已被当前报告契约取代", old_plan)
        self.assertIn("提炼学习", ui_metadata)
        self.assertIn("可继续追问", ui_metadata)

    def test_learning_is_a_fixed_core_section_with_transferable_change(self):
        contract = (SKILL_ROOT / "references" / "report-contract.md").read_text(encoding="utf-8")
        for phrase in (
            "触发问题",
            "新获得的知识",
            "原有理解如何改变",
            "可迁移应用",
            "不能复述",
        ):
            self.assertIn(phrase, contract)

    def test_ai_questions_are_copyable_and_trace_back_to_the_review(self):
        contract = (SKILL_ROOT / "references" / "report-contract.md").read_text(encoding="utf-8")
        for phrase in (
            "3–5 个",
            "可直接复制",
            "想解决什么",
            "对应学习或问题",
            "尚未解决",
            "待验证判断",
            "下一步决策",
            "100–140 个中文字符",
            "不得把对应关系改写成小标题",
        ):
            self.assertIn(phrase, contract)

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
            "书籍",
            "思维",
            "生活",
        ):
            self.assertIn(phrase, contract)

    def test_optional_idempotent_notion_publish_contract(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        publishing = (SKILL_ROOT / "references" / "notion-publishing.md").read_text(encoding="utf-8")
        self.assertIn("--publish", skill)
        self.assertIn("默认不写入 Notion", skill)
        self.assertIn("日期 + 类型", publishing)
        self.assertIn("AI 步伐", publishing)
        self.assertIn("存在则更新", publishing)
        self.assertIn("发布失败不得影响", publishing)

    def test_outcome_grouping_keeps_evidence_status(self):
        contract = (SKILL_ROOT / "references" / "report-contract.md").read_text(encoding="utf-8")
        for phrase in ("业务主题", "成果动词", "完成证据", "真正受阻"):
            self.assertIn(phrase, contract)

    def test_publish_contract_avoids_private_fallbacks(self):
        texts = [
            (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8"),
            (SKILL_ROOT / "references" / "notion-publishing.md").read_text(encoding="utf-8"),
        ]
        for forbidden in ("NOTION_TOKEN", "notion_API-post-search", "127.0.0.1", "notion.js"):
            self.assertNotIn(forbidden, "\n".join(texts))


if __name__ == "__main__":
    unittest.main()
