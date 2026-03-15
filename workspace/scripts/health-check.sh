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

check "workspace writable"       "touch \"$BASE/.wt\" && rm \"$BASE/.wt\""
check "events.jsonl writable"    "touch \"$EVENTS_FILE\""
check "events.jsonl JSON valid"  "python3 -c \"
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
check "Disk > 1GB"                "disk_ok"
check "IDENTITY.md exists"        "test -f \"$BASE/IDENTITY.md\""
check "AGENTS.md exists"          "test -f \"$BASE/AGENTS.md\""
check "memory/core.md exists"     "test -f \"$BASE/memory/core.md\""
check "memory/errors.md exists"   "test -f \"$BASE/memory/errors.md\""
check "scripts/evolve.py exists"  "test -f \"$BASE/scripts/evolve.py\""
check "scripts/create_event.py"   "test -f \"$BASE/scripts/create_event.py\""
check "evolve.py syntax OK"       "python3 -m py_compile \"$BASE/scripts/evolve.py\""
check "create_event.py syntax OK" "python3 -m py_compile \"$BASE/scripts/create_event.py\""
check "recent events have tags"   "python3 -c \"
import json
lines = open('$EVENTS_FILE').readlines()[-20:]
missing = [i+1 for i,l in enumerate(lines)
           if l.strip() and not json.loads(l).get('tags') and not json.loads(l).get('tag')]
if missing: print('missing tags lines:',missing); exit(1)
\" 2>/dev/null || true"

echo ""
echo "Health Check: OK=$PASS  ERR=$FAIL"
[ $FAIL -gt 0 ] && exit 1 || exit 0
