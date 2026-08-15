import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
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

    def test_report_contract_prioritizes_diagnosis_over_activity_log(self):
        contract = (SKILL_ROOT / "references" / "report-contract.md").read_text(encoding="utf-8")
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        readme = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
        publishing = (SKILL_ROOT / "references" / "notion-publishing.md").read_text(
            encoding="utf-8"
        )

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
        self.assertNotIn("固定包含昨日概览", readme)
        self.assertNotIn("标题、六节、链接", publishing)

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
