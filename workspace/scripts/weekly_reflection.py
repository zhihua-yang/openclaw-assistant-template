#!/usr/bin/env python3
"""
weekly_reflection.py — 每周一 09:00 执行
周报生成 + decay penalty 触发 + 训练计划生成
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import safe_read_json, safe_write_json, safe_read_jsonl, safe_append_jsonl
from utils.paths import (
    EVOLUTION_CHAIN, INTELLIGENCE_INDEX, CAPABILITIES_JSON,
    PROFILE_JSON, GOALS_JSON, WEEKLY_SUMMARY, TRAINING_PLAN, CALIBRATION
)
from utils.sample_check import is_sample_sufficient

CST = timezone(timedelta(hours=8))


def load_profile() -> dict:
    if os.path.exists(PROFILE_JSON):
        return safe_read_json(PROFILE_JSON)
    return {}


def get_current_week() -> str:
    today = date.today()
    iso = today.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def compute_weekly_stats(chain: list) -> dict:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    last_week_start = week_start - timedelta(weeks=1)
    last_week_end   = week_start - timedelta(days=1)

    stats = {
        "total_tasks": 0,
        "routine": 0, "stretch": 0, "novel": 0,
        "near_transfer": 0, "far_transfer": 0,
        "error_driven_learning": 0,
        "challenge_driven_learning": 0,
        "intentional_challenges": 0,
        "index_delta": {"IQ": 0.0, "EQ": 0.0, "FQ": 0.0},
        "high_conf_total": 0, "high_conf_fail": 0,
        "low_conf_total": 0, "low_conf_success": 0,
    }

    for record in chain:
        ts = record.get("ts", "")[:10]
        try:
            d = date.fromisoformat(ts)
        except Exception:
            continue
        if not (last_week_start <= d <= last_week_end):
            continue

        etype = record.get("event_type", "")

        if etype == "task-done":
            stats["total_tasks"] += 1
            diff = record.get("task_difficulty", "routine")
            stats[diff] = stats.get(diff, 0) + 1

        if etype == "capability-reuse":
            t = record.get("transfer_type", "near")
            if t == "far":
                stats["far_transfer"] += 1
            else:
                stats["near_transfer"] += 1

        if etype == "learning-achievement":
            trigger = record.get("learning_trigger", "normal")
            if trigger == "error-driven":
                stats["error_driven_learning"] += 1
            elif trigger == "challenge-driven":
                stats["challenge_driven_learning"] += 1

        if etype == "intentional-challenge":
            stats["intentional_challenges"] += 1

        if record.get("scoring_decision"):
            delta = record["scoring_decision"].get("actual_delta", {})
            for dim in ["IQ", "EQ", "FQ"]:
                stats["index_delta"][dim] = round(
                    stats["index_delta"][dim] + delta.get(dim, 0.0), 4
                )

        conf = record.get("pre_task_confidence")
        if conf == "high":
            stats["high_conf_total"] += 1
            if etype in ("task-rework", "user-correction"):
                stats["high_conf_fail"] += 1
        elif conf == "low":
            stats["low_conf_total"] += 1
            if etype == "task-done":
                stats["low_conf_success"] += 1

    total = stats["total_tasks"]
    stats["routine_ratio"]  = round(stats["routine"] / total, 3) if total else 0
    stats["stretch_ratio"]  = round(stats["stretch"] / total, 3) if total else 0
    stats["novel_ratio"]    = round(stats["novel"]   / total, 3) if total else 0
    stats["overconfidence_rate"]  = round(stats["high_conf_fail"] / stats["high_conf_total"], 3) if stats["high_conf_total"] else 0
    stats["underconfidence_rate"] = round(stats["low_conf_success"] / stats["low_conf_total"], 3) if stats["low_conf_total"] else 0
    return stats


def detect_stage(chain: list, weeks: int = 3, threshold: float = 0.3) -> tuple:
    weekly_net = defaultdict(float)
    for record in chain:
        if not record.get("scoring_decision"):
            continue
        ts = record.get("ts", "")[:10]
        try:
            d = date.fromisoformat(ts)
        except Exception:
            continue
        iso = d.isocalendar()
        week_key = f"{iso[0]}-W{iso[1]:02d}"
        delta = record["scoring_decision"].get("actual_delta", {})
        weekly_net[week_key] += sum(delta.values())

    sorted_weeks = sorted(weekly_net.keys())[-weeks:]
    if len(sorted_weeks) < weeks:
        return "insufficient_data", ""

    recent_nets = [weekly_net[w] for w in sorted_weeks]
    avg_8w = sum(list(weekly_net.values())[-8:]) / max(len(list(weekly_net.values())[-8:]), 1)

    if all(n < threshold for n in recent_nets):
        return "plateau-observed", f"连续{weeks}周净增长偏低（均低于{threshold}）"
    if recent_nets[-1] > avg_8w * 2:
        return "breakthrough-observed", f"本周净增长（{recent_nets[-1]:.2f}）超过8周均值2倍"
    return "steady", "正常进化节奏"


def update_calibration(stats: dict, profile: dict):
    period = datetime.now(CST).strftime("%Y-%m")
    if os.path.exists(CALIBRATION):
        cal = safe_read_json(CALIBRATION)
        if cal.get("period") != period:
            cal = {"period": period, "high_confidence_success": 0,
                   "high_confidence_fail": 0, "low_confidence_success": 0, "low_confidence_fail": 0}
    else:
        cal = {"period": period, "high_confidence_success": 0,
               "high_confidence_fail": 0, "low_confidence_success": 0, "low_confidence_fail": 0}

    cal["high_confidence_fail"]    += stats.get("high_conf_fail", 0)
    cal["high_confidence_success"] += stats.get("high_conf_total", 0) - stats.get("high_conf_fail", 0)
    cal["low_confidence_success"]  += stats.get("low_conf_success", 0)

    hc_total = cal["high_confidence_success"] + cal["high_confidence_fail"]
    lc_total = cal["low_confidence_success"] + cal.get("low_confidence_fail", 0)

    cal["overconfidence_rate"]  = round(cal["high_confidence_fail"] / hc_total, 3) if hc_total else 0
    cal["underconfidence_rate"] = round(cal["low_confidence_success"] / lc_total, 3) if lc_total else 0

    threshold_oc = profile.get("overconfidence_alert_threshold", 0.15)
    if cal["overconfidence_rate"] > threshold_oc:
        cal["calibration_summary"] = f"⚠️ 过度自信率 {cal['overconfidence_rate']:.1%}，高于阈值 {threshold_oc:.1%}，建议注意。"
    else:
        cal["calibration_summary"] = f"✅ 校准良好，过度自信率 {cal['overconfidence_rate']:.1%}。"

    safe_write_json(CALIBRATION, cal)
    return cal


def check_decay_penalties(chain: list, capabilities: list) -> list:
    """检查是否需要生成 capability-decay-penalty"""
    from collections import defaultdict
    penalty_events = []
    today = date.today()

    for cap in capabilities:
        cap_id = cap.get("capability_id")
        status = cap.get("status", "")
        if status not in ("standard_verified", "strong_verified", "declared"):
            continue

        last_used = cap.get("last_used", "")
        if not last_used:
            continue
        try:
            last_date = date.fromisoformat(last_used)
        except Exception:
            continue

        idle_days = (today - last_date).days

        # 检查是否有连续 7 天以上未打破的 forgetting-risk 或 stagnation
        unresolved_diag_days = 0
        for record in chain:
            if record.get("event_type") not in ("forgetting-risk", "stagnation-warning"):
                continue
            if cap_id not in record.get("capability_ids", [cap_id]):
                continue
            ts = record.get("ts", "")[:10]
            try:
                d = date.fromisoformat(ts)
                days_ago = (today - d).days
                if days_ago <= 30 and record.get("status") == "pending":
                    unresolved_diag_days = max(unresolved_diag_days, days_ago)
            except Exception:
                pass

        if idle_days >= 60 or unresolved_diag_days >= 7:
            import uuid as _uuid
            now_ts = datetime.now(CST)
            penalty_events.append({
                "event_id": f"evt-{now_ts.strftime('%Y%m%d')}-{_uuid.uuid4().hex[:6]}",
                "ts": now_ts.isoformat(),
                "source_type": "derived",
                "event_type": "capability-decay-penalty",
                "title": f"能力衰减惩罚：{cap.get('display_name', cap_id)}",
                "content": f"能力 {cap_id} 已 {idle_days} 天未复用，触发周期性衰减。",
                "task_type": "system",
                "capability_ids": [cap_id],
                "evidence_level": "logical",
                "is_primary_scoring_event": False,
                "created_by": "weekly_reflection.py",
                "processed": False
            })

    return penalty_events


def generate_training_plan(stats: dict, stage: str, goals: dict, capabilities: list) -> dict:
    tasks = []

    if stats.get("routine_ratio", 0) > 0.6:
        tasks.append({
            "priority": 1,
            "action": "安排至少 2 个 stretch 难度任务",
            "reason": f"routine 占比 {stats['routine_ratio']:.0%}，偏高"
        })

    cap_needing_far = [
        cap for cap in capabilities
        if cap.get("status") == "standard_verified"
        and cap.get("far_transfer_count", 0) == 0
    ]
    if cap_needing_far:
        cap = cap_needing_far[0]
        tasks.append({
            "priority": 2,
            "action": f"为 [{cap['capability_id']}] {cap.get('display_name','')} 设计 1 次 far transfer",
            "target_capability": cap["capability_id"],
            "reason": "缺 far transfer，无法升入 strong_verified"
        })

    if stats.get("error_driven_learning", 0) == 0:
        tasks.append({
            "priority": 3,
            "action": "遇到 error-fix 时，补写 1 条 error-driven learning-achievement",
            "reason": "上周 error-driven 学习为零"
        })

    if stats.get("high_conf_total", 0) < 3:
        tasks.append({
            "priority": 4,
            "action": "重要任务记录 pre_task_confidence",
            "reason": "校准样本不足"
        })

    avoid = [
        "连续 3 天只做 routine 类型任务",
        "evidence_level 填 logical 但无系统推断依据"
    ]

    return {
        "week": get_current_week(),
        "generated_by": "rules",
        "stage": stage,
        "tasks": tasks,
        "avoid": avoid
    }


def render_weekly_report(summary: dict, cal: dict) -> str:
    index = summary.get("index_after", {})
    delta = summary.get("index_delta", {})

    def fmt_delta(v):
        return f"+{v:.2f} ↑" if v > 0 else f"{v:.2f} ↓" if v < 0 else "0.00 →"

    lines = [
        "# OpenClaw 周报",
        f"\n> 周次：{summary.get('week')} | 生成时间：{datetime.now(CST).strftime('%Y-%m-%d %H:%M')}",
        "\n## 📊 本周指数",
        "| 指数 | 本周变化 |",
        "|---|---|",
    ]
    for dim in ["IQ", "EQ", "FQ"]:
        lines.append(f"| {dim} | {fmt_delta(delta.get(dim, 0))} |")

    lines += [
        "\n## 🧭 学习区分布（本周）",
        f"- routine：{summary.get('routine_ratio', 0):.0%} | stretch：{summary.get('stretch_ratio', 0):.0%} | novel：{summary.get('novel_ratio', 0):.0%}",
        "\n## 🔁 能力迁移",
        f"- near transfer：{summary.get('near_transfer_count', 0)} | far transfer：{summary.get('far_transfer_count', 0)}",
        "\n## 🧠 错误/挑战驱动学习",
        f"- error-driven：{summary.get('error_driven_learning_count', 0)} | challenge-driven：{summary.get('challenge_driven_learning_count', 0)}",
        "\n## 🎯 元认知校准",
        f"- {cal.get('calibration_summary', '无数据')}",
    ]

    if not summary.get("sample_sufficient"):
        count = summary.get("sample_count", 0)
        lines += [
            "\n## 📈 成长阶段",
            f"- 数据积累中（当前 {count} 个有效任务，目标 ≥ 15）",
            "- plateau / breakthrough 判断将在样本充足后启用"
        ]
    else:
        stage = summary.get("stage", "steady")
        reason = summary.get("stage_reason", "")
        lines += [
            "\n## 📈 成长阶段",
            f"- 当前：{stage}",
            f"- 原因：{reason}"
        ]

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="OpenClaw 周反思")
    parser.add_argument("--dry-run", action="store_true", help="只打印不写入")
    args = parser.parse_args()

    print(f"[weekly] 开始执行 — {datetime.now(CST).isoformat()}")

    profile      = load_profile()
    chain        = safe_read_jsonl(EVOLUTION_CHAIN)
    capabilities = safe_read_json(CAPABILITIES_JSON).get("capabilities", []) if os.path.exists(CAPABILITIES_JSON) else []
    goals        = safe_read_json(GOALS_JSON) if os.path.exists(GOALS_JSON) else {}
    index        = safe_read_json(INTELLIGENCE_INDEX) if os.path.exists(INTELLIGENCE_INDEX) else {}

    min_tasks = profile.get("sample_sufficient_min_task_done", 15)
    sufficient, count = is_sample_sufficient(EVOLUTION_CHAIN, min_tasks)

    stats = compute_weekly_stats(chain)
    stage, stage_reason = detect_stage(chain)
    cal   = update_calibration(stats, profile)

    summary = {
        "week": get_current_week(),
        "delta": stats["index_delta"],
        "routine_ratio":  stats["routine_ratio"],
        "stretch_ratio":  stats["stretch_ratio"],
        "novel_ratio":    stats["novel_ratio"],
        "near_transfer_count":  stats["near_transfer"],
        "far_transfer_count":   stats["far_transfer"],
        "error_driven_learning_count":   stats["error_driven_learning"],
        "challenge_driven_learning_count": stats["challenge_driven_learning"],
        "intentional_challenge_count": stats["intentional_challenges"],
        "overconfidence_rate":  stats["overconfidence_rate"],
        "underconfidence_rate": stats["underconfidence_rate"],
        "stage":         stage,
        "stage_reason":  stage_reason,
        "sample_sufficient": sufficient,
        "sample_count":  count,
        "top_issue":     "routine 偏高" if stats["routine_ratio"] > 0.6 else "正常"
    }

    # decay penalty
    penalty_events = check_decay_penalties(chain, capabilities)

    training_plan = generate_training_plan(stats, stage, goals, capabilities)
    report        = render_weekly_report(summary, cal)

    if args.dry_run:
        print("\n=== 周报预览 ===")
        print(report)
        print("\n=== 训练计划 ===")
        print(json.dumps(training_plan, ensure_ascii=False, indent=2))
        print(f"\n=== Decay Penalty 待写入：{len(penalty_events)} 条 ===")
        return

    safe_write_json(WEEKLY_SUMMARY, summary)
    safe_write_json(TRAINING_PLAN, training_plan)

    for pe in penalty_events:
        safe_append_jsonl(EVOLUTION_CHAIN, pe)
        print(f"[weekly] 写入 decay-penalty：{pe['event_id']} ({pe['capability_ids']})")

    print(report)
    print(f"\n[weekly] 完成。样本充足：{sufficient}（{count}/{min_tasks}）")


if __name__ == "__main__":
    main()
