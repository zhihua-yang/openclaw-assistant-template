#!/usr/bin/env python3
"""
audit_events.py — OpenClaw v3.11.1-Lite
每日自动诊断扫描，输出建议到 audit_queue.jsonl
只记录，永不直接改分
"""

import json
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
MEMORY   = BASE_DIR / "memory"
CHAIN    = MEMORY / "evolution_chain.jsonl"
QUEUE    = MEMORY / "audit_queue.jsonl"
PROFILE  = MEMORY / "profile.json"

TODAY    = datetime.now().strftime("%Y-%m-%d")
NOW_TS   = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def load_profile():
    if PROFILE.exists():
        return json.loads(PROFILE.read_text())
    return {}


def load_events(days=30):
    if not CHAIN.exists():
        return []
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    events = []
    for line in CHAIN.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
            if e.get("date", "") >= cutoff:
                events.append(e)
        except json.JSONDecodeError:
            continue
    return events


def load_queue():
    if not QUEUE.exists():
        return []
    items = []
    for line in QUEUE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return items


def save_queue(items):
    QUEUE.write_text("\n".join(json.dumps(i, ensure_ascii=False) for i in items) + "\n")


def already_diagnosed(queue, diag_type, target_date=None):
    """避免同类诊断重复写入"""
    for item in queue:
        if item.get("status") in ("pending", "adopted"):
            if item.get("diag_type") == diag_type:
                if target_date is None or item.get("target_date") == target_date:
                    return True
    return False


def make_diag(diag_type, summary, detail, suggestion):
    return {
        "id": f"diag-{TODAY}-{uuid.uuid4().hex[:6]}",
        "diag_type": diag_type,
        "date": TODAY,
        "created_at": NOW_TS,
        "status": "pending",
        "summary": summary,
        "detail": detail,
        "suggestion": suggestion,
    }


