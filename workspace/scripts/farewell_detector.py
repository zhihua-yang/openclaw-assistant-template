#!/usr/bin/env python3
"""
farewell_detector.py v1.0
检测输入文本是否包含告别词，若检测到则自动触发 session_note_writer.py。

用法（由 AGENTS.md 自动规则或 AI exec: 调用）：
  python3 farewell_detector.py --text "好的，再见"
  python3 farewell_detector.py --text "bye" --auto-trigger \
    --summary "..." --type task-done --content "..."

返回码：
  0 = 检测到告别词
  1 = 未检测到
  2 = 检测到并已触发 session_note_writer（--auto-trigger 模式）
"""

import argparse
import subprocess
import sys
from pathlib import Path

# 35+ 种告别词（中英文）
FAREWELL_KEYWORDS = [
    # 中文
    "再见", "拜了", "拜拜", "先这样", "下次再说", "结束", "退出",
    "88", "886", "晚安", "好的再见", "好了再见", "就这样吧",
    "暂时这样", "今天就到这", "今天就到这里", "先到这里",
    "先到这", "告一段落", "下线了", "去忙了", "忙去了",
    "有空再聊", "回头见", "待会见", "改天聊", "先聊到这",
    # 英文
    "bye", "goodbye", "good bye", "see you", "see ya",
    "later", "quit", "done", "that's all", "thats all",
    "good night", "gotta go", "gtg", "ttyl", "talk later",
    "take care", "peace out", "signing off", "log off",
    "we're done", "we are done", "all done",
]


def detect(text: str) -> tuple[bool, str]:
    """返回 (是否告别, 匹配到的关键词)"""
    text_lower = text.lower().strip()
    for kw in FAREWELL_KEYWORDS:
        if kw in text_lower:
            return True, kw
    return False, ""


def trigger_session_notes(args_extra: list) -> int:
    """调用 session_note_writer.py"""
    script = Path(__file__).parent / "session_note_writer.py"
    if not script.exists():
        print(f"ERR: session_note_writer.py not found at {script}", file=sys.stderr)
        return 1
    cmd = [sys.executable, str(script)] + args_extra
    print(f"[farewell_detector] triggering session_note_writer: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def main():
    p = argparse.ArgumentParser(description="farewell_detector.py v1.0")
    p.add_argument("--text",         required=True,  help="要检测的用户输入文本")
    p.add_argument("--auto-trigger", action="store_true",
                   help="检测到告别词时自动调用 session_note_writer.py")
    # 以下参数在 --auto-trigger 模式下透传给 session_note_writer
    p.add_argument("--summary",  default="会话自动结束（告别词触发）")
    p.add_argument("--type",     default="task-done")
    p.add_argument("--content",  nargs="+", default=["会话正常结束，告别词自动触发 session-notes"])
    p.add_argument("--tags",     default="session,auto-close")
    p.add_argument("--error",    default="")
    p.add_argument("--list-keywords", action="store_true", help="列出所有告别词")
    a = p.parse_args()

    if a.list_keywords:
        print("告别词列表：")
        for kw in FAREWELL_KEYWORDS:
            print(f"  {kw}")
        return 0

    found, matched = detect(a.text)

    if not found:
        print(f"[farewell_detector] 未检测到告别词")
        return 1

    print(f"[farewell_detector] 检测到告别词: '{matched}'")

    if not a.auto_trigger:
        return 0

    # 构建透传参数
    extra = [
        "--summary", a.summary,
        "--type",    a.type,
        "--content", *a.content,
        "--tags",    a.tags,
    ]
    if a.error:
        extra += ["--error", a.error]

    rc = trigger_session_notes(extra)
    return 2 if rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
