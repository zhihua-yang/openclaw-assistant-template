#!/usr/bin/env python3
"""
session_note_writer.py — OpenClaw v3.11.1-Lite
告别词触发时，将会话摘要写入新管道 memory/evolution_chain.jsonl
不再直接写 .sys/logs/events.jsonl 旧格式

调用方：farewell_detector.py
用法（farewell_detector.py 内部调用）：
  python3 session_note_writer.py \
    --type task-done \
    --content "会话结束：完成邮件修复" \
    --task-type session-summary \
    --evidence self
"""

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
CREATE_EVENT = SCRIPTS_DIR / "create_event.py"


def build_cmd(args) -> list:
    """把 session_note_writer 的参数翻译成 create_event.py 的参数列表"""
    cmd = [
        sys.executable, str(CREATE_EVENT),
        "--type",    args.type,
        "--content", args.content,
    ]
    if args.task_type:
        cmd += ["--task-type", args.task_type]
    if args.evidence:
        cmd += ["--evidence", args.evidence]
    if args.note:
        cmd += ["--note", args.note]
    if args.cap:
        cmd += ["--cap", args.cap]
    if args.difficulty:
        cmd += ["--difficulty", args.difficulty]
    return cmd


def main():
    parser = argparse.ArgumentParser(
        description="session_note_writer — 告别词触发，写入新管道 create_event.py"
    )
    # 保持与 farewell_detector.py 现有调用签名兼容
    parser.add_argument("--type",       default="task-done",      help="事件类型（默认 task-done）")
    parser.add_argument("--content",    required=True,            help="会话摘要内容")
    parser.add_argument("--task-type",  default="session-summary", help="任务类型标签")
    parser.add_argument("--evidence",   default="self",           help="证据等级（默认 self）")
    parser.add_argument("--note",       default=None,             help="备注")
    parser.add_argument("--cap",        default=None,             help="关联能力 ID")
    parser.add_argument("--difficulty", default=None,             help="任务难度")
    # 旧版 --tags 参数：静默忽略，不传给 create_event.py（新版无此参数）
    parser.add_argument("--tags",       default=None,             help="[已废弃] 旧版标签，静默忽略")

    args = parser.parse_args()

    if not CREATE_EVENT.exists():
        print(f"❌ 找不到 create_event.py: {CREATE_EVENT}", file=sys.stderr)
        sys.exit(1)

    cmd = build_cmd(args)

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"❌ create_event.py 调用失败 (exit {e.returncode})", file=sys.stderr)
        if e.stdout:
            print(e.stdout, end="")
        if e.stderr:
            print(e.stderr, end="", file=sys.stderr)
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