def run_diagnostics(events, queue, profile):
    new_diags = []

    # ── 1. stagnation-warning：连续 3 天无 learning-achievement ──
    learning_dates = {e["date"] for e in events if e.get("type") == "learning-achievement"}
    streak = 0
    for i in range(7):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        if day not in learning_dates:
            streak += 1
        else:
            break
    if streak >= 3 and not already_diagnosed(queue, "stagnation-warning"):
        new_diags.append(make_diag(
            "stagnation-warning",
            f"连续 {streak} 天无学习记录",
            f"最近 {streak} 天未检测到 learning-achievement 事件",
            "考虑补录学习收获，或安排一次 error-driven 复盘"
        ))

    # ── 2. repeat-error-alert：7 天内同类错误重复 ≥ 2 ──
    recent7 = [e for e in events if e.get("date", "") >= (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")]
    error_types: dict = {}
    for e in recent7:
        if e.get("type") in ("error-found", "error-fix", "user-correction"):
            tt = e.get("task_type", "unknown")
            error_types[tt] = error_types.get(tt, 0) + 1
    for tt, cnt in error_types.items():
        if cnt >= 2 and not already_diagnosed(queue, "repeat-error-alert", tt):
            new_diags.append(make_diag(
                "repeat-error-alert",
                f"7天内 {tt} 类型错误重复 {cnt} 次",
                f"task_type={tt} 在近7天出现 {cnt} 次错误相关事件",
                "建议复盘根因，录入 antipattern 防止复发"
            ) | {"target_date": tt})

    # ── 3. comfort-zone-warning：routine 占比 > 70%（近30天）──
    recent30_done = [e for e in events if e.get("type") == "task-done"]
    if len(recent30_done) >= 10:
        routine_cnt = sum(1 for e in recent30_done if e.get("difficulty", "routine") == "routine")
        ratio = routine_cnt / len(recent30_done)
        if ratio > 0.70 and not already_diagnosed(queue, "comfort-zone-warning"):
            new_diags.append(make_diag(
                "comfort-zone-warning",
                f"舒适区占比 {ratio:.0%}（近30天 task-done）",
                f"近30天 {len(recent30_done)} 条 task-done 中，routine 占 {routine_cnt} 条（{ratio:.0%}）",
                "建议安排 stretch 或 novel 难度任务，避免能力停滞"
            ))

    # ── 4. suspected-missing-learning：task-done 含学习关键词但无派生 ──
    LEARN_KEYWORDS = ["学到", "理解了", "发现", "原来", "搞懂", "根因", "排查", "复盘"]
    task_done_ids = {e.get("task_id") for e in events if e.get("type") == "task-done"}
    derived_parents = {e.get("parent_id") for e in events if e.get("parent_id")}
    for e in events:
        if e.get("type") != "task-done":
            continue
        content = e.get("content", "")
        if any(kw in content for kw in LEARN_KEYWORDS):
            tid = e.get("task_id") or e.get("id")
            if tid not in derived_parents:
                diag_key = f"suspected-missing-learning-{tid}"
                if not already_diagnosed(queue, "suspected-missing-learning", diag_key):
                    new_diags.append(make_diag(
                        "suspected-missing-learning",
                        f"任务含学习关键词但无派生事件：{content[:40]}",
                        f"事件 {tid} 内容含学习关键词，但未找到对应 learning-achievement",
                        "考虑补录 learning-achievement，记录认知更新"
                    ) | {"target_date": diag_key})

    # ── 5. overconfidence-warning：高置信失败率 > 15% ──
    high_conf = [e for e in events if e.get("confidence") == "high" and e.get("type") == "task-done"]
    if len(high_conf) >= 5:
        fails = [e for e in high_conf if e.get("outcome") == "fail"]
        fail_rate = len(fails) / len(high_conf)
        threshold = profile.get("overconfidence_alert_threshold", 0.15)
        if fail_rate > threshold and not already_diagnosed(queue, "overconfidence-warning"):
            new_diags.append(make_diag(
                "overconfidence-warning",
                f"高置信失败率 {fail_rate:.0%}（阈值 {threshold:.0%}）",
                f"近30天 {len(high_conf)} 条高置信任务中，{len(fails)} 条结果为 fail",
                "注意元认知校准，适当降低预判置信度"
            ))

    # ── 6. underconfidence-warning：低置信成功率 > 25% ──
    low_conf = [e for e in events if e.get("confidence") == "low" and e.get("type") == "task-done"]
    if len(low_conf) >= 5:
        successes = [e for e in low_conf if e.get("outcome") == "success"]
        succ_rate = len(successes) / len(low_conf)
        if succ_rate > 0.25 and not already_diagnosed(queue, "underconfidence-warning"):
            new_diags.append(make_diag(
                "underconfidence-warning",
                f"低置信成功率 {succ_rate:.0%}",
                f"近30天 {len(low_conf)} 条低置信任务中，{len(successes)} 条结果为 success",
                "实际表现优于预期，建议提升自我评估准确度"
            ))

    # ── 7. plateau-detected：连续 3 周净增长 < 0.3 ──
    iq_events = [e for e in events if e.get("iq_delta") is not None]
    if len(iq_events) >= 9:
        weekly_deltas = []
        for w in range(3):
            start = (datetime.now() - timedelta(days=(w + 1) * 7)).strftime("%Y-%m-%d")
            end   = (datetime.now() - timedelta(days=w * 7)).strftime("%Y-%m-%d")
            week_events = [e for e in iq_events if start <= e.get("date", "") < end]
            weekly_deltas.append(sum(e.get("iq_delta", 0) for e in week_events))
        if all(d < 0.3 for d in weekly_deltas) and not already_diagnosed(queue, "plateau-detected"):
            new_diags.append(make_diag(
                "plateau-detected",
                f"连续3周 IQ 净增长均 < 0.3（{[round(d,2) for d in weekly_deltas]}）",
                f"近3周每周 IQ delta：{weekly_deltas}，均低于 0.3",
                "建议增加 intentional-challenge 或 error-driven 学习事件打破平台期"
            ))

    return new_diags


def main():
    print(f"[audit_events] {NOW_TS} 开始扫描")

    profile = load_profile()
    events  = load_events(days=30)
    queue   = load_queue()

    print(f"  已加载事件：{len(events)} 条（近30天）")
    print(f"  审计队列：{len(queue)} 条")

    new_diags = run_diagnostics(events, queue, profile)

    if new_diags:
        queue.extend(new_diags)
        save_queue(queue)
        print(f"  新增诊断建议：{len(new_diags)} 条")
        for d in new_diags:
            print(f"    [{d['diag_type']}] {d['summary']}")
    else:
        print("  无新诊断建议")

    # 自动过期超期 pending 建议
    expire_days = profile.get("audit_expire_days", 7)
    cutoff = (datetime.now() - timedelta(days=expire_days)).strftime("%Y-%m-%d")
    expired = 0
    for item in queue:
        if item.get("status") == "pending" and item.get("date", "") < cutoff:
            item["status"] = "expired"
            expired += 1
    if expired:
        save_queue(queue)
        print(f"  已过期建议：{expired} 条")

    print(f"[audit_events] 扫描完成")


if __name__ == "__main__":
    main()
