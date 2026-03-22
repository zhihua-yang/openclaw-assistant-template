#!/usr/bin/env python3
"""
evolve.py — 计分引擎
每日 00:20 由 Cron 触发，处理 evolution_chain 中未处理的事件
"""
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import safe_read_json, safe_write_json, safe_read_jsonl, safe_append_jsonl
from utils.paths import (
    EVOLUTION_CHAIN, INTELLIGENCE_INDEX, CAPABILITIES_JSON,
    AUDIT_QUEUE, PROFILE_JSON, RECENT_DIGEST
)

CST = timezone(timedelta(hours=8))

EVIDENCE_COEFFICIENTS = {"external": 1.0, "logical": 0.7, "self": 0.2}

BASE_DELTAS = {
    "task-done-new":                    {"IQ": 0.2,  "EQ": 0.0,  "FQ": 0.2},
    "task-done-routine":                {"IQ": 0.0,  "EQ": 0.0,  "FQ": 0.1},
    "error-fix":                        {"IQ": 0.3,  "EQ": 0.0,  "FQ": 0.0},
    "system-improvement":               {"IQ": 0.1,  "EQ": 0.0,  "FQ": 0.2},
    "user-positive-feedback":           {"IQ": 0.0,  "EQ": 0.2,  "FQ": 0.1},
    "user-correction":                  {"IQ": -0.1, "EQ": -0.3, "FQ": -0.1},
    "task-rework":                      {"IQ": 0.0,  "EQ": -0.1, "FQ": -0.3},
    "intentional-challenge-success":    {"IQ": 0.2,  "EQ": 0.0,  "FQ": 0.0},
    "intentional-challenge-partial":    {"IQ": 0.1,  "EQ": 0.0,  "FQ": 0.0},
    "intentional-challenge-fail":       {"IQ": 0.0,  "EQ": 0.0,  "FQ": 0.0},
    "learning-achievement-normal":      {"IQ": 0.1,  "EQ": 0.0,  "FQ": 0.0},
    "learning-achievement-error":       {"IQ": 0.15, "EQ": 0.0,  "FQ": 0.0},
    "learning-achievement-challenge":   {"IQ": 0.12, "EQ": 0.0,  "FQ": 0.0},
    "capability-reuse-near":            {"IQ": 0.1,  "EQ": 0.0,  "FQ": 0.1},
    "capability-reuse-far":             {"IQ": 0.12, "EQ": 0.0,  "FQ": 0.05},
    "reputation-recovered":             {"IQ": 0.1,  "EQ": 0.1,  "FQ": 0.0},
    "capability-decay-penalty":         {"IQ": -0.1, "EQ": 0.0,  "FQ": -0.1},
}

NEGATIVE_EVENTS     = {"user-correction", "task-rework", "error-found", "capability-decay-penalty"}
NO_RESISTANCE_EVENTS = NEGATIVE_EVENTS

CHAIN_MAX_POSITIVE = 0.6
CHAIN_MAX_NEGATIVE = -0.6
DERIVED_MAX_RATIO  = 0.5
DAILY_FQ_CAP       = 2


def load_profile() -> dict:
    if os.path.exists(PROFILE_JSON):
        return safe_read_json(PROFILE_JSON)
    return {}


def resistance_factor(current_score: float) -> float:
    return max(0.1, (100 - current_score) / 50)


def get_base_delta_key(event: dict) -> str:
    etype = event.get("event_type", "")

    if etype == "task-done":
        return "task-done-new" if event.get("is_first_of_type") else "task-done-routine"

    if etype == "intentional-challenge":
        outcome = event.get("outcome", "fail")
        return f"intentional-challenge-{outcome}"

    if etype == "learning-achievement":
        trigger = event.get("learning_trigger") or event.get("trigger", "normal")
        if trigger == "error-driven":
            return "learning-achievement-error"
        if trigger == "challenge-driven":
            return "learning-achievement-challenge"
        return "learning-achievement-normal"

    if etype == "capability-reuse":
        transfer = event.get("transfer_type", "near")
        return f"capability-reuse-{transfer}"

    return etype


def compute_delta(event: dict, index: dict) -> dict:
    key      = get_base_delta_key(event)
    base     = BASE_DELTAS.get(key, {"IQ": 0.0, "EQ": 0.0, "FQ": 0.0})
    evidence = event.get("evidence_level", "self")
    coef     = EVIDENCE_COEFFICIENTS.get(evidence, 0.2)
    etype    = event.get("event_type", "")

    result = {}
    for dim in ["IQ", "EQ", "FQ"]:
        bd = base.get(dim, 0.0)
        if bd == 0.0:
            result[dim] = 0.0
            continue
        if bd > 0 and etype not in NO_RESISTANCE_EVENTS:
            rf = resistance_factor(index.get(dim, {}).get("score", 50.0))
        else:
            rf = 1.0
        # self 证据只进 EQ_process，不直接改 IQ/FQ
        if evidence == "self" and dim in ("IQ", "FQ"):
            result[dim] = 0.0
        else:
            result[dim] = round(bd * coef * rf, 4)

    return result


