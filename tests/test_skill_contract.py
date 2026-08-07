import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_codex_chat_coverage_contract(self):
        self.assertTrue((SKILL_ROOT / "references" / "codex-app-chat-collection.md").is_file())

        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for label in ("Codex 编程任务", "Codex 应用聊天", "Claude Code"):
            self.assertIn(label, skill_text)

        report_contract = (SKILL_ROOT / "references" / "report-contract.md").read_text(encoding="utf-8")
        for required_text in ("1–4", "书籍", "思维", "生活"):
            self.assertIn(required_text, report_contract)

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
