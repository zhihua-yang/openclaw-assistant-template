#!/usr/bin/env python3
"""
weekly_reflection.py v1.0
每周自动生成周报，写入 memory/project.md
- 不依赖 OpenClaw skill / payload
- 直接读取 events.jsonl + memory/ 生成结构化周报
- 输出 ≤200字摘要到 stdout（供 cron 日志）
- 写一条 task-done 事件到 events.jsonl 记录周报已生成

用法：
  python3 weekly_reflection.py          # 正常运行
  python3 weekly_reflection.py --dry-run # 只打印，不写文件
"""

import json
import sys
import re
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta, timezone

# 动态推导 workspace 根目录
BASE  = Path(__file__).parent.parent
LOGS  = BASE / '.sys' / 'logs' / 'events.jsonl'
PROJ  = BASE / 'memory' / 'project.md'
CORE  = BASE / 'memory' / 'core.md'
RECENT = BASE / 'memory' / 'recent.md'

DRY_RUN = '--dry-run' in sys.argv


def load_events_last_7_days():
    events = []
    if not LOGS.exists():
        return events
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    for line in LOGS.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
            ts = e.get('ts', '')
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                events.append(e)
        except Exception:
            pass
    return events


def summarize_events(events):
    type_counts = Counter(e.get('type', 'unknown') for e in events)
    all_tags = []
    for e in events:
        all_tags.extend(e.get('tags', e.get('tag', [])))
    top_tags = Counter(all_tags).most_common(5)

    tasks_done     = [e for e in events if e.get('type') == 'task-done']
    errors_found   = [e for e in events if e.get('type') in ('error-found', 'error-fix')]
    improvements   = [e for e in events if e.get('type') == 'system-improvement']
    capabilities   = [e for e in events if e.get('type') in ('new-capability', 'learning-achievement')]
    corrections    = [e for e in events if e.get('type') == 'user-correction']

    return {
        'total':        len(events),
        'type_counts':  type_counts,
        'top_tags':     top_tags,
        'tasks_done':   tasks_done,
        'errors_found': errors_found,
        'improvements': improvements,
        'capabilities': capabilities,
        'corrections':  corrections,
    }


def generate_report(summary, week_str):
    lines = [
        f'',
        f'## 周报 {week_str}',
        f'',
        f'**本周事件总计：{summary["total"]} 条**',
        f'',
    ]

    # 事件类型分布
    if summary['type_counts']:
        lines.append('### 事件分布')
        for t, c in summary['type_counts'].most_common():
            lines.append(f'- {t}: {c} 条')
        lines.append('')

    # 高频 Tag
    if summary['top_tags']:
        tag_str = '、'.join(f'{t}×{c}' for t, c in summary['top_tags'])
        lines.append(f'**高频 Tag**：{tag_str}')
        lines.append('')

    # 完成的任务
    if summary['tasks_done']:
        lines.append('### ✅ 完成的任务')
        for e in summary['tasks_done'][:10]:
            content = e.get('content', '').split('\n')[0][:80]
            lines.append(f'- {content}')
        lines.append('')

    # 新能力 / 学习
    if summary['capabilities']:
        lines.append('### 🧠 新能力 / 学习')
        for e in summary['capabilities'][:5]:
            content = e.get('content', '').split('\n')[0][:80]
            lines.append(f'- {content}')
        lines.append('')

    # 系统改进
    if summary['improvements']:
        lines.append('### ⚙️ 系统改进')
        for e in summary['improvements'][:5]:
            content = e.get('content', '').split('\n')[0][:80]
            lines.append(f'- {content}')
        lines.append('')

    # 错误 & 修复
    if summary['errors_found']:
        lines.append('### 🐛 错误 & 修复')
        for e in summary['errors_found'][:5]:
            content = e.get('content', '').split('\n')[0][:80]
            lines.append(f'- {content}')
        lines.append('')

    # 用户纠正
    if summary['corrections']:
        lines.append('### 📝 用户纠正')
        for e in summary['corrections'][:5]:
            content = e.get('content', '').split('\n')[0][:80]
            lines.append(f'- {content}')
        lines.append('')

    lines.append('---')
    return '\n'.join(lines)


def generate_summary(summary, week_str):
    """生成 ≤200字的摘要，输出到 stdout / cron 日志"""
    tasks_n  = len(summary['tasks_done'])
    caps_n   = len(summary['capabilities'])
    errs_n   = len(summary['errors_found'])
    improv_n = len(summary['improvements'])
    top_tags = '、'.join(t for t, _ in summary['top_tags'][:3]) or '无'

    summary_text = (
        f'[周报 {week_str}] '
        f'共 {summary["total"]} 条事件｜'
        f'任务完成 {tasks_n} 项｜'
        f'新能力 {caps_n} 项｜'
        f'错误修复 {errs_n} 项｜'
        f'系统改进 {improv_n} 项｜'
        f'高频Tag：{top_tags}'
    )
    # 截断到200字
    if len(summary_text) > 200:
        summary_text = summary_text[:197] + '...'
    return summary_text


def append_event(content):
    """记录周报已生成的事件"""
    if not LOGS.exists():
        return
    record = {
        'ts':      datetime.now(timezone.utc).isoformat(),
        'type':    'task-done',
        'content': content,
        'tags':    ['weekly', 'cron', 'reflection'],
        'count':   1,
    }
    with LOGS.open('a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')


def write_to_project_md(report):
    """追加写入 memory/project.md，保留历史"""
    PROJ.parent.mkdir(parents=True, exist_ok=True)
    if not PROJ.exists():
        PROJ.write_text('# Project Memory\n_周报由 weekly_reflection.py 自动生成_\n', encoding='utf-8')
    existing = PROJ.read_text(encoding='utf-8')
    PROJ.write_text(existing + report, encoding='utf-8')


def main():
    now      = datetime.now(timezone.utc)
    week_str = now.strftime('%Y-W%W')  # e.g. 2026-W12

    events  = load_events_last_7_days()
    summary = summarize_events(events)
    report  = generate_report(summary, week_str)
    short   = generate_summary(summary, week_str)

    if DRY_RUN:
        print('[weekly_reflection] DRY RUN — 不写入文件')
        print()
        print('=== 周报内容 ===')
        print(report)
        print()
        print('=== 摘要（≤200字）===')
        print(short)
        return 0

    write_to_project_md(report)
    append_event(f'weekly-self-reflection 周报已生成：{week_str}，共 {summary["total"]} 条事件')

    print(short)
    print(f'[weekly_reflection] 周报已写入：{PROJ}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
