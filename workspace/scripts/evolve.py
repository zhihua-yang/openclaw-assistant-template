#!/usr/bin/env python3
"""
evolve.py v3.3
- 自动检测 OpenClaw 运行时目录（.sys/ 或 .openclaw/）
- 结构化 events.jsonl（含 tag/count 字段）
- 量化晋升：error count >= 2 -> errors.md pending
- 修复时区比较 bug：统一使用 UTC naive datetime
- CLI: python3 evolve.py search <keyword> [top_n]
"""

import json
import re
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta, timezone

BASE  = Path.home() / ".openclaw/workspace"
MEM   = BASE / "memory/recent.md"
ERRS  = BASE / "memory/errors.md"


def _detect_runtime_dir(base: Path) -> Path:
    """
    自动检测 OpenClaw 实际使用的运行时目录。
    优先使用已有数据的目录，fallback 到 .sys/（OpenClaw 默认）。
    """
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
    """统一转为 UTC naive datetime，避免 aware/naive 混合比较报错。"""
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
            ts = _to_naive_utc(datetime.fromisoformat(e["ts"]))
            if ts >= cutoff:
                events.append(e)
        except Exception:
            pass
    return events


def append_event(type_: str, content: str, tags: list, count: int = 1, extra: dict = None):
    """写入一条标准化事件到 events.jsonl，时间戳带 UTC 时区。"""
    record = {
        "ts":      datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "type":    type_,
        "tag":     tags,
        "content": content,
        "count":   count,
    }
    if extra:
        record.update(extra)
    with LOGS.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def search_memory(keyword: str, top_n: int = 5) -> list:
    """逐行扫描 events.jsonl，按 count 降序返回匹配结果。"""
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


def extract_insights(events: list) -> dict:
    corrections  = [e for e in events if e.get("type") == "user-correction"]
    errors       = [e for e in events if e.get("type") in ("repeated-error", "user-correction")]
    capabilities = [e for e in events if e.get("type") == "new-capability"]
    preferences  = [e for e in events if e.get("type") == "preference"]

    error_counts = Counter()
    for e in errors:
        key = e.get("content", "")[:80]
        error_counts[key] += e.get("count", 1)

    frequent_errors = [e for e, c in error_counts.items() if c >= 2]

    all_tags = []
    for e in events:
        all_tags.extend(e.get("tag", []))
    tag_summary = Counter(all_tags).most_common(5)

    return {
        "corrections":      corrections,
        "frequent_errors":  frequent_errors,
        "new_capabilities": [e.get("content", "") for e in capabilities],
        "preferences":      [e.get("content", "") for e in preferences],
        "total_events":     len(events),
        "tag_summary":      tag_summary,
    }


def update_memory(insights: dict):
    if not MEM.exists():
        print("[evolve] recent.md not found, skipped")
        return
    content  = MEM.read_text()
    ts       = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    total    = insights["total_events"]
    tag_line = ", ".join(f"{t}x{c}" for t, c in insights["tag_summary"]) or "-"

    corrections_text = "\n".join(
        f"- {c.get('old','?')} -> {c.get('new','?')}（{c.get('reason','')}）"
        for c in insights["corrections"]
    ) or "- 无"
    errors_text = "\n".join(f"- {e}" for e in insights["frequent_errors"]) or "- 无"
    caps_text   = "\n".join(f"- {c}" for c in insights["new_capabilities"]) or "- 无"
    prefs_text  = "\n".join(f"- {p}" for p in insights["preferences"]) or "- 无"

    section = (
        f"\n## [{ts}] 进化摘要（近7天 {total} 事件）\n\n"
        f"### 高频 Tag\n- {tag_line}\n\n"
        f"### 用户纠正\n{corrections_text}\n\n"
        f"### 高频错误（>=2次，待晋升）\n{errors_text}\n\n"
        f"### 新能力\n{caps_text}\n\n"
        f"### 用户偏好\n{prefs_text}\n"
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
    if not insights["frequent_errors"]:
        return
    if not ERRS.exists():
        ERRS.write_text("# Error Log\n\n")

    content = ERRS.read_text()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for err_content in insights["frequent_errors"]:
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
    print(f"[evolve] errors.md updated: {len(insights['frequent_errors'])} items")


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
    print(f"[evolve] using logs: {LOGS}")

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
                tags = ", ".join(r.get("tag", []))
                print(f"[{r.get('ts','')}] [{r.get('type','')}] count={r.get('count',1)}")
                print(f"  tags: {tags}")
                print(f"  {r.get('content','')}\n")
    else:
        events   = load_recent_events(7)
        insights = extract_insights(events)
        update_memory(insights)
        update_errors_md(insights)
        archive_if_needed()

        if insights["frequent_errors"]:
            print(f"[evolve] Pending promotion: {insights['frequent_errors']}")
        if insights["new_capabilities"]:
            print(f"[evolve] New capabilities: {insights['new_capabilities']}")
