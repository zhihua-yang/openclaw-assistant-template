#!/usr/bin/env python3
"""
create_event.py — OpenClaw v3.11.1-Lite
结构化事件录入，无模型调用
"""

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
MEMORY   = BASE_DIR / "memory"
CHAIN    = MEMORY / "evolution_chain.jsonl"
PROFILE  = MEMORY / "profile.json"

NOW      = datetime.now()
TODAY    = NOW.strftime("%Y-%m-%d")
NOW_TS   = NOW.strftime("%Y-%m-%dT%H:%M:%S")

# ── 事件类型定义 ──────────────────────────────────
FACT_TYPES = {
    "task-done":               "完成一个明确任务",
    "error-fix":               "发现并修复 bug / 错误",
    "error-found":             "发现错误（尚未修复）",
    "task-rework":             "任务需要返工重做",
    "user-correction":         "被用户指出错误",
    "user-positive-feedback":  "收到用户明确正向反馈",
    "system-improvement":      "完成系统性改进",
    "intentional-challenge":   "主动刻意练习挑战",
}

DERIVED_TYPES = {
    "learning-achievement":    "学习收获 / 认知更新（派生，需 --parent）",
    "capability-reuse":        "能力复用验证（派生，需 --parent）",
    "capability-status-change":"能力状态变更（系统自动，慎用）",
    "antipattern-extracted":   "提炼避坑规则（派生）",
    "reputation-recovered":    "信誉恢复（派生）",
    "capability-decay-penalty":"能力衰减惩罚（由 weekly_reflection 触发）",
    "milestone-unlocked":      "里程碑解锁（派生）",
}

ALL_TYPES = {**FACT_TYPES, **DERIVED_TYPES}

VALID_DIFFICULTIES    = ("routine", "stretch", "novel")
VALID_CONFIDENCES     = ("high", "medium", "low")
VALID_EVIDENCES       = ("external", "self")   # logical 只能由系统产生
VALID_TRANSFERS       = ("near", "far")
VALID_TRIGGERS        = ("normal", "error-driven", "challenge-driven")
VALID_CHALLENGE_TYPES = ("consolidate", "stretch", "transfer")
VALID_OUTCOMES        = ("success", "partial", "fail")


def load_profile():
    if PROFILE.exists():
        return json.loads(PROFILE.read_text())
    return {}


def validate_args(args, profile):
    errors = []

    if args.type not in ALL_TYPES:
        errors.append(f"未知事件类型: {args.type}，使用 --list-types 查看可用类型")

    if args.evidence and args.evidence == "logical":
        errors.append("evidence=logical 只能由系统自动推断，不允许手动填写")

    if args.type in DERIVED_TYPES and not args.parent:
        if args.type in ("learning-achievement", "capability-reuse"):
            errors.append(f"{args.type} 是派生事件，必须提供 --parent <parent_event_id>")

    if args.type == "learning-achievement":
        min_len = profile.get("min_learning_content_length", 12)
        if args.cognitive_update and len(args.cognitive_update) < min_len:
            errors.append(f"--cognitive-update 内容过短（最少 {min_len} 字），请描述具体认知更新")

    if args.difficulty and args.difficulty not in VALID_DIFFICULTIES:
        errors.append(f"--difficulty 无效值: {args.difficulty}，可选: {VALID_DIFFICULTIES}")

    if args.confidence and args.confidence not in VALID_CONFIDENCES:
        errors.append(f"--confidence 无效值: {args.confidence}，可选: {VALID_CONFIDENCES}")

    if args.evidence and args.evidence not in VALID_EVIDENCES:
        errors.append(f"--evidence 无效值: {args.evidence}，可选: {VALID_EVIDENCES}（logical 由系统产生）")

    if args.transfer and args.transfer not in VALID_TRANSFERS:
        errors.append(f"--transfer 无效值: {args.transfer}，可选: {VALID_TRANSFERS}")

    if args.trigger and args.trigger not in VALID_TRIGGERS:
        errors.append(f"--trigger 无效值: {args.trigger}，可选: {VALID_TRIGGERS}")

    if args.challenge_type and args.challenge_type not in VALID_CHALLENGE_TYPES:
        errors.append(f"--challenge-type 无效值: {args.challenge_type}，可选: {VALID_CHALLENGE_TYPES}")

    if args.outcome and args.outcome not in VALID_OUTCOMES:
        errors.append(f"--outcome 无效值: {args.outcome}，可选: {VALID_OUTCOMES}")

    return errors


