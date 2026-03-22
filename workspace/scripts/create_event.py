#!/usr/bin/env python3
"""
create_event.py — 结构化事件录入
缺省 evidence_level=self，不做自动摘要或学习提炼
"""
import argparse
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import safe_append_jsonl, safe_read_json, safe_write_json
from utils.paths import EVOLUTION_CHAIN, CAPABILITIES_JSON, PROFILE_JSON, RECENT_DIGEST

CST = timezone(timedelta(hours=8))

VALID_FACT_EVENTS = [
    "task-done", "error-fix", "error-found", "task-rework",
    "user-correction", "user-positive-feedback", "system-improvement",
    "intentional-challenge"
]
VALID_DERIVED_EVENTS = [
    "learning-achievement", "capability-reuse", "capability-status-change",
    "antipattern-extracted", "reputation-recovered", "milestone-unlocked",
    "capability-decay-penalty"
]
VALID_DIFFICULTIES = ["routine", "stretch", "novel"]
VALID_CONFIDENCE   = ["high", "medium", "low"]
VALID_EVIDENCE     = ["external", "logical", "self"]
VALID_TRANSFER     = ["near", "far"]
VALID_TRIGGERS     = ["normal", "error-driven", "challenge-driven"]
VALID_CHALLENGE    = ["consolidate", "stretch", "transfer"]
VALID_OUTCOMES     = ["success", "partial", "fail"]


def load_profile() -> dict:
    if os.path.exists(PROFILE_JSON):
        return safe_read_json(PROFILE_JSON)
    return {"evidence_default": "self"}


def generate_event_id() -> str:
    now = datetime.now(CST)
    return f"evt-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"


def generate_task_id() -> str:
    now = datetime.now(CST)
    return f"task-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"


def determine_source_type(event_type: str) -> str:
    if event_type in VALID_FACT_EVENTS:
        return "fact"
    if event_type in VALID_DERIVED_EVENTS:
        return "derived"
    return "diagnostic"


def build_event(args, profile: dict) -> dict:
    now = datetime.now(CST)
    evidence = args.evidence or profile.get("evidence_default", "self")

    event = {
        "event_id": generate_event_id(),
        "ts": now.isoformat(),
        "source_type": determine_source_type(args.type),
        "event_type": args.type,
        "title": args.title or args.content[:40],
        "content": args.content,
        "task_type": args.task_type or "general",
        "task_id": args.task_id or generate_task_id(),
        "task_difficulty": args.difficulty or "routine",
        "is_primary_scoring_event": not args.derived,
        "parent_event_id": args.parent or None,
        "related_event_ids": args.related or [],
        "evidence_level": evidence,
        "evidence_refs": [args.evidence_ref] if args.evidence_ref else [],
        "capability_ids": args.cap or [],
        "antipattern_ids": args.antipattern or [],
        "tags": args.tags or [],
        "created_by": "create_event.py"
    }

    # 可选字段
    if args.confidence:
        event["pre_task_confidence"] = args.confidence
    if args.transfer:
        event["transfer_type"] = args.transfer
    if args.trigger:
        event["learning_trigger"] = args.trigger
    if args.challenge_type:
        event["challenge_type"] = args.challenge_type
    if args.outcome:
        event["outcome"] = args.outcome
    if args.cognitive_update:
        event["cognitive_update"] = args.cognitive_update

    return event


def validate_event(event: dict) -> list:
    errors = []
    if not event.get("content"):
        errors.append("content 不能为空")
    if event.get("evidence_level") not in VALID_EVIDENCE:
        errors.append(f"evidence_level 必须是 {VALID_EVIDENCE}")
    if event.get("task_difficulty") not in VALID_DIFFICULTIES:
        errors.append(f"task_difficulty 必须是 {VALID_DIFFICULTIES}")
    if event.get("event_type") == "learning-achievement":
        if event.get("learning_trigger") == "error-driven" and not event.get("cognitive_update"):
            errors.append("error-driven learning 必须提供 --cognitive-update")
        if not event.get("parent_event_id"):
            errors.append("learning-achievement 必须提供 --parent（主事件 ID）")
    if event.get("event_type") == "intentional-challenge":
        if not event.get("challenge_type"):
            errors.append("intentional-challenge 建议提供 --challenge-type")
    return errors


