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


if __name__ == "__main__":
    unittest.main()
