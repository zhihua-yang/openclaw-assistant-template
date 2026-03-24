#!/usr/bin/env python3
"""
resolve_audit.py — 人工审计处理工具
只修改 status，不直接修改指数或能力状态
"""
import argparse
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import safe_read_jsonl, safe_write_json, safe_append_jsonl
from utils.paths import AUDIT_QUEUE, EVOLUTION_CHAIN

CST = timezone(timedelta(hours=8))


def load_queue() -> list:
    return safe_read_jsonl(AUDIT_QUEUE)


def save_queue(records: list):
    import json
    lock_path = os.path.expanduser(f"~/.openclaw_locks/{os.path.basename(AUDIT_QUEUE)}.lock")
    from filelock import FileLock
    with FileLock(lock_path, timeout=10):
        with open(AUDIT_QUEUE, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


def cmd_list(args):
    records = load_queue()
    pending = [r for r in records if r.get("status") == "pending"]
    if not pending:
        print("✅ 无待处理审计建议。")
        return
    print(f"📋 待处理建议（{len(pending)} 条）：\n")
    for r in pending:
        print(f"  [{r['id']}] {r['diag_type']} ({r.get('severity', 'info')})")
        print(f"    建议操作：{r.get('suggestion', r.get('recommended_action', '无'))}")
        print(f"    创建时间：{(r.get('ts') or r.get('created_at', ''))[:10]}")
        if r.get("related_event_ids"):
            print(f"    相关事件：{r['related_event_ids']}")
        print()


def cmd_adopt(args):
    records = load_queue()
    found = False
    for r in records:
        if r.get("id") == args.diag_id:
            if r.get("status") != "pending":
                print(f"⚠️ 该建议状态为 {r['status']}，无法采纳。")
                return
            r["status"] = "adopted"
            r["processed_at"] = datetime.now(CST).isoformat()
            found = True
            print(f"✅ 已采纳：{args.diag_id}")
            print(f"   类型：{r['diag_type']}")
            print(f"   建议后续操作：create_event.py 录入对应派生事件")
            break
    if not found:
        print(f"❌ 未找到：{args.diag_id}")
        return
    save_queue(records)


def cmd_dismiss(args):
    records = load_queue()
    found = False
    for r in records:
        if r.get("id") == args.diag_id:
            if r.get("status") != "pending":
                print(f"⚠️ 该建议状态为 {r['status']}，无法忽略。")
                return
            r["status"] = "dismissed"
            r["processed_at"] = datetime.now(CST).isoformat()
            found = True
            print(f"🚫 已忽略：{args.diag_id}")
            break
    if not found:
        print(f"❌ 未找到：{args.diag_id}")
        return
    save_queue(records)


def cmd_expire_old(args):
    from datetime import date
    records = load_queue()
    expire_days = 7
    today = date.today()
    count = 0
    for r in records:
        if r.get("status") == "pending":
            ts = r.get("ts", "")[:10]
            try:
                d = date.fromisoformat(ts)
                if (today - d).days > expire_days:
                    r["status"] = "expired"
                    r["processed_at"] = datetime.now(CST).isoformat()
                    count += 1
            except Exception:
                pass
    save_queue(records)
    print(f"🗂️ 已过期 {count} 条超期建议。")


def main():
    parser = argparse.ArgumentParser(description="OpenClaw 审计处理工具")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("--list", help="列出所有 pending 建议").set_defaults(func=cmd_list)
    p_adopt = sub.add_parser("--adopt", help="采纳某条建议")
    p_adopt.add_argument("diag_id")
    p_adopt.set_defaults(func=cmd_adopt)
    p_dismiss = sub.add_parser("--dismiss", help="忽略某条建议")
    p_dismiss.add_argument("diag_id")
    p_dismiss.set_defaults(func=cmd_dismiss)
    sub.add_parser("--expire-old", help="批量过期超期建议").set_defaults(func=cmd_expire_old)

    # 兼容 --list / --adopt / --dismiss / --expire-old 直接参数形式
    args, _ = parser.parse_known_args()

    import sys
    argv = sys.argv[1:]
    if "--list" in argv:
        cmd_list(args)
    elif "--adopt" in argv:
        idx = argv.index("--adopt")
        args.diag_id = argv[idx + 1]
        cmd_adopt(args)
    elif "--dismiss" in argv:
        idx = argv.index("--dismiss")
        args.diag_id = argv[idx + 1]
        cmd_dismiss(args)
    elif "--expire-old" in argv:
        cmd_expire_old(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
