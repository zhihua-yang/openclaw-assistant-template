#!/usr/bin/env python3
"""
evolve.py v3.4
- v3.3: 修复时区 bug（naive/aware datetime 混用）
- v3.4: 修复3个字段一致性 bug：
        1. tags 字段名：兼容读取 tags / tag
        2. capabilities：同时读 new-capability 和 learning-achievement
        3. corrections：改为读 content 字段（无 old/new 字段）
        新增：promoted 错误过滤；STANDARD_TYPES/FIELD_TAGS 常量
"""

import json
import re
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta, timezone

STANDARD_TYPES = [
    "task-done", "error-found", "system-improvement", "learning-achievement",
    "user-correction", "automation-deployment", "error-fix", "system-monitoring",
    "quality-verification", "new-capability", "automation-planning", "memory-compaction",
    "pua-inspection", "quality-improvement",
]

FIELD_TAGS    = "tags"
FIELD_TAG_ALT = "tag"

BASE  = Path.home() / ".openclaw/workspace"
MEM   = BASE / "memory/recent.md"
ERRS  = BASE / "memory/errors.md"


def _detect_runtime_dir(base: Path) -> Path:
    candidates = [
        base / ".sys/logs/events.jsonl",
        base / ".openclaw/logs/events.jsonl",
    ]
    for p in candidates:
        if p.exists() and p.stat().st_size > 0:
            return p
    fallback = base / ".sys/logs/events.jsonl"
    fallback.parent.mkdir(parents=True, exist_ok=True)
    fallback.touch()
    return fallback


LOGS = _detect_runtime_dir(BASE)

for _d in ["sessions", "baseline", "todo", "compact"]:
    LOGS.parent.parent.joinpath(_d).mkdir(parents=True, exist_ok=True)
(BASE / "memory/archive").mkdir(parents=True, exist_ok=True)


def _to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def load_recent_events(days=7):
    events = []
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    if not LOGS.exists():
        return events
    for line in LOGS.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
            if "ts" not in e:
                continue
            if _to_naive_utc(datetime.fromisoformat(e["ts"])) >= cutoff:
                events.append(e)
        except (json.JSONDecodeError, ValueError, KeyError):
            pass
    return events


def append_event(type_: str, content: str, tags: list, count: int = 1, extra: dict = None):
    record = {
        "ts":       datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "type":     type_,
        "content":  content,
        FIELD_TAGS: tags,
        "count":    count,
    }
    if extra:
        record.update(extra)
    with LOGS.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def search_memory(keyword: str, top_n: int = 5) -> list:
    results = []
    if not LOGS.exists():
        return results
    kw = keyword.lower()
    for line in LOGS.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        if kw in line.lower():
            try:
                results.append(json.loads(line))
            except Exception:
                pass
    results.sort(key=lambda x: (x.get("count", 1), x.get("ts", "")), reverse=True)
    return results[:top_n]


def get_event_tags(e: dict) -> list:
    """兼容 tags / tag 两种字段名。"""
    return e.get(FIELD_TAGS, e.get(FIELD_TAG_ALT, []))


def extract_insights(events: list) -> dict:
    corrections  = [e for e in events if e.get("type") == "user-correction"]
    errors       = [e for e in events if e.get("type") in (
                        "repeated-error", "user-correction", "bug-analysis", "error-found")]
    capabilities = [e for e in events if e.get("type") in (
                        "new-capability", "learning-achievement")]
    preferences  = [e for e in events if e.get("type") == "preference"]

    error_counts = Counter()
    for e in errors:
        key = e.get("content", "")[:80]
        error_counts[key] += e.get("count", 1)
    frequent_errors = [e for e, c in error_counts.items() if c >= 2]

    all_tags = []
    for e in events:
        all_tags.extend(get_event_tags(e))
    tag_summary = Counter(all_tags).most_common(5)

    return {
        "corrections":      corrections,
        "frequent_errors":  frequent_errors,
        "new_capabilities": [e.get("content", "") for e in capabilities],
        "preferences":      [e.get("content", "") for e in preferences],
        "total_events":     len(events),
        "tag_summary":      tag_summary,
    }


def get_already_promoted_errors() -> list:
    if not ERRS.exists():
        return []
    promoted = []
    current = None
    for line in ERRS.read_text().split("\n"):
        if line.startswith("## [") and "] " in line:
            current = line.split("] ", 1)[1][:80]
        elif current and "promoted" in line:
            promoted.append(current)
            current = None
    return promoted


def _filter_promoted(errors: list) -> list:
    promoted = get_already_promoted_errors()
    return [e for e in errors
            if not any(p in e[:80] or e[:80] in p for p in promoted)]