def get_task_done_count_today(chain: list, task_type: str, today_str: str) -> int:
    count = 0
    for record in chain:
        if (record.get("event_type") == "task-done"
                and record.get("task_type") == task_type
                and (record.get("ts") or "").startswith(today_str)
                and record.get("processed", False)):
            count += 1
    return count


def get_penalty_balance(chain: list, capability_id: str) -> float:
    """计算当前修复周期内该能力的待补平净扣分"""
    negative_total  = 0.0
    recovered_total = 0.0
    in_cycle        = False

    for record in chain:
        etype = record.get("event_type", "")
        caps  = record.get("capability_ids", [])
        if capability_id not in caps:
            continue
        if etype in {"error-found", "task-rework", "user-correction"}:
            negative_total += abs(record.get("actual_delta", {}).get("IQ", 0.0))
            in_cycle = True
        elif etype == "reputation-recovered" and in_cycle:
            recovered_total += record.get("actual_delta", {}).get("IQ", 0.0)

    return max(0.0, negative_total - recovered_total)


def is_first_task_type(chain: list, task_type: str) -> bool:
    for record in chain:
        if (record.get("event_type") == "task-done"
                and record.get("task_type") == task_type
                and record.get("processed", False)):
            return False
    return True


def update_capability_status(capabilities: list, event: dict) -> list:
    etype         = event.get("event_type", "")
    caps_in_event = event.get("capability_ids", [])

    for cap in capabilities:
        if cap["capability_id"] not in caps_in_event:
            continue

        if etype == "learning-achievement":
            if cap.get("status") == "observed":
                cap["status"] = "declared"

        elif etype == "capability-reuse":
            cap["reuse_count"] = cap.get("reuse_count", 0) + 1
            if event.get("transfer_type") == "far":
                cap["far_transfer_count"]  = cap.get("far_transfer_count", 0) + 1
            else:
                cap["near_transfer_count"] = cap.get("near_transfer_count", 0) + 1

            near  = cap.get("near_transfer_count", 0)
            far   = cap.get("far_transfer_count", 0)
            total = cap.get("reuse_count", 0)

            if cap.get("status") == "declared" and total >= 1:
                cap["status"] = "standard_verified"
            if cap.get("status") == "standard_verified" and total >= 3 and near >= 2 and far >= 1:
                cap["status"] = "strong_verified"

        cap["last_used"] = (event.get("ts") or "")[:10]

    return capabilities


def process_events(unprocessed: list, all_chain: list,
                   index: dict, capabilities: list, profile: dict) -> tuple:
    today_str      = datetime.now(CST).strftime("%Y-%m-%d")
    daily_fq_counts = {}
    processed_ids  = set()
    chain_deltas   = {}
    evo_nodes      = []

    for event in unprocessed:
        etype    = event.get("event_type", "")
        source   = event.get("source_type", "")
        event_id = event.get("event_id", "")

        if source == "diagnostic":
            event["processed"] = True
            processed_ids.add(event_id)
            continue

        task_type = event.get("task_type", "general")
        task_id   = event.get("task_id", event_id)

        # 判断是否首次任务类型
        if etype == "task-done":
            event["is_first_of_type"] = is_first_task_type(all_chain, task_type)

        # FQ 日限
        fq_capped = False
        if etype == "task-done" and not event.get("is_first_of_type"):
            cap_count = daily_fq_counts.get(task_type, 0)
            cap_limit = profile.get("daily_fq_cap_per_task_type", DAILY_FQ_CAP)
            if cap_count >= cap_limit:
                fq_capped = True
            else:
                daily_fq_counts[task_type] = cap_count + 1

        # reputation-recovered 封顶
        rep_capped   = False
        actual_delta = compute_delta(event, index)
        if etype == "reputation-recovered":
            for cap_id in event.get("capability_ids", []):
                balance = get_penalty_balance(all_chain, cap_id)
                if balance <= 0:
                    actual_delta = {"IQ": 0.0, "EQ": 0.0, "FQ": 0.0}
                    rep_capped   = True
                else:
                    for dim in ["IQ", "EQ"]:
                        actual_delta[dim] = min(actual_delta[dim], balance)

        if fq_capped:
            actual_delta["FQ"] = 0.0

        # 链级上限检查
        chain_key = task_id
        chain_sum = chain_deltas.get(chain_key, {"IQ": 0.0, "EQ": 0.0, "FQ": 0.0})
        for dim in ["IQ", "EQ", "FQ"]:
            new_sum = chain_sum[dim] + actual_delta[dim]
            if new_sum > CHAIN_MAX_POSITIVE:
                actual_delta[dim] = max(0.0, CHAIN_MAX_POSITIVE - chain_sum[dim])
            elif new_sum < CHAIN_MAX_NEGATIVE:
                actual_delta[dim] = min(0.0, CHAIN_MAX_NEGATIVE - chain_sum[dim])
            chain_sum[dim] = chain_sum[dim] + actual_delta[dim]
        chain_deltas[chain_key] = chain_sum

        # 写入指数
        index_before = {dim: index.get(dim, {}).get("score", 50.0) for dim in ["IQ", "EQ", "FQ"]}
        for dim in ["IQ", "EQ", "FQ"]:
            current = index.get(dim, {}).get("score", 50.0)
            if dim not in index:
                index[dim] = {"score": 50.0}
            index[dim]["score"] = round(current + actual_delta.get(dim, 0.0), 4)

        # 更新能力状态
        capabilities = update_capability_status(capabilities, event)

        # 记录 evo node
        evo_node = {
            "node_id":          f"evo-{event_id}",
            "ts":               event.get("ts"),
            "primary_event_id": event_id,
            "base_event_type":  etype,
            "task_id":          task_id,
            "scoring_decision": {
                "base_delta_key":       get_base_delta_key(event),
                "evidence_level":       event.get("evidence_level", "self"),
                "evidence_coefficient": EVIDENCE_COEFFICIENTS.get(
                                            event.get("evidence_level", "self"), 0.2),
                "fq_capped":            fq_capped,
                "rep_capped":           rep_capped,
                "actual_delta":         actual_delta,
            },
            "index_before": index_before,
            "index_after":  {dim: index.get(dim, {}).get("score", 50.0) for dim in ["IQ", "EQ", "FQ"]},
            "processed":    True,
        }

        evo_nodes.append(evo_node)
        event["processed"]    = True
        event["actual_delta"] = actual_delta
        processed_ids.add(event_id)

    return index, capabilities, evo_nodes, processed_ids


