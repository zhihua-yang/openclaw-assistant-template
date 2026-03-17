#!/usr/bin/env python3
"""
create_event.py v1.0
标准化事件写入工具：
- type 合法性验证（14个标准类型）
- tags 自动生成（字段名统一用 tags，强制非空）
- 内容字数验证（中英文混合）
- ts UTC 标准化
用法：
  python3 create_event.py --type learning-achievement --content "内容..."
  python3 create_event.py --list-types
  python3 create_event.py --check-type task-done
"""

import json, sys, argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

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

TAG_RULES = {
    "learning-achievement":  ["learning"],
    "user-correction":       ["user-interaction", "feedback"],
    "task-done":             ["task-completion", "progress"],
    "error-found":           ["error-detection", "monitoring"],
    "system-improvement":    ["improvement", "optimization"],
    "automation-deployment": ["automation", "deployment"],
    "error-fix":             ["error-resolution", "fixing"],
    "quality-verification":  ["quality-check", "verification"],
    "pua-inspection":        ["pua-mode", "deep-inspection"],
    "quality-improvement":   ["quality", "improvement"],
    "system-monitoring":     ["monitoring", "check"],
}

KEYWORD_TAGS = {
    "monitoring": ["monitor", "check", "verify", "inspect"],
    "automation": ["auto", "script", "cron", "schedule"],
    "quality":    ["quality", "fix", "improve", "enhance"],
    "error":      ["error", "bug", "issue", "problem"],
    "learning":   ["learn", "study", "understand", "master"],
    "system":     ["system", "architecture", "design", "structure"],
    "data":       ["data", "log", "record", "event"],
}


def _units(s: str) -> float:
    return len(s.strip()) / 15 if any('\u4e00' <= c <= '\u9fff' for c in s) \
           else len(s.strip().split())


def gen_tags(etype: str, content: str, user_tags: Optional[List[str]] = None) -> list:
    tags = list(TAG_RULES.get(etype, []))
    if user_tags:
        tags.extend(user_tags)
    cl = content.lower()
    for tag, kws in KEYWORD_TAGS.items():
        if tag not in tags and any(k in cl for k in kws):
            tags.append(tag)
    seen, unique = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique or [etype.replace("-", "_")]


def create_event(etype, content, tags=None, count=1, extra=None):
    if etype not in STANDARD_TYPES:
        print(f"ERR: type '{etype}' not in STANDARD_TYPES")
        print(f"     available: {', '.join(STANDARD_TYPES)}")
        return None
    u = _units(content)
    min_u = MIN_CONTENT.get(etype, MIN_CONTENT["default"])
    if u < min_u:
        print(f"ERR: content too short ({u:.1f}/{min_u} units for {etype})")
        return None
    ev = {
        "ts":      datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "type":    etype,
        "content": content.strip(),
        "tags":    gen_tags(etype, content, tags),
        "count":   count,
    }
    if extra:
        ev["extra"] = extra
    print(f"OK  type={etype}  units={u:.1f}/{min_u}  tags={ev['tags'][:3]}")
    return ev


def write_event(ev, outfile=None):
    if outfile:
        fp = Path(outfile)
    else:
        root = Path(__file__).parent.parent
        fp = next(
            (c for c in [
                root / ".sys/logs/events.jsonl",
                root / ".openclaw/logs/events.jsonl",
            ] if c.exists()),
            root / ".sys/logs/events.jsonl",
        )
    fp.parent.mkdir(parents=True, exist_ok=True)
    with open(fp, "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print(f"written: {fp}")


def main():
    p = argparse.ArgumentParser(description="create_event.py v1.0")
    p.add_argument("--type")
    p.add_argument("--content", nargs="+")
    p.add_argument("--tags",  help="逗号分隔")
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--extra", help="key:value,key:value")
    p.add_argument("--file",  help="输出文件路径")
    p.add_argument("--list-types",  action="store_true")
    p.add_argument("--check-type")
    a = p.parse_args()

    if a.list_types:
        for t in STANDARD_TYPES:
            print(f"  {t}  (min {MIN_CONTENT.get(t, MIN_CONTENT['default'])} units)")
        return 0
    if a.check_type:
        ok = a.check_type in STANDARD_TYPES
        print(f"{'OK' if ok else 'ERR'}: '{a.check_type}'")
        return 0
    if not a.type or not a.content:
        p.print_help()
        return 1

    tags  = [t.strip() for t in a.tags.split(",")] if a.tags else None
    extra = {}
    if a.extra:
        for kv in a.extra.split(","):
            k, _, v = kv.partition(":")
            if k:
                extra[k.strip()] = v.strip()
    ev = create_event(a.type, " ".join(a.content), tags, a.count, extra or None)
    if ev:
        write_event(ev, a.file)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
