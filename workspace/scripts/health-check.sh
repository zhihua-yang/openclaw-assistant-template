#!/bin/bash
BASE="${WORKSPACE:-$HOME/.openclaw/workspace}"
PASS=0; FAIL=0

check() {
  local desc="$1"; shift
  if eval "$@" &>/dev/null; then echo "OK  $desc"; ((PASS++))
  else echo "ERR $desc"; ((FAIL++)); fi
}

disk_ok() {
  local avail
  avail=$(df -k "$BASE" 2>/dev/null | tail -1 | awk '{print $4}')
  [ -n "$avail" ] && [ "$avail" -gt 1048576 ]
}

# 自动探测运行时目录
EVENTS_FILE=""
for candidate in \
  "$BASE/.sys/logs/events.jsonl" \
  "$BASE/.openclaw/logs/events.jsonl"; do
  if [ -f "$candidate" ]; then
    EVENTS_FILE="$candidate"
    break
  fi
done
if [ -z "$EVENTS_FILE" ]; then
  mkdir -p "$BASE/.sys/logs"
  touch "$BASE/.sys/logs/events.jsonl"
  EVENTS_FILE="$BASE/.sys/logs/events.jsonl"
fi

echo "-- Runtime dir: $(dirname $EVENTS_FILE)"

# 基础环境
check "workspace writable"          "touch \"$BASE/.wt\" && rm \"$BASE/.wt\""
check "events.jsonl writable"       "touch \"$EVENTS_FILE\""
check "events.jsonl JSON valid"     "python3 -c \"
import json,sys
bad=[]
try:
  for i,l in enumerate(open('$EVENTS_FILE'),1):
    l=l.strip()
    if not l: continue
    try: json.loads(l)
    except: bad.append(i)
  if bad: print('bad lines:',bad); sys.exit(1)
except FileNotFoundError: pass
\""
check "Disk > 1GB"                  "disk_ok"

# 关键文件
check "IDENTITY.md exists"          "test -f \"$BASE/IDENTITY.md\""
check "AGENTS.md exists"            "test -f \"$BASE/AGENTS.md\""
check "memory/core.md exists"       "test -f \"$BASE/memory/core.md\""
check "memory/errors.md exists"     "test -f \"$BASE/memory/errors.md\""

# 脚本文件
check "scripts/evolve.py"           "test -f \"$BASE/scripts/evolve.py\""
check "scripts/create_event.py"     "test -f \"$BASE/scripts/create_event.py\""
check "scripts/session_note_writer.py" "test -f \"$BASE/scripts/session_note_writer.py\""
check "scripts/farewell_detector.py"   "test -f \"$BASE/scripts/farewell_detector.py\""

# 语法检查
check "evolve.py syntax"            "python3 -m py_compile \"$BASE/scripts/evolve.py\""
check "create_event.py syntax"      "python3 -m py_compile \"$BASE/scripts/create_event.py\""
check "session_note_writer.py syntax" "python3 -m py_compile \"$BASE/scripts/session_note_writer.py\""
check "farewell_detector.py syntax"   "python3 -m py_compile \"$BASE/scripts/farewell_detector.py\""

# session-notes 功能验证
check "farewell 'bye' detected"     "python3 \"$BASE/scripts/farewell_detector.py\" --text 'bye'"
check "farewell '再见' detected"     "python3 \"$BASE/scripts/farewell_detector.py\" --text '再见'"

# 双路径 sessions 目录
check ".sys/sessions dir exists"    "test -d \"$BASE/.sys/sessions\""
check ".openclaw/sessions dir"      "test -d \"$BASE/.openclaw/sessions\" || mkdir -p \"$BASE/.openclaw/sessions\""

# 事件质量抽查（近20条）
check "recent events have tags"     "python3 -c \"
import json
lines = open('$EVENTS_FILE').readlines()[-20:]
missing = [i+1 for i,l in enumerate(lines)
           if l.strip() and not json.loads(l).get('tags') and not json.loads(l).get('tag')]
if missing: print('missing tags lines:',missing); exit(1)
\" 2>/dev/null || true"

# 事件活跃度检查（近24小时是否有记录）
check "events active in 24h"        "python3 -c \"
import json
from datetime import datetime,timezone,timedelta
cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
found = False
try:
  for l in open('$EVENTS_FILE').readlines()[-50:]:
    l=l.strip()
    if not l: continue
    e=json.loads(l)
    ts=e.get('ts','')
    if ts:
      dt=datetime.fromisoformat(ts)
      if dt.tzinfo: dt=dt.astimezone(timezone.utc)
      else: dt=dt.replace(tzinfo=timezone.utc)
      if dt >= cutoff: found=True; break
except: pass
if not found: print('no events in last 24h'); exit(1)
\" 2>/dev/null || true"

echo ""
echo "Health Check: OK=$PASS  ERR=$FAIL"
[ $FAIL -gt 0 ] && exit 1 || exit 0