def build_event(args, profile):
    event_id  = f"evt-{TODAY}-{uuid.uuid4().hex[:8]}"
    task_id   = args.task_id or event_id
    evidence  = args.evidence or profile.get("evidence_default", "self")

    event = {
        "id":         event_id,
        "type":       args.type,
        "date":       TODAY,
        "created_at": NOW_TS,
        "task_id":    task_id,
        "content":    args.content,
        "evidence_level": evidence,
    }

    # 可选字段（有值才写入，保持 JSON 干净）
    if args.task_type:
        event["task_type"] = args.task_type
    if args.difficulty:
        event["difficulty"] = args.difficulty
    if args.confidence:
        event["confidence"] = args.confidence
    if args.evidence_ref:
        event["evidence_ref"] = args.evidence_ref
    if args.cap:
        event["capability_id"] = args.cap
    if args.parent:
        event["parent_id"] = args.parent
    if args.trigger and args.trigger != "normal":
        event["trigger"] = args.trigger
    if args.cognitive_update:
        event["cognitive_update"] = args.cognitive_update
    if args.transfer:
        event["transfer_type"] = args.transfer
    if args.challenge_type:
        event["challenge_type"] = args.challenge_type
    if args.outcome:
        event["outcome"] = args.outcome
    if args.note:
        event["note"] = args.note

    # 类型推断
    event["event_class"] = "derived" if args.type in DERIVED_TYPES else "fact"

    return event


def append_event(event):
    MEMORY.mkdir(parents=True, exist_ok=True)
    with CHAIN.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def print_event_preview(event):
    print("\n── 事件预览 ──────────────────────────────")
    for k, v in event.items():
        print(f"  {k:<20}: {v}")
    print("──────────────────────────────────────────\n")


def cmd_list_types():
    print("\n── 事实事件（Fact）─────────────────────────")
    for t, desc in FACT_TYPES.items():
        print(f"  {t:<30}  {desc}")
    print("\n── 派生事件（Derived，需 --parent）─────────")
    for t, desc in DERIVED_TYPES.items():
        print(f"  {t:<30}  {desc}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="OpenClaw v3.11.1-Lite 事件录入工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 最小模式
  python3 create_event.py --type task-done --content "完成邮件修复" --task-type email-debug

  # 完整模式
  python3 create_event.py --type task-done --content "完成邮件修复" \\
    --task-type email-debug --difficulty stretch --confidence medium \\
    --evidence external --evidence-ref "log:cron-20260322" --cap cap_smtp

  # 错误驱动学习
  python3 create_event.py --type learning-achievement \\
    --content "理解了 SMTP 认证失败根因" --trigger error-driven \\
    --cognitive-update "Gmail 需要 App Password，不是账号密码" \\
    --parent evt-20260322-abc123

  # 查看事件类型
  python3 create_event.py --list-types
        """
    )

    parser.add_argument("--list-types",      action="store_true",  help="列出所有可用事件类型")
    parser.add_argument("--type",            type=str,             help="事件类型")
    parser.add_argument("--content",         type=str,             help="事件内容描述")
    parser.add_argument("--task-type",       type=str,             help="任务类型标签（如 email-debug）")
    parser.add_argument("--task-id",         type=str,             help="手动指定 task_id（同一任务链多个事件用同一 task_id）")
    parser.add_argument("--difficulty",      type=str,             choices=VALID_DIFFICULTIES,    help="任务难度")
    parser.add_argument("--confidence",      type=str,             choices=VALID_CONFIDENCES,     help="事前置信度")
    parser.add_argument("--evidence",        type=str,             choices=VALID_EVIDENCES,       help="证据等级（external/self，logical 由系统产生）")
    parser.add_argument("--evidence-ref",    type=str,             help="证据引用（如 log:xxx、screenshot:xxx）")
    parser.add_argument("--cap",             type=str,             help="关联能力 ID（如 cap_smtp_debug）")
    parser.add_argument("--parent",          type=str,             help="父事件 ID（派生事件必填）")
    parser.add_argument("--trigger",         type=str,             choices=VALID_TRIGGERS,        help="触发类型")
    parser.add_argument("--cognitive-update",type=str,             help="认知更新描述（learning-achievement 推荐填写）")
    parser.add_argument("--transfer",        type=str,             choices=VALID_TRANSFERS,       help="迁移类型（near/far）")
    parser.add_argument("--challenge-type",  type=str,             choices=VALID_CHALLENGE_TYPES, help="挑战类型")
    parser.add_argument("--outcome",         type=str,             choices=VALID_OUTCOMES,        help="任务结果")
    parser.add_argument("--note",            type=str,             help="备注（自由文本）")
    parser.add_argument("--dry-run",         action="store_true",  help="预览事件，不写入文件")

    args = parser.parse_args()

    # --list-types 独立执行，不依赖其他参数
    if args.list_types:
        cmd_list_types()
        sys.exit(0)

    # 其他命令需要 --type 和 --content
    if not args.type:
        parser.error("请提供 --type 参数，或使用 --list-types 查看可用类型")
    if not args.content:
        parser.error("请提供 --content 参数")

    profile = load_profile()

    # 验证参数
    errors = validate_args(args, profile)
    if errors:
        print("❌ 参数错误：")
        for e in errors:
            print(f"  · {e}")
        sys.exit(1)

    # 构建事件
    event
