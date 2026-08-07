#!/usr/bin/env python3
"""Extract privacy-conscious daily conversation summaries from local JSONL logs."""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date as Date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


def sanitize_search_brief(text: str) -> str:
    """Return a bounded, privacy-preserving topic hint, not source content."""
    value = str(text or "").replace("\\n", "\n")
    value = re.sub(r"```.*?```", " ", value, flags=re.S)
    value = re.sub(r"`[^`]*`", " ", value)
    value = re.sub(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[account-redacted]", value)
    value = re.sub(r"(?<!\w)@[A-Za-z0-9_]{2,}", "[account-redacted]", value)
    value = re.sub(r"(?i)\b(?:repository|repo|project|仓库|项目)\s*(?:name\s*)?(?::|=|\s)\s*[\w.-]+", "[project-redacted]", value)
    value = re.sub(r"(?i)\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_-]{16,}|github_pat_[A-Za-z0-9_-]{16,})\b", "[credential-redacted]", value)
    value = re.sub(r"\beyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\b", "[credential-redacted]", value)
    value = re.sub(r"(?i)(?:--?|/)(?:api[-_]?key|token|password|passwd|secret|authorization|account|username|user[-_]?id|login)\s*(?:=|\s)\s*['\"]?[^\s,'\"]+", "[credential-redacted]", value)
    value = re.sub(r"(?i)\b(?:account|username|user[-_]?id|login|账号|账户)\s*(?::|=|\s)\s*['\"]?[^\s,'\"]+", "[account-redacted]", value)
    path = r"(?:[a-z]:\\+|\\+|/)(?:[^\s\\/,()]+[\\/]+)*[^\s\\/,()]*"
    label = r"(?:repo\s+)?[\w.-]+"
    # Remove path-adjacent names before replacing paths, including labels on
    # either side. This deliberately leaves ordinary topic words untouched.
    value = re.sub(r"(?i)\b[\w.-]+\s+(?:at|in|from)\s+" + path, "[path-redacted]", value)
    value = re.sub(r"(?i)\b" + label + r"\s*(?::|=)\s*" + path, "[path-redacted]", value)
    value = re.sub(path + r"\s*,\s*" + label, "[path-redacted]", value, flags=re.I)
    value = re.sub(path + r"\s*\(\s*" + label + r"\s*\)", "[path-redacted]", value, flags=re.I)
    value = re.sub(r"(?i)\b(?:api[_-]?key|token|password|passwd|secret|authorization)\s*[:=]\s*['\"]?[^\s,'\"]+", "[redacted]", value)
    value = re.sub(r"https?://[^\s/]+(?::[^@\s/]+)?@[^\s/?#]+[^\s]*", "[url-redacted]", value)
    value = re.sub(r"https?://[^\s]+(?:\?[^\s]+|#[^\s]+)", "[url-redacted]", value)
    value = re.sub(path, "[path-redacted]", value, flags=re.I)
    # A generic path match may have consumed the path before a trailing label.
    value = re.sub(r"\[path-redacted\]\s*,\s*" + label, "[path-redacted]", value, flags=re.I)
    value = re.sub(r"\[path-redacted\]\s*\(\s*" + label + r"\s*\)", "[path-redacted]", value, flags=re.I)
    kept = []
    code_line = re.compile(r"""(?ix)^\s*(?:
        from\s+\S+\s+import\b | import\s+\S+ | def\s+\w+ | class\s+\w+ | function\s+\w+ |
        (?:const|let|var)\s+\w+\s*= | \w[\w.]*\s*= | return\b |
        file\s+['\"] | at\s+\S+\s*\( | traceback\b | exception: | error: | \^ |
        (?:if|for|while)\b.*: | (?:try|catch|finally|switch)\b.*[:{] |
        \w+(?:\.\w+)+\s*\([^)]*\)\s*;? | .*=>.*
    )""")
    for line in value.splitlines():
        stripped = line.strip()
        punctuation = sum(character in "{};" for character in stripped)
        if code_line.match(stripped) or punctuation >= 2 or stripped in {"{", "}"}:
            continue
        kept.append(line)
    return re.sub(r"\s+", " ", " ".join(kept)).strip()[:240]

def _windows_shared_read(path: Path) -> str:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel32.CreateFileW
    create.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    create.restype = ctypes.c_void_p
    handle = create(str(path), 0x80000000, 0x1 | 0x2 | 0x4, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise PermissionError(ctypes.get_last_error(), "CreateFileW failed", str(path))
    try:
        chunks, buffer, read_count = [], ctypes.create_string_buffer(65536), ctypes.c_uint32()
        while kernel32.ReadFile(handle, buffer, len(buffer), ctypes.byref(read_count), None) and read_count.value:
            chunks.append(buffer.raw[:read_count.value])
        return b"".join(chunks).decode("utf-8", errors="replace")
    finally:
        kernel32.CloseHandle(handle)


def _parse_line(line: str, warnings: list[str], stats: dict):
    try:
        item = json.loads(line)
        if not isinstance(item, dict):
            raise ValueError("not object")
        return item
    except (json.JSONDecodeError, ValueError):
        stats["malformed_lines"] += 1
        warnings.append("malformed JSONL input encountered")
        return None


def iter_jsonl(path: Path, warnings: list[str], stats: dict):
    """Yield decoded JSON objects one line at a time, including lock fallback."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for number, line in enumerate(handle, 1):
                item = _parse_line(line, warnings, stats)
                if item is not None:
                    yield item, number
        return
    except PermissionError:
        if os.name != "nt":
            stats["skipped_locked_files"] += 1; warnings.append("locked or unreadable input skipped"); return
    except OSError:
        stats["skipped_locked_files"] += 1; warnings.append("unreadable input skipped"); return
    try:
        for number, line in enumerate(_windows_shared_read(path).splitlines(), 1):
            item = _parse_line(line, warnings, stats)
            if item is not None:
                yield item, number
    except OSError:
        stats["skipped_locked_files"] += 1; warnings.append("locked or unreadable input skipped")


def parse_timestamp(record: dict):
    raw = record.get("timestamp") or record.get("created_at")
    if not isinstance(raw, str): return None, None
    try:
        instant = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return (instant, raw) if instant.tzinfo else (None, None)
    except ValueError:
        return None, None


def text_blocks(content, allowed=("text",)):
    if isinstance(content, str): return content
    if not isinstance(content, list): return ""
    return "\n".join(block.get("text") or block.get("input_text") for block in content if isinstance(block, dict) and block.get("type") in allowed and isinstance(block.get("text") or block.get("input_text"), str))


def record_id(record: dict, payload: dict, line: int, source_file_id: str):
    for value in (payload.get("uuid"), payload.get("id"), record.get("uuid"), record.get("id")):
        if isinstance(value, str) and value: return value, True
    digest = hashlib.sha256(f"{source_file_id}:{line}".encode("utf-8")).hexdigest()[:16]
    return f"line-{digest}", False


def session_id(record: dict, path: Path):
    for key in ("session_id", "sessionId", "conversation_id", "conversationId"):
        if isinstance(record.get(key), str) and record[key]: return record[key]
    return path.stem


def source_identifier(root: Path, path: Path):
    try: return path.relative_to(root).as_posix()
    except ValueError: return path.name


def eligible_codex(record, path, line, source_file_id=None):
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
    kind, role, text, action, fallback = payload.get("type"), None, "", None, False
    if record.get("type") == "event_msg" and kind == "user_message": role, text = "user", payload.get("text", "")
    elif record.get("type") == "event_msg" and kind == "task_complete": role, text = "assistant", payload.get("last_agent_message", "")
    elif record.get("type") == "response_item" and kind == "message" and payload.get("role") == "user": role, text, fallback = "user", text_blocks(payload.get("content"), ("input_text",)), True
    elif record.get("type") == "response_item" and kind in ("function_call", "custom_tool_call"): action = {"name": payload.get("name", "unknown"), "status": payload.get("status", "unknown")}
    mid, stable = record_id(record, payload, line, source_file_id or path.name)
    return role, text.strip() if isinstance(text, str) else "", action, mid, stable, fallback


def eligible_claude(record, path, line, source_file_id=None):
    kind = record.get("type")
    if kind not in ("user", "assistant") or (kind == "user" and record.get("isMeta") is True): return None, "", None, "", False, False
    message = record.get("message") if isinstance(record.get("message"), dict) else {}
    content = message.get("content", record.get("content"))
    text = (text_blocks(content, ("text",)) if isinstance(content, list) else content) if kind == "user" else text_blocks(content, ("text",))
    mid, stable = record_id(record, message, line, source_file_id or path.name)
    return kind, text.strip() if isinstance(text, str) else "", None, mid, stable, False


def candidate_files(root: Path, source: str, warnings: list[str], stats: dict):
    try:
        if source == "codex":
            found = []
            for base in (root / "sessions", root / "archived_sessions"):
                if base.is_dir(): found.extend(p for p in base.rglob("*.jsonl") if p.is_file())
            return sorted(found)
        projects = root / "projects"
        if not projects.is_dir(): return []
        return sorted(p for project in projects.iterdir() if project.is_dir() for p in project.glob("*.jsonl") if p.is_file())
    except OSError:
        warnings.append("input directory enumeration failed")
        return []


def is_subagent_meta(record: dict):
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
    origin = payload.get("thread_source")
    normalized = re.sub(r"[-_\s]", "", str(origin).lower())
    return record.get("type") == "session_meta" and "subagent" in normalized


def codex_file_is_subagent(path: Path, warnings: list[str], stats: dict) -> bool:
    """Use one metadata predicate for extract and show via a streaming probe."""
    # Probing must not double-count malformed input; the caller's real scan
    # records warnings and statistics exactly once.
    probe_stats = {"malformed_lines": 0, "skipped_locked_files": 0}
    return any(is_subagent_meta(record) for record, _ in iter_jsonl(path, [], probe_stats))

def collect_source(root, source, zone, target, warnings, stats):
    files = candidate_files(root, source, warnings, stats)
    if files:
        stats.setdefault("_available_sources", []).append(source)
    else:
        stats["unavailable_sources"] = stats.get("unavailable_sources", 0) + 1
        warnings.append(f"{source} source unavailable")
    stats["files_scanned"] += len(files)
    start = datetime.combine(target, time.min, tzinfo=zone) if target else None
    end, messages, actions, matched = (start + timedelta(days=1) if start else None), [], [], set()
    for path in files:
        # Buffer eligible metadata only. If a later session marker identifies
        # a subagent, discard this file's buffer without a second scan.
        file_messages, file_actions, subagent = [], [], False
        location = source_identifier(root, path)
        for record, line in iter_jsonl(path, warnings, stats):
            if source == "codex" and is_subagent_meta(record):
                subagent = True
                break
            instant, raw_ts = parse_timestamp(record)
            if target is not None and (instant is None or not (start <= instant.astimezone(zone) < end)): continue
            role, text, action, mid, stable, fallback = (eligible_codex(record, path, line, location) if source == "codex" else eligible_claude(record, path, line, location))
            sid = session_id(record, path)
            if action:
                file_actions.append({**action, "timestamp": raw_ts or "", "_instant": instant, "_source": source, "_session": sid, "_file": location})
            if role and text:
                item = {"source": source, "session_id": sid, "role": role, "message_id": mid, "timestamp": raw_ts or "", "text": text, "locator": {"source_file": location, "line": line}, "_instant": instant, "_order": line, "_stable": stable, "_fallback": fallback}
                if role == "user": item["search_brief"] = sanitize_search_brief(text)
                file_messages.append(item)
        if not subagent and (file_messages or file_actions):
            messages.extend(file_messages); actions.extend(file_actions); matched.add(path)
    stats["files_matched"] += len(matched)
    return messages, actions


def compact(text, limit):
    if len(text) <= limit: return text
    if limit <= 0: return ""
    head, tail = text[:max(1, limit // 3)].rstrip(), text[-max(1, limit // 3):].lstrip()
    notable = [sentence.strip() for sentence in re.split(r"(?<=[?.!])\s+", text) if "?" in sentence or re.match(r"(?i)^(please|do|make|create|fix|review|write|summarize|explain)\b", sentence.strip())]
    middle = " ".join(notable[:2])
    if middle:
        return (f"{head} … {middle[:max(0, limit - len(head) - len(tail) - 6)]} … {tail}")[:limit]
    return (f"{head} … {tail}")[:limit]


def public_message(item): return {key: value for key, value in item.items() if not key.startswith("_")}
def public_action(item): return {key: value for key, value in item.items() if not key.startswith("_")}


def build_report(target, zone_name, codex, claude, maximum):
    zone = ZoneInfo(zone_name)
    stats = {"files_scanned": 0, "files_matched": 0, "malformed_lines": 0, "skipped_locked_files": 0, "unavailable_sources": 0, "deduplicated_messages": 0, "truncated_characters": 0, "included_characters": 0, "_available_sources": []}
    warnings, all_messages, all_actions = [], [], []
    for source, root in (("codex", codex), ("claude", claude)):
        messages, actions = collect_source(root, source, zone, target, warnings, stats)
        all_messages.extend(messages); all_actions.extend(actions)
    ordered = sorted(all_messages, key=lambda item: (item["_instant"].astimezone(timezone.utc), item["source"], item["session_id"], item["message_id"], item["_order"]))
    event_users = {(item["source"], item["session_id"], item["text"], item["_instant"]) for item in ordered if item["role"] == "user" and not item["_fallback"]}
    stable_seen, unique = set(), []
    for item in ordered:
        stable_key = (item["source"], item["session_id"], item["role"], item["message_id"])
        fallback_copy = item["_fallback"] and (item["source"], item["session_id"], item["text"], item["_instant"]) in event_users
        if fallback_copy or (item["_stable"] and stable_key in stable_seen): stats["deduplicated_messages"] += 1; continue
        if item["_stable"]: stable_seen.add(stable_key)
        unique.append(item)
    genuine_total = sum(len(item["text"]) for item in unique)
    grouped = defaultdict(list)
    for item in unique: grouped[(item["source"], item["session_id"])].append(item)
    sessions = []
    for (source, sid), items in sorted(grouped.items(), key=lambda pair: (min(item["_instant"].astimezone(timezone.utc) for item in pair[1]), pair[0][0], pair[0][1])):
        tier = 6000 if sum(len(item["text"]) for item in items) <= 6000 else (2000 if sum(len(item["text"]) for item in items) <= 40000 else 1200)
        for item in items: item["text"] = compact(item["text"], tier)
        source_files = sorted({item["locator"]["source_file"] for item in items})
        actions = sorted((action for action in all_actions if action["_source"] == source and action["_session"] == sid and action["_file"] in source_files), key=lambda action: (action["_instant"].astimezone(timezone.utc), action["name"], action["status"]))
        sessions.append({"source": source, "session_id": sid, "first_timestamp": min(items, key=lambda item: item["_instant"])["timestamp"], "last_timestamp": max(items, key=lambda item: item["_instant"])["timestamp"], "user_requests": [public_message(item) for item in items if item["role"] == "user"], "assistant_outcomes": [public_message(item) for item in items if item["role"] == "assistant"], "actions": [public_action(action) for action in actions], "source_files": source_files})
    remaining = maximum
    for session in sessions:
        for bucket in ("user_requests", "assistant_outcomes"):
            for item in session[bucket]:
                item["text"] = compact(item["text"], remaining)
                remaining -= len(item["text"])
    stats["included_characters"] = maximum - remaining
    stats["truncated_characters"] = max(0, genuine_total - stats["included_characters"])
    sources = list(dict.fromkeys(stats.pop("_available_sources")))
    return {"date": target.isoformat(), "timezone": zone_name, "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "sources": sources, "stats": stats, "sessions": sessions, "warnings": sorted(set(warnings)), "privacy": {"source_file_paths": "redacted to paths relative to configured roots", "search_briefs": "sanitized before use"}}


def show_message(source, sid, message_id, codex, claude, maximum):
    root = codex if source == "codex" else claude
    warnings, stats = [], {"malformed_lines": 0, "skipped_locked_files": 0}
    matches = []
    for path in candidate_files(root, source, warnings, stats):
        if source == "codex" and codex_file_is_subagent(path, warnings, stats):
            continue
        location = source_identifier(root, path)
        for record, line in iter_jsonl(path, warnings, stats):
            role, text, _, mid, _, _ = eligible_codex(record, path, line, location) if source == "codex" else eligible_claude(record, path, line, location)
            if role and text and session_id(record, path) == sid and mid == message_id:
                _, raw = parse_timestamp(record)
                result = {"source": source, "session_id": sid, "message_id": mid, "role": role, "timestamp": raw, "text": text[:min(maximum, 6000)], "source_file": location, "locator": {"source_file": location, "line": line}}
                matches.append(result)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise LookupError("ambiguous message locator")
    raise LookupError("message not found")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__); subs = parser.add_subparsers(dest="command", required=True)
    extract = subs.add_parser("extract"); extract.add_argument("--date", required=True); extract.add_argument("--timezone", required=True); extract.add_argument("--output", required=True); extract.add_argument("--codex-root", default=str(Path.home() / ".codex")); extract.add_argument("--claude-root", default=str(Path.home() / ".claude")); extract.add_argument("--max-total-chars", type=int, default=80000)
    show = subs.add_parser("show"); show.add_argument("--source", choices=("codex", "claude"), required=True); show.add_argument("--session-id", required=True); show.add_argument("--message-id", required=True); show.add_argument("--codex-root", default=str(Path.home() / ".codex")); show.add_argument("--claude-root", default=str(Path.home() / ".claude")); show.add_argument("--max-chars", type=int, default=6000)
    args = parser.parse_args(argv)
    try:
        if args.command == "extract":
            if args.max_total_chars < 0: raise ValueError("max-total-chars must be nonnegative")
            report = build_report(Date.fromisoformat(args.date), args.timezone, Path(args.codex_root), Path(args.claude_root), args.max_total_chars)
            Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            if args.max_chars < 0: raise ValueError("max-chars must be nonnegative")
            print(json.dumps(show_message(args.source, args.session_id, args.message_id, Path(args.codex_root), Path(args.claude_root), args.max_chars), ensure_ascii=False))
        return 0
    except (ValueError, LookupError, OSError) as exc: print(str(exc), file=sys.stderr); return 1

if __name__ == "__main__": raise SystemExit(main())
