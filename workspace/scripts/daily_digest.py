#!/usr/bin/env python3
"""
daily_digest.py — 每日摘要更新
更新 recent_digest.json，供上下文注入使用
"""
import os
import sys
from datetime import datetime, timezone, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import safe_read_json, safe_write_json, safe_read_jsonl
from utils.paths import (
    EVOLUTION_CHAIN, CAPABILITIES_JSON, ANTIPATTERNS_JSON,
    GOALS_JSON, INTELLIGENCE_INDEX, RECENT_DIGEST
)

CST = timezone(timedelta(hours=8))


def main():
    chain        = safe_read_jsonl(EVOLUTION_CHAIN)
    capabilities = safe_read_json(CAPABILITIES_JSON).get("capabilities", []) if os.path.exists(CAPABILITIES_JSON) else []
    antipatterns = safe_read_json(ANTIPATTERNS_JSON).get("antipatterns", []) if os.path.exists(ANTIPATTERNS_JSON) else []
    goals        = safe_read_json(GOALS_JSON) if os.path.exists(GOALS_JSON) else {}
    index        = safe_read_json(INTELLIGENCE_INDEX) if os.path.exists(INTELLIGENCE_INDEX) else {}

    today = date.today()
    window = 7

    recent_failures = 0
    recent_reworks  = 0
    recent_challenges = 0
    for e in chain:
        ts = e.get("ts", "")[:10]
        try:
            d = date.fromisoformat(ts)
        except Exception:
            continue
        if (today - d).days > window:
            continue
        etype = e.get("event_type", "")
        if etype in ("error-found", "user-correction"):
            recent_failures += 1
        elif etype == "task-rework":
            recent_reworks += 1
        elif etype == "intentional-challenge":
            recent_challenges += 1

    top_caps = sorted(
        [c for c in capabilities if c.get("status") in ("standard_verified", "strong_verified")],
        key=lambda c: c.get("last_used", ""),
        reverse=True
    )[:3]

    active_aps = sorted(
        antipatterns,
        key=lambda ap: ap.get("last_triggered", ""),
        reverse=True
    )[:3]

    result_goals = goals.get("result_goals", {})
    gap_parts = []
    for dim in ["IQ", "EQ", "FQ"]:
        current = index.get(dim, {}).get("score", 50.0)
        target  = result_goals.get(dim, {}).get("target_6m", 70.0)
        gap = round(target - current, 2)
        if gap > 0:
            gap_parts.append(f"{dim}差距{gap}")

    digest = {
        "updated_at": datetime.now(CST).isoformat(),
        "top_capabilities": [c["capability_id"] for c in top_caps],
        "active_antipatterns": [ap["antipattern_id"] for ap in active_aps],
        "recent_failures":   recent_failures,
        "recent_reworks":    recent_reworks,
        "recent_challenges": recent_challenges,
        "current_focus":     gap_parts[0].replace("差距", " 差距最大，需关注") if gap_parts else "均衡发展",
        "goal_gap_summary":  "，".join(gap_parts) if gap_parts else "已达目标",
        "index_snapshot":    {dim: index.get(dim, {}).get("score", 50.0) for dim in ["IQ", "EQ", "FQ"]}
    }

    safe_write_json(RECENT_DIGEST, digest)
    print(f"[digest] 更新完成：{RECENT_DIGEST}")
    print(f"  top_caps: {digest['top_capabilities']}")
    print(f"  gap: {digest['goal_gap_summary']}")


if __name__ == "__main__":
    main()
