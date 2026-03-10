#!/bin/bash
# log_stats.sh - 查询最近一次对话的耗时、tool调用数和今日对话次数
# 用法: bash log_stats.sh [日志文件]

LOG_FILE="${1:-/tmp/openclaw/openclaw-$(date +%Y-%m-%d).log}"

if [ ! -f "$LOG_FILE" ]; then
  echo "日志文件不存在: $LOG_FILE"
  exit 1
fi

python3 << 'PYEOF'
import json
import re
import sys
import os

log_file = os.environ.get('LOG_FILE_PATH', '/tmp/openclaw/openclaw-' + __import__('datetime').date.today().isoformat() + '.log')

runs = {}  # runId -> {start, end, duration, tool_count}
today_run_count = 0

with open(log_file, 'r') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except:
            continue
        
        msg = data.get('1', '')
        
        if 'embedded run prompt end' in msg:
            today_run_count += 1
            m_run = re.search(r'runId=([a-f0-9-]+)', msg)
            m_dur = re.search(r'durationMs=(\d+)', msg)
            if m_run and m_dur:
                run_id = m_run.group(1)
                if run_id not in runs:
                    runs[run_id] = {}
                runs[run_id]['duration'] = int(m_dur.group(1))
                runs[run_id]['end_time'] = data.get('_meta', {}).get('date', '')
                if 'tool_count' not in runs[run_id]:
                    runs[run_id]['tool_count'] = 0
        
        elif 'embedded run tool start' in msg:
            m_run = re.search(r'runId=([a-f0-9-]+)', msg)
            if m_run:
                run_id = m_run.group(1)
                if run_id not in runs:
                    runs[run_id] = {'tool_count': 0}
                runs[run_id]['tool_count'] = runs[run_id].get('tool_count', 0) + 1

if not runs:
    print("未找到对话记录")
    sys.exit(1)

# 找最近一次完整的 run（有 duration 的）
finished = {k: v for k, v in runs.items() if 'duration' in v}
if not finished:
    print("未找到已完成的对话记录")
    sys.exit(1)

# 按 end_time 排序取最新
latest_id = sorted(finished.keys(), key=lambda k: finished[k].get('end_time', ''))[-1]
latest = finished[latest_id]

dur_ms = latest['duration']
tool_count = latest.get('tool_count', 0)
dur_s = dur_ms / 1000

print(f"⏱ 最近一次耗时: {dur_ms}ms ({dur_s:.1f}s)")
print(f"🔧 Tool调用数: {tool_count}")
print(f"💬 今日对话总次数: {today_run_count}")

PYEOF
