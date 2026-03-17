#!/usr/bin/env python3
"""
session_note_writer.py v1.0
/session-notes 的真正实现。
AI 在会话结束时通过 exec: 调用本脚本，完成：
  1. 写会话摘要到 .sys/sessions/YYYY-MM-DD.md（双路径兼容）
  2. 追加结构化事件到 events.jsonl（强制规范）
  3. 检查并更新 memory/errors.md
  4. 触发 /remember（更新 memory/recent.md）

用法：
  python3 session_note_writer.py \
    --summary   "本次会话摘要..." \
    --type      task-done \
    --content   "完成了什么..." \
    --tags      task-completion,progress \
    [--error    "发现的错误描述"]   \
    [--dry-run]
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

STANDARD_TYPES = [
    "task-done", "error-found", "system-improvement", "learning-achievement",
    "user-correction", "automation-deployment", "error-fix", "system-monitoring",
    "quality-verification", "new-capability", "automation-planning", "memory-compaction",
    "pua-inspection", "quality-improvement",
]

MIN_CONTENT = {
    "learning-achievement": 15,
    "user-correction":      10,
    "task-done":             8,
    "error-found":           8,
    "system-improvement":   10,
    "default":               5,
}

BASE = Path.home() / ".openclaw/workspace"
ERRS = BASE / "memory/errors.md"
MEM  = BASE / "memory/recent.md"


def _detect_runtime_dir(base: Path) -> Path:
    """自动探测运行时目录，兼容 .sys/ 和 .openclaw/ 两种路径。"""
    for candidate in [
        base / ".sys/logs/events.jsonl",
        base / ".openclaw/logs/events.jsonl",
    ]:
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate.parent
    # 默认用 .sys
    default = base / ".sys/logs"
    default.mkdir(parents=True, exist_ok=True)
    return default


def _detect_sessions_dir(base: Path) -> Path:
    """自动探测 sessions 目录，双路径均创建确保可写。"""
    dirs = [base / ".sys/sessions", base / ".openclaw/sessions"]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    # 优先用 .sys
    return dirs[0]


def _units(s: str) -> float:
    return len(s.strip()) / 15 if any('\u4e00' <= c <= '\u9fff' for c in s) \
           else len(s.strip().split())


def write_session_log(sessions_dir: Path, summary: str, dry_run: bool = False):
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ts_str   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    path     = sessions_dir / f"{date_str}.md"

    entry = f"\n## [{ts_str}]\n\n{summary.strip()}\n"

    if dry_run:
        print(f"[DRY-RUN] session log -> {path}")
        print(entry)
        return

    with open(path, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"[session_note_writer] session log written: {path}")


def write_event(logs_dir: Path, etype: str, content: str, tags: list,
                count: int = 1, dry_run: bool = False):
    if etype not in STANDARD_TYPES:
        print(f"ERR: type '{etype}' not in STANDARD_TYPES", file=sys.stderr)
        return False

    u     = _units(content)
    min_u = MIN_CONTENT.get(etype, MIN_CONTENT["default"])
    if u < min_u:
        print(f"ERR: content too short ({u:.1f}/{min_u} units for {etype})", file=sys.stderr)
        return False

    ev = {
        "ts":      datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "type":    etype,
        "content": content.strip(),
        "tags":    tags if tags else [etype.replace("-", "_")],
        "count":   count,
    }

    jsonl_path = logs_dir / "events.jsonl"

    if dry_run:
        print(f"[DRY-RUN] event -> {jsonl_path}")
        print(json.dumps(ev, ensure_ascii=False))
        return True

    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print(f"[session_note_writer] event written: type={etype} tags={tags[:2]}")
    return True


def update_errors_md(error_desc: str, dry_run: bool = False):
    if not error_desc:
        return

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not ERRS.exists():
        if not dry_run:
            ERRS.write_text("# Error Log\n\n")

    content = ERRS.read_text() if ERRS.exists() else "# Error Log\n\n"

    # 检查是否已有同类条目
    short = error_desc[:60]
    if short in content:
        # 出现次数 +1，若 >= 2 改为 pending
        new_content = re.sub(
            r"(- \*\*出现次数\*\*：)(\d+)",
            lambda m: f"{m.group(1)}{int(m.group(2)) + 1}",
            content, count=1,
        )
        new_content = new_content.replace("monitoring", "pending", 1)
        action = "updated"
    else:
        new_entry = (
            f"\n## [{ts}] {short}\n"
            f"- **触发场景**：会话自动记录\n"
            f"- **错误行为**：{error_desc}\n"
            f"- **正确处理**：待人工补充\n"
            f"- **tag**：[auto-detected]\n"
            f"- **出现次数**：1\n"
            f"- **状态**：monitoring\n"
        )
        new_content = content + new_entry
        action = "added"

    if dry_run:
        print(f"[DRY-RUN] errors.md {action}: {short}")
        return

    ERRS.write_text(new_content)
    print(f"[session_note_writer] errors.md {action}: {short}")


def trigger_remember(dry_run: bool = False):
    """
    /remember 的轻量实现：将最近事件摘要追加到 memory/recent.md。
    完整版由 evolve.py 每天执行；这里只做"今日新增"标记。
    """
    if not MEM.exists():
        print("[session_note_writer] memory/recent.md not found, skipped /remember")
        return

    ts    = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    marker = f"<!-- last-session-notes: {ts} -->"

    content = MEM.read_text()
    if marker in content:
        return  # 同一分钟内不重复写

    entry = f"\n{marker}\n_Last session-notes executed at {ts} UTC_\n"

    if dry_run:
        print(f"[DRY-RUN] /remember marker -> memory/recent.md")
        return

    with open(MEM, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"[session_note_writer] /remember marker written to recent.md")


def main():
    p = argparse.ArgumentParser(description="session_note_writer.py v1.0")
    p.add_argument("--summary",  required=True,  help="本次会话的自然语言摘要")
    p.add_argument("--type",     required=True,  help="事件类型（14个标准类型之一）")
    p.add_argument("--content",  required=True,  nargs="+", help="结构化事件内容描述")
    p.add_argument("--tags",     default="",     help="逗号分隔的 tags")
    p.add_argument("--error",    default="",     help="本次会话发现的错误（可选）")
    p.add_argument("--count",    type=int, default=1)
    p.add_argument("--dry-run",  action="store_true", help="只打印，不写文件")
    a = p.parse_args()

    logs_dir     = _detect_runtime_dir(BASE)
    sessions_dir = _detect_sessions_dir(BASE)
    tags         = [t.strip() for t in a.tags.split(",") if t.strip()]
    content      = " ".join(a.content)
    dry_run      = a.dry_run

    print(f"[session_note_writer] runtime logs: {logs_dir}")
    print(f"[session_note_writer] sessions dir: {sessions_dir}")

    # 步骤1：写会话日志（双路径）
    write_session_log(sessions_dir, a.summary, dry_run)
    # 同步写一份到 .openclaw/sessions（双路径兼容）
    alt_sessions = BASE / ".openclaw/sessions"
    if alt_sessions != sessions_dir:
        write_session_log(alt_sessions, a.summary, dry_run)

    # 步骤2：写结构化事件
    write_event(logs_dir, a.type, content, tags, a.count, dry_run)

    # 步骤3：更新 errors.md（有错误时）
    update_errors_md(a.error, dry_run)

    # 步骤4：触发 /remember
    trigger_remember(dry_run)

    print("[session_note_writer] /session-notes 完成")


if __name__ == "__main__":
    main()