def update_memory(insights: dict):
    if not MEM.exists():
        print("[evolve] recent.md not found, skipped")
        return
    content  = MEM.read_text()
    ts       = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    total    = insights["total_events"]
    tag_line = ", ".join(f"{t}x{c}" for t, c in insights["tag_summary"]) or "-"

    corrections_text = "\n".join(
        f"- {c.get('content', '(no content)')[:80]}"
        for c in insights["corrections"]
    ) or "- None"

    filtered_errors = _filter_promoted(insights["frequent_errors"])
    errors_text = "\n".join(f"- {e}" for e in filtered_errors) or "- None"
    caps_text   = "\n".join(f"- {c[:100]}" for c in insights["new_capabilities"]) or "- None"
    prefs_text  = "\n".join(f"- {p}" for p in insights["preferences"]) or "- None"

    section = (
        f"\n## [{ts}] Evolution Summary (last 7d, {total} events)\n\n"
        f"### Top Tags\n- {tag_line}\n\n"
        f"### User Corrections\n{corrections_text}\n\n"
        f"### Frequent Errors (>=2, pending)\n{errors_text}\n\n"
        f"### New Capabilities\n{caps_text}\n\n"
        f"### Preferences\n{prefs_text}\n"
    )
    new_content = re.sub(
        r"## \[\d{4}-\d{2}-\d{2}.*?(?=## \[|\Z)",
        section,
        content,
        flags=re.DOTALL,
    )
    if new_content == content:
        new_content = content + section
    MEM.write_text(new_content)
    print(f"[evolve] recent.md updated ({total} events, logs: {LOGS})")


def update_errors_md(insights: dict):
    errors_to_process = _filter_promoted(insights["frequent_errors"])
    if not errors_to_process:
        return
    if not ERRS.exists():
        ERRS.write_text("# Error Log\n\n")
    content = ERRS.read_text()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for err_content in errors_to_process:
        if err_content in content:
            content = re.sub(
                r"(- \*\*出现次数\*\*：)(\d+)",
                lambda m: f"{m.group(1)}{int(m.group(2)) + 1}",
                content,
                count=1,
            )
            content = content.replace("monitoring", "pending")
        else:
            content += (
                f"\n## [{ts}] {err_content[:60]}\n"
                f"- **触发场景**：自动检测（events.jsonl）\n"
                f"- **错误行为**：{err_content}\n"
                f"- **正确处理**：待人工补充\n"
                f"- **tag**：[auto-detected]\n"
                f"- **出现次数**：2\n"
                f"- **状态**：pending\n"
            )
    ERRS.write_text(content)
    print(f"[evolve] errors.md updated: {len(errors_to_process)} items")


def archive_if_needed():
    if not MEM.exists():
        return
    lines = MEM.read_text().splitlines()
    if len(lines) > 300:
        archive_path = BASE / f"memory/archive/{datetime.now(timezone.utc).strftime('%Y-%m')}.md"
        archive_path.write_text("\n".join(lines))
        MEM.write_text("\n".join(lines[-50:]))
        print(f"[evolve] archived to {archive_path}")


if __name__ == "__main__":
    print(f"[evolve] v3.4 | logs: {LOGS}")
    if len(sys.argv) >= 2 and sys.argv[1] == "search":
        if len(sys.argv) < 3:
            print("Usage: python3 evolve.py search <keyword> [top_n]")
            sys.exit(1)
        keyword = sys.argv[2]
        top_n   = int(sys.argv[3]) if len(sys.argv) >= 4 else 5
        results = search_memory(keyword, top_n)
        if not results:
            print(f"No results for: {keyword}")
        else:
            print(f"Top {len(results)} results for '{keyword}':\n")
            for r in results:
                tags = ", ".join(get_event_tags(r))
                print(f"[{r.get('ts','')}] [{r.get('type','')}] count={r.get('count',1)}")
                print(f"  tags: {tags}")
                print(f"  {r.get('content','')}\n")
    else:
        events   = load_recent_events(7)
        insights = extract_insights(events)
        update_memory(insights)
        update_errors_md(insights)
        archive_if_needed()
        filtered = _filter_promoted(insights["frequent_errors"])
        if filtered:
            print(f"[evolve] Pending promotion: {filtered}")
        skipped = len(insights["frequent_errors"]) - len(filtered)
        if skipped > 0:
            print(f"[evolve] Skipped {skipped} already-promoted error(s)")
        if insights["new_capabilities"]:
            print(f"[evolve] New capabilities: {len(insights['new_capabilities'])}")