def update_recent_digest(index: dict):
    if not os.path.exists(RECENT_DIGEST):
        digest = {}
    else:
        digest = safe_read_json(RECENT_DIGEST)
    digest["index_snapshot"] = {
        dim: index.get(dim, {}).get("score", 50.0) for dim in ["IQ", "EQ", "FQ"]
    }
    digest["updated_at"] = datetime.now(CST).isoformat()
    safe_write_json(RECENT_DIGEST, digest)


def main():
    print(f"[evolve] 开始执行 — {datetime.now(CST).isoformat()}")

    profile      = load_profile()
    index        = safe_read_json(INTELLIGENCE_INDEX) if os.path.exists(INTELLIGENCE_INDEX) \
                   else {"IQ": {"score": 50.0}, "EQ": {"score": 50.0}, "FQ": {"score": 50.0}}
    capabilities = safe_read_json(CAPABILITIES_JSON).get("capabilities", []) \
                   if os.path.exists(CAPABILITIES_JSON) else []

    all_chain = safe_read_jsonl(EVOLUTION_CHAIN)

    # ★ 修复1：加 event_id 存在性检查，排除 evo node（node_id/primary_event_id 格式）
    unprocessed = [
        e for e in all_chain
        if not e.get("processed", False)
        and e.get("source_type") != "diagnostic"
        and e.get("event_id") is not None
    ]

    print(f"[evolve] 待处理事件：{len(unprocessed)} 条")

    if not unprocessed:
        print("[evolve] 无待处理事件，退出。")
        return

    index, capabilities, evo_nodes, processed_ids = process_events(
        unprocessed, all_chain, index, capabilities, profile
    )

    # ★ 修复2：dict comprehension 加守卫，防止残留 None key（双保险）
    processed_map = {
        e.get("event_id"): e
        for e in unprocessed
        if e.get("event_id") is not None
    }

    updated_chain = []
    for record in all_chain:
        eid = record.get("event_id")
        if eid in processed_map:
            updated_chain.append(processed_map[eid])
        else:
            updated_chain.append(record)

    # 追加 evo nodes
    for node in evo_nodes:
        safe_append_jsonl(EVOLUTION_CHAIN, node)

    # 更新指数
    index["last_updated"] = datetime.now(CST).strftime("%Y-%m-%d")
    safe_write_json(INTELLIGENCE_INDEX, index)

    # 更新能力库
    cap_data = safe_read_json(CAPABILITIES_JSON) if os.path.exists(CAPABILITIES_JSON) else {}
    cap_data["capabilities"] = capabilities
    safe_write_json(CAPABILITIES_JSON, cap_data)

    update_recent_digest(index)

    print(f"[evolve] 完成。处理事件：{len(processed_ids)} 条")
    for dim in ["IQ", "EQ", "FQ"]:
        print(f"  {dim}: {index.get(dim, {}).get('score', 50.0):.2f}")


if __name__ == "__main__":
    main()
