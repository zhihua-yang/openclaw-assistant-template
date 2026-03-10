#!/usr/bin/env python3
import json, os, re, shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

BASE   = Path(os.environ.get("WORKSPACE", str(Path.home() / ".openclaw/workspace")))
LOGS   = BASE / ".openclaw/logs/events.jsonl"
MEMORY = BASE / "memory/recent.md"
STATE  = BASE / ".openclaw/logs/last_evolution_line.txt"
REQUIRED = {"ts", "type", "uuid", "session_id"}

for d in [LOGS.parent, BASE/".openclaw/sessions", BASE/".openclaw/baseline",
          BASE/".openclaw/compact", BASE/"memory/archive"]:
    d.mkdir(parents=True, exist_ok=True)
if not LOGS.exists():  LOGS.touch()
if not STATE.exists(): STATE.write_text("0", encoding="utf-8")


def validate(raw, lineno):
    try:
        e = json.loads(raw)
    except json.JSONDecodeError as ex:
        return None, f"行 {lineno}: JSON 错误 — {ex}"
    miss = REQUIRED - e.keys()
    if miss:
        return None, f"行 {lineno}: 缺字段 {miss}"
    try:
        datetime.fromisoformat(e["ts"])
    except ValueError:
        return None, f"行 {lineno}: ts 非法 — {e['ts']}"
    return e, None


def load_new_events():
    last = int(STATE.read_text(encoding="utf-8").strip() or "0")
    all_lines = LOGS.read_text(encoding="utf-8").splitlines()
    events, bad, seen = [], [], set()
    for i, raw in enumerate(all_lines[last:]):
        raw = raw.strip()
        if not raw:
            continue
        e, err = validate(raw, last + i + 1)
        if err:
            bad.append(err)
            continue
        key = e.get("uuid") or f"{e['ts']}-{e['type']}-{e.get('error','')}"
        if key in seen:
            continue
        seen.add(key)
        events.append(e)
    if bad:
        print(f"WARNING: 跳过 {len(bad)} 条非法行")
        [print("  " + b) for b in bad]
    return events, len(all_lines)


def get_insights(events):
    corrections = [e for e in events if e.get("type") == "user_correction"]
    errors      = [e for e in events if e.get("type") == "repeated_error"]
    caps        = [e for e in events if e.get("type") == "new_capability"]
    cnt  = Counter(e.get("error", "") for e in errors)
    freq = [k for k, v in cnt.items() if v >= 3 and k]
    return {
        "corrections":     corrections,
        "frequent_errors": freq,
        "new_caps":        [e.get("description", "") for e in caps],
        "total":           len(events),
        "has_cluster":     bool(freq or corrections),
    }


def mem_section(ins):
    lines = [
        "## 历史学习",
        f"最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"自上次进化新增事件数：{ins['total']}",
        "", "### 用户纠正行为",
    ]
    lines += [
        f"- 不要 {c.get('old','?')}，应该 {c.get('new','?')}（原因：{c.get('reason','无')}）"
        for c in ins["corrections"]
    ] or ["- 无"]
    lines += ["", "### 高频错误（已触发规则更新）"]
    lines += [f"- {e}" for e in ins["frequent_errors"]] or ["- 无"]
    lines += ["", "### 新掌握的能力/工具"]
    lines += [f"- {c}" for c in ins["new_caps"]] or ["- 无"]
    lines.append("")
    return "\n".join(lines)


def backup(p):
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = p.with_suffix(f".bak.{ts}")
    shutil.copy2(p, dst)
    print(f"Backup: {dst}")


def update_memory(ins):
    if not MEMORY.exists():
        print(f"WARNING: {MEMORY} 不存在")
        return
    try:
        backup(MEMORY)
        txt = MEMORY.read_text(encoding="utf-8")
        if "## 历史学习" not in txt:
            txt += "\n## 历史学习\n"
        txt = re.sub(
            r"## 历史学习.*?(?=\n## |\Z)",
            mem_section(ins), txt, flags=re.DOTALL
        )
        MEMORY.write_text(txt, encoding="utf-8")
        print(f"OK: 更新了 {ins['total']} 条事件的学习记录")
    except (OSError, re.error) as ex:
        print(f"ERROR: {ex}")


def archive():
    if not MEMORY.exists():
        return
    try:
        lines = MEMORY.read_text(encoding="utf-8").splitlines()
        if len(lines) > 300:
            ap = BASE / f"memory/archive/{datetime.now().strftime('%Y-%m')}.md"
            ap.write_text("\n".join(lines), encoding="utf-8")
            MEMORY.write_text("\n".join(lines[-50:]), encoding="utf-8")
            print(f"ARCHIVE: {ap}")
    except OSError as ex:
        print(f"ERROR: 归档失败 {ex}")


if __name__ == "__main__":
    print("evolve.py start", datetime.now().isoformat())
    events, total_lines = load_new_events()
    ins = get_insights(events)

    if ins["total"] < 5:
        print(f"SKIP: 仅 {ins['total']} 条新事件，不足 5 条")
        raise SystemExit(0)

    if not ins["has_cluster"]:
        print("INFO: 无有效聚类，仅更新记忆")
        update_memory(ins)
        archive()
        STATE.write_text(str(total_lines), encoding="utf-8")
        raise SystemExit(0)

    update_memory(ins)
    archive()
    STATE.write_text(str(total_lines), encoding="utf-8")

    if ins["frequent_errors"]:
        print("LEVEL2: 高频错误:", ins["frequent_errors"])
        print("  → 在 OpenClaw 执行 /memory-evolution 审批 diff")
    if ins["new_caps"]:
        print("NEW_CAP:", ins["new_caps"])
    print("evolve.py done")