def update_recent_digest(event: dict):
    if not os.path.exists(RECENT_DIGEST):
        return
    try:
        digest = safe_read_json(RECENT_DIGEST)
        if event["event_type"] == "task-done":
            digest["last_task_ts"] = event["ts"]
        elif event["event_type"] in ["error-found", "error-fix", "task-rework", "user-correction"]:
            digest["recent_failures"] = digest.get("recent_failures", 0) + 1
        elif event["event_type"] == "intentional-challenge":
            digest["recent_challenges"] = digest.get("recent_challenges", 0) + 1
        digest["updated_at"] = event["ts"]
        safe_write_json(RECENT_DIGEST, digest)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="OpenClaw 事件录入工具")
    parser.add_argument("--type",           required=True,  help=f"事件类型: {VALID_FACT_EVENTS + VALID_DERIVED_EVENTS}")
    parser.add_argument("--content",        required=True,  help="事件内容描述")
    parser.add_argument("--title",          help="事件标题（可选，缺省截取 content 前40字）")
    parser.add_argument("--task-type",      help="任务类型，如 email-debug / cron-maintenance")
    parser.add_argument("--task-id",        help="任务 ID（可选，自动生成）")
    parser.add_argument("--difficulty",     choices=VALID_DIFFICULTIES, help="任务难度（默认 routine）")
    parser.add_argument("--confidence",     choices=VALID_CONFIDENCE,   help="事前把握程度")
    parser.add_argument("--evidence",       choices=VALID_EVIDENCE,     help="证据等级（默认 self）")
    parser.add_argument("--evidence-ref",   help="证据引用，如 log:xxx")
    parser.add_argument("--cap",            nargs="+", help="关联 capability_id（可多个）")
    parser.add_argument("--antipattern",    nargs="+", help="关联 antipattern_id（可多个）")
    parser.add_argument("--tags",           nargs="+", help="标签")
    parser.add_argument("--parent",         help="父事件 ID（派生事件必填）")
    parser.add_argument("--related",        nargs="+", help="相关事件 ID")
    parser.add_argument("--derived",        action="store_true", help="标记为非主计分事件")
    parser.add_argument("--transfer",       choices=VALID_TRANSFER,  help="迁移类型（capability-reuse 专用）")
    parser.add_argument("--trigger",        choices=VALID_TRIGGERS,  help="学习触发源（learning-achievement 专用）")
    parser.add_argument("--challenge-type", choices=VALID_CHALLENGE, help="挑战类型（intentional-challenge 专用）")
    parser.add_argument("--outcome",        choices=VALID_OUTCOMES,  help="结果（intentional-challenge 专用）")
    parser.add_argument("--cognitive-update", help="认知更新描述（error-driven learning 必填）")
    parser.add_argument("--dry-run",        action="store_true", help="只打印不写入")
    parser.add_argument("--list-types",     action="store_true", help="列出所有事件类型")

    args = parser.parse_args()

    if args.list_types:
        print("事实事件（fact）：", VALID_FACT_EVENTS)
        print("派生事件（derived）：", VALID_DERIVED_EVENTS)
        return

    profile = load_profile()
    event = build_event(args, profile)
    errors = validate_event(event)

    if errors:
        print("❌ 校验失败：")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    if args.dry_run:
        import json
        print("📋 预览（dry-run）：")
        print(json.dumps(event, ensure_ascii=False, indent=2))
        return

    safe_append_jsonl(EVOLUTION_CHAIN, event)
    update_recent_digest(event)

    print(f"✅ 事件已写入：{event['event_id']}")
    print(f"   类型：{event['event_type']} | 证据：{event['evidence_level']} | 难度：{event['task_difficulty']}")


if __name__ == "__main__":
    main()
