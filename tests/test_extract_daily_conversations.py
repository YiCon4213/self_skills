import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts" / "extract_daily_conversations.py"
README = SKILL / "README.md"


def write_jsonl(path, records, bad=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        if bad:
            handle.write("{bad json\n")


def codex_user(ts, text, uid="u1", session="s1"):
    return {"timestamp": ts, "session_id": session, "type": "event_msg",
            "payload": {"type": "user_message", "uuid": uid, "text": text}}


def run_cli(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                          text=True, capture_output=True, encoding="utf-8")


class ExtractDailyConversationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.codex = self.root / "codex"
        self.claude = self.root / "claude"
        self.output = self.root / "out.json"

    def tearDown(self):
        self.temp.cleanup()

    def extract(self, *extra):
        result = run_cli("extract", "--date", "2026-08-04", "--timezone", "Asia/Shanghai",
                         "--output", self.output, "--codex-root", self.codex,
                         "--claude-root", self.claude, *extra)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(self.output.read_text(encoding="utf-8"))

    def test_timezone_boundary_and_old_session_are_included_by_record_timestamp(self):
        path = self.codex / "sessions" / "old.jsonl"
        write_jsonl(path, [
            codex_user("2026-08-03T15:59:59Z", "too early", "a"),
            codex_user("2026-08-03T16:00:00Z", "start", "b"),
            {"timestamp": "2026-08-04T15:59:59Z", "session_id": "s1", "type": "event_msg",
             "payload": {"type": "task_complete", "last_agent_message": "done", "uuid": "c"}},
            codex_user("2026-08-04T16:00:00Z", "too late", "d"),
            {"session_id": "s1", "type": "event_msg", "payload": {"type": "user_message", "text": "no time"}},
        ])
        data = self.extract()
        session = data["sessions"][0]
        self.assertEqual([m["text"] for m in session["user_requests"]], ["start"])
        self.assertEqual([m["text"] for m in session["assistant_outcomes"]], ["done"])
        self.assertEqual(data["stats"]["files_matched"], 1)

    def test_codex_fallback_dedupes_and_collects_actions_without_tool_text(self):
        path = self.codex / "archived_sessions" / "s.jsonl"
        write_jsonl(path, [
            codex_user("2026-08-04T01:00:00Z", "same", "same"),
            {"timestamp": "2026-08-04T01:00:00Z", "session_id": "s1", "type": "response_item",
             "payload": {"type": "message", "role": "user", "id": "fallback", "content": [{"type": "input_text", "text": "same"}]}},
            {"timestamp": "2026-08-04T01:01:00Z", "session_id": "s1", "type": "response_item",
             "payload": {"type": "function_call", "name": "search", "status": "completed", "arguments": "secret"}},
            {"timestamp": "2026-08-04T01:02:00Z", "session_id": "s1", "type": "response_item",
             "payload": {"type": "message", "role": "developer", "content": [{"type": "input_text", "text": "hidden"}]}},
        ])
        data = self.extract()
        session = data["sessions"][0]
        self.assertEqual([m["text"] for m in session["user_requests"]], ["same"])
        self.assertEqual(session["actions"], [{"name": "search", "status": "completed", "timestamp": "2026-08-04T01:01:00Z"}])
        self.assertEqual(data["stats"]["deduplicated_messages"], 1)

    def test_claude_direct_project_files_only_filters_and_dedupes_streamed_text(self):
        direct = self.claude / "projects" / "project-a" / "chat.jsonl"
        nested = self.claude / "projects" / "project-a" / "sub" / "tool.jsonl"
        write_jsonl(direct, [
            {"type": "user", "uuid": "cu", "timestamp": "2026-08-04T03:00:00Z", "sessionId": "c1", "message": {"content": "Ask plainly"}},
            {"type": "user", "isMeta": True, "timestamp": "2026-08-04T03:01:00Z", "sessionId": "c1", "message": {"content": "meta"}},
            {"type": "assistant", "uuid": "ca", "timestamp": "2026-08-04T03:02:00Z", "sessionId": "c1", "message": {"content": [{"type": "text", "text": "Answer"}, {"type": "thinking", "thinking": "hide"}, {"type": "tool_use", "name": "x"}]}},
            {"type": "assistant", "uuid": "ca", "timestamp": "2026-08-04T03:03:00Z", "sessionId": "c1", "message": {"content": [{"type": "text", "text": "Answer"}]}},
        ])
        write_jsonl(nested, [{"type": "user", "timestamp": "2026-08-04T03:00:00Z", "message": {"content": "nested"}}])
        data = self.extract()
        session = data["sessions"][0]
        self.assertEqual([m["text"] for m in session["user_requests"]], ["Ask plainly"])
        self.assertEqual([m["text"] for m in session["assistant_outcomes"]], ["Answer"])
        self.assertEqual(data["stats"]["deduplicated_messages"], 1)

    def test_context_tiers_and_global_budget_record_truncation(self):
        path = self.codex / "sessions" / "large.jsonl"
        huge = "HEAD question? " + ("body " * 15000) + "TAIL please act."
        medium = "MIDDLE question? " + ("m " * 4000) + "END act."
        write_jsonl(path, [codex_user("2026-08-04T02:00:00Z", huge, "h", "huge"),
                           codex_user("2026-08-04T02:01:00Z", medium, "m", "medium")])
        data = self.extract("--max-total-chars", "1500")
        texts = [m["text"] for s in data["sessions"] for m in s["user_requests"]]
        self.assertLessEqual(sum(map(len, texts)), 1500)
        self.assertTrue(texts[0].startswith("HEAD"))
        self.assertGreater(data["stats"]["truncated_characters"], 0)

    def test_malformed_missing_timestamp_and_one_source_warn_without_bodies(self):
        write_jsonl(self.codex / "sessions" / "bad.jsonl", [
            {"type": "event_msg", "payload": {"type": "user_message", "text": "secret body"}},
            codex_user("invalid", "also secret", "x"),
        ], bad=True)
        data = self.extract()
        self.assertEqual(data["sources"], ["codex"])
        warnings = " ".join(data["warnings"])
        self.assertIn("malformed", warnings.lower())
        self.assertNotIn("secret", warnings)
        self.assertEqual(data["stats"]["malformed_lines"], 1)

    def test_show_caps_text_and_not_found_is_nonzero(self):
        write_jsonl(self.codex / "sessions" / "show.jsonl", [codex_user("2026-08-04T04:00:00Z", "z" * 7000, "showme", "show")])
        data = self.extract()
        msg = data["sessions"][0]["user_requests"][0]
        shown = run_cli("show", "--source", "codex", "--session-id", "show", "--message-id", msg["message_id"],
                        "--codex-root", self.codex, "--claude-root", self.claude, "--max-chars", "9999")
        self.assertEqual(shown.returncode, 0, shown.stderr)
        payload = json.loads(shown.stdout)
        self.assertEqual(len(payload["text"]), 6000)
        self.assertFalse(Path(payload["source_file"]).is_absolute())
        missing = run_cli("show", "--source", "codex", "--session-id", "show", "--message-id", "nope", "--codex-root", self.codex)
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("not found", missing.stderr.lower())

    def test_windows_locked_read_fallback_is_used(self):
        spec = importlib.util.spec_from_file_location("extractor", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        warnings, stats = [], {"skipped_locked_files": 0, "malformed_lines": 0}
        with patch("builtins.open", side_effect=PermissionError), patch.object(module.os, "name", "nt"), patch.object(module, "_windows_shared_read", return_value='{"ok": true}'):
            records = list(module.iter_jsonl(Path("locked.jsonl"), warnings, stats))
        self.assertEqual(records[0][0]["ok"], True)
        self.assertEqual(stats["skipped_locked_files"], 0)

    def test_sanitizer_removes_secrets_paths_urls_and_code(self):
        spec = importlib.util.spec_from_file_location("extractor_sanitize", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        text = "token=abc123 https://bob:pw@example.com/a?key=secret C:\\Users\\alice\\repo\\app.py /home/bob/private/proj/x ```python\\nprint('x')\\n``` Traceback (most recent call last):\n  File 'x.py', line 3\nPlease summarize this safely."
        cleaned = module.sanitize_search_brief(text)
        self.assertIn("Please summarize this safely", cleaned)
        self.assertNotIn("abc123", cleaned)
        self.assertNotIn("alice", cleaned.lower())
        self.assertNotIn("example.com", cleaned)
        self.assertNotIn("print", cleaned)
        self.assertLessEqual(len(cleaned), 240)


class FixRoundRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.codex = self.root / "codex"
        self.claude = self.root / "claude"
        self.output = self.root / "out.json"

    def tearDown(self):
        self.temp.cleanup()

    def extract(self, day="2026-08-04", zone="Asia/Shanghai", *extra):
        result = run_cli("extract", "--date", day, "--timezone", zone, "--output", self.output,
                         "--codex-root", self.codex, "--claude-root", self.claude, *extra)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(self.output.read_text(encoding="utf-8"))

    def test_iter_jsonl_yields_before_reading_the_next_line(self):
        spec = importlib.util.spec_from_file_location("extractor_stream", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        class OneLineThenFail:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def __iter__(self):
                yield '{"first": true}'
                raise AssertionError("iterator was eagerly consumed")
        with patch("builtins.open", return_value=OneLineThenFail()):
            records = module.iter_jsonl(Path("stream.jsonl"), [], {"malformed_lines": 0, "skipped_locked_files": 0})
            self.assertEqual(next(records)[0], {"first": True})

    def test_dedupe_keeps_distinct_same_text_and_only_drops_stable_or_fallback_duplicates(self):
        write_jsonl(self.codex / "sessions" / "dupes.jsonl", [
            codex_user("2026-08-04T01:00:00Z", "repeat", "one", "dupes"),
            codex_user("2026-08-04T01:01:00Z", "repeat", "two", "dupes"),
            codex_user("2026-08-04T01:01:00Z", "repeat", "two", "dupes"),
            {"timestamp": "2026-08-04T01:00:00Z", "session_id": "dupes", "type": "response_item", "payload": {"type": "message", "role": "user", "id": "fallback", "content": [{"type": "input_text", "text": "repeat"}]}},
        ])
        data = self.extract()
        requests = data["sessions"][0]["user_requests"]
        self.assertEqual([item["message_id"] for item in requests], ["one", "two"])
        self.assertEqual(data["stats"]["deduplicated_messages"], 2)

    def test_extraction_adds_sanitized_search_brief_without_changing_local_text(self):
        secret = "Please help C:\\\\Users\\\\alice\\\\secret-repo\\\\app.py token=abc https://bob:pw@example.test/x?q=hide ```py\\nprint(1)\\n``` Traceback (most recent call last):\\n  File 'x.py', line 1"
        write_jsonl(self.codex / "sessions" / "brief.jsonl", [codex_user("2026-08-04T01:00:00Z", secret, "brief", "brief")])
        request = self.extract()["sessions"][0]["user_requests"][0]
        self.assertEqual(request["text"], secret)
        self.assertIn("Please help", request["search_brief"])
        for forbidden in ("alice", "secret-repo", "abc", "example.test", "print"):
            self.assertNotIn(forbidden, request["search_brief"].lower())
        self.assertLessEqual(len(request["search_brief"]), 240)

    def test_enumeration_oserror_adds_generic_warning_and_continues(self):
        spec = importlib.util.spec_from_file_location("extractor_enum", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        projects = self.claude / "projects"
        projects.mkdir(parents=True)
        with patch.object(Path, "iterdir", side_effect=OSError("private path should not leak")):
            data = module.build_report(__import__("datetime").date(2026, 8, 4), "Asia/Shanghai", self.codex, self.claude, 80000)
        self.assertTrue(any("enumerat" in warning.lower() for warning in data["warnings"]))
        self.assertNotIn("private", " ".join(data["warnings"]))

    def test_sorting_uses_utc_instants_not_timestamp_strings(self):
        write_jsonl(self.codex / "sessions" / "offsets.jsonl", [
            codex_user("2026-08-04T00:30:00+02:00", "first in UTC", "a", "offset"),
            codex_user("2026-08-03T23:00:00Z", "second in UTC", "b", "offset"),
        ])
        data = self.extract("2026-08-04", "Europe/Berlin")
        self.assertEqual([m["text"] for m in data["sessions"][0]["user_requests"]], ["first in UTC", "second in UTC"])

    def test_non_shanghai_zone_and_default_eighty_thousand_character_budget(self):
        write_jsonl(self.codex / "sessions" / "zones.jsonl", [
            codex_user("2026-08-04T03:59:59Z", "prior eastern day", "early", "zone"),
            codex_user("2026-08-04T04:00:00Z", "eastern start", "start", "zone"),
        ] + [codex_user("2026-08-04T12:00:00Z", "x" * 5999 + "?", f"bulk-{i}", f"bulk-{i}") for i in range(14)])
        data = self.extract("2026-08-04", "America/New_York")
        zone_session = next(session for session in data["sessions"] if session["session_id"] == "zone")
        self.assertEqual([m["text"] for m in zone_session["user_requests"]], ["eastern start"])
        self.assertEqual(data["stats"]["included_characters"], 80000)
        self.assertEqual(data["stats"]["truncated_characters"], 4013)

    def test_codex_subagent_session_meta_excludes_the_whole_file(self):
        write_jsonl(self.codex / "sessions" / "subagent.jsonl", [
            {"type": "session_meta", "payload": {"thread_source": "sub-agent"}},
            codex_user("2026-08-04T01:00:00Z", "must not appear", "sub", "sub"),
        ])
        write_jsonl(self.codex / "sessions" / "main.jsonl", [codex_user("2026-08-04T01:00:00Z", "main only", "main", "main")])
        data = self.extract()
        self.assertEqual([session["session_id"] for session in data["sessions"]], ["main"])

class FixRoundTwoRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.codex = self.root / "codex"
        self.claude = self.root / "claude"

    def tearDown(self):
        self.temp.cleanup()

    def test_show_rejects_a_codex_subagent_file(self):
        write_jsonl(self.codex / "sessions" / "subagent-show.jsonl", [
            {"type": "session_meta", "payload": {"thread_source": "subagent"}},
            codex_user("2026-08-04T01:00:00Z", "do not expose", "hidden", "hidden-session"),
        ])
        result = run_cli("show", "--source", "codex", "--session-id", "hidden-session", "--message-id", "hidden", "--codex-root", self.codex, "--claude-root", self.claude)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not found", result.stderr.lower())

    def test_sanitizer_removes_plain_code_and_private_path_adjacent_project_names(self):
        spec = importlib.util.spec_from_file_location("extractor_sanitize_round_two", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        text = "Discuss Python and JavaScript. secret-repo at C:\\Users\\alice\\secret-repo\\src. /home/bob/private/other-project (other-project).\nimport os\nvalue = {\"password\": 1}\ndef private_fn():\n  return value\n  File \"app.py\", line 9\nKeep the safe summary."
        cleaned = module.sanitize_search_brief(text)
        self.assertIn("Python", cleaned)
        self.assertIn("JavaScript", cleaned)
        self.assertIn("Keep the safe summary", cleaned)
        for forbidden in ("secret-repo", "other-project", "import os", "value =", "private_fn", "app.py"):
            self.assertNotIn(forbidden, cleaned.lower())
        self.assertLessEqual(len(cleaned), 240)

class FixRoundThreeRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.codex = self.root / "codex"

    def tearDown(self):
        self.temp.cleanup()

    def test_codex_collection_streams_each_file_once(self):
        spec = importlib.util.spec_from_file_location("extractor_single_pass", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        write_jsonl(self.codex / "sessions" / "single.jsonl", [codex_user("2026-08-04T01:00:00Z", "one pass", "one", "single")])
        original = module.iter_jsonl
        calls = []
        def counted(*args, **kwargs):
            calls.append(args[0])
            yield from original(*args, **kwargs)
        stats = {"files_scanned": 0, "files_matched": 0, "malformed_lines": 0, "skipped_locked_files": 0}
        with patch.object(module, "iter_jsonl", counted):
            messages, _ = module.collect_source(self.codex, "codex", __import__("zoneinfo").ZoneInfo("Asia/Shanghai"), __import__("datetime").date(2026, 8, 4), [], stats)
        self.assertEqual(len(calls), 1)
        self.assertEqual([message["text"] for message in messages], ["one pass"])

    def test_sanitizer_removes_structural_code_and_all_labeled_path_adjacency_forms(self):
        spec = importlib.util.spec_from_file_location("extractor_sanitize_round_three", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        text = """Discuss Rust and TypeScript for the migration.
project-x: C:\\Users\\sam\\project-x\\src
repo project-y = C:\\work\\project-y\\main
C:\\private\\project-z\\app, project-z
/private/project-q (repo project-q)
console.log(value);
client.send(payload)
if ready:
for item in items:
while active:
try:
catch (error) {
const render = () => value;
{ key: value; }
Keep the product design discussion."""
        cleaned = module.sanitize_search_brief(text)
        for safe in ("Rust", "TypeScript", "migration", "product design discussion"):
            self.assertIn(safe, cleaned)
        for forbidden in ("project-x", "project-y", "project-z", "project-q", "users", "console.log", "client.send", "if ready", "for item", "while active", "try", "catch", "render", "key: value"):
            self.assertNotIn(forbidden, cleaned.lower())
        self.assertLessEqual(len(cleaned), 240)


class RepositoryDocumentationTests(unittest.TestCase):
    def test_readme_documents_human_facing_usage_privacy_and_output(self):
        self.assertTrue(README.is_file(), "README.md must exist at the repository root")
        content = README.read_text(encoding="utf-8")
        for required in ("review-daily-ai-work", "$review-daily-ai-work",
                         "D:\\Web\\new_think", "隐私", "测试"):
            self.assertIn(required, content)


class FinalReviewRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.codex = self.root / "codex"
        self.claude = self.root / "claude"
        self.output = self.root / "out.json"

    def tearDown(self):
        self.temp.cleanup()

    def extract(self):
        result = run_cli("extract", "--date", "2026-08-04", "--timezone", "Asia/Shanghai",
                         "--output", self.output, "--codex-root", self.codex,
                         "--claude-root", self.claude)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(self.output.read_text(encoding="utf-8"))

    def test_sanitizer_removes_accounts_labeled_projects_and_unlabeled_credentials(self):
        spec = importlib.util.spec_from_file_location("extractor_final_sanitize", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        text = ("Research OAuth for alice@example.com and @alice. "
                "repository=private-repo project secret-project "
                "sk-abcdefghijklmnopqrstuvwxyz123456 ghp_abcdefghijklmnopqrstuvwxyz123456 "
                "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.signature "
                "Compare official authentication guidance.")
        cleaned = module.sanitize_search_brief(text)
        self.assertIn("OAuth", cleaned)
        self.assertIn("official authentication guidance", cleaned)
        for forbidden in ("alice", "example.com", "private-repo", "secret-project", "sk-",
                          "ghp_", "eyjhb", "signature"):
            self.assertNotIn(forbidden, cleaned.lower())
        self.assertLessEqual(len(cleaned), 240)

    def test_sanitizer_removes_space_separated_cli_credentials_and_accounts(self):
        spec = importlib.util.spec_from_file_location("extractor_cli_sanitize", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cleaned = module.sanitize_search_brief(
            "Run deploy --token supersecret --account alice --api-key keyvalue then review deployment safety."
        )
        self.assertIn("deployment safety", cleaned)
        for forbidden in ("supersecret", "alice", "keyvalue"):
            self.assertNotIn(forbidden, cleaned.lower())

    def test_fallback_message_ids_are_unique_across_files_and_show_is_precise(self):
        for project, text in (("project-a", "first fallback"), ("project-b", "second fallback")):
            write_jsonl(self.claude / "projects" / project / "same.jsonl", [{
                "timestamp": "2026-08-04T01:00:00Z", "sessionId": "shared-session",
                "type": "user", "message": {"content": text},
            }])
        data = self.extract()
        requests = data["sessions"][0]["user_requests"]
        self.assertEqual(len({item["message_id"] for item in requests}), 2)
        for item in requests:
            shown = run_cli("show", "--source", "claude", "--session-id", "shared-session",
                            "--message-id", item["message_id"], "--codex-root", self.codex,
                            "--claude-root", self.claude)
            self.assertEqual(shown.returncode, 0, shown.stderr)
            self.assertEqual(json.loads(shown.stdout)["text"], item["text"])

    def test_show_rejects_ambiguous_stable_locator(self):
        for project, text in (("project-a", "first"), ("project-b", "second")):
            write_jsonl(self.claude / "projects" / project / "same.jsonl", [{
                "timestamp": "2026-08-04T01:00:00Z", "sessionId": "shared-session",
                "type": "user", "uuid": "duplicate-id", "message": {"content": text},
            }])
        shown = run_cli("show", "--source", "claude", "--session-id", "shared-session",
                        "--message-id", "duplicate-id", "--codex-root", self.codex,
                        "--claude-root", self.claude)
        self.assertNotEqual(shown.returncode, 0)
        self.assertIn("ambiguous", shown.stderr.lower())

    def test_show_rejects_same_file_duplicate_stable_locator(self):
        duplicate = {
            "timestamp": "2026-08-04T01:00:00Z", "sessionId": "shared-session",
            "type": "user", "uuid": "duplicate-id", "message": {"content": "same text"},
        }
        write_jsonl(self.claude / "projects" / "project-a" / "same.jsonl", [duplicate, duplicate])
        shown = run_cli("show", "--source", "claude", "--session-id", "shared-session",
                        "--message-id", "duplicate-id", "--codex-root", self.codex,
                        "--claude-root", self.claude)
        self.assertNotEqual(shown.returncode, 0)
        self.assertIn("ambiguous", shown.stderr.lower())

    def test_absent_sources_are_explicitly_disclosed(self):
        data = self.extract()
        self.assertEqual(data["sources"], [])
        self.assertEqual(data["stats"]["unavailable_sources"], 2)
        warnings = " ".join(data["warnings"]).lower()
        self.assertIn("codex source unavailable", warnings)
        self.assertIn("claude source unavailable", warnings)


if __name__ == "__main__":
    unittest.main()
