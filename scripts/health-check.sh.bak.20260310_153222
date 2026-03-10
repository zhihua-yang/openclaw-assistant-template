#!/bin/bash

# WORKSPACE 必须由调用方传入，否则报错
if [ -z "$WORKSPACE" ]; then
  echo "ERR WORKSPACE 未设置，请用 WORKSPACE=/path bash health-check.sh 调用"
  exit 1
fi

BASE="$WORKSPACE"
PASS=0; FAIL=0

check() {
  local desc="$1"; shift
  if eval "$@" &>/dev/null; then
    echo "OK  $desc"; ((PASS++))
  else
    echo "ERR $desc"; ((FAIL++))
  fi
}

check "workspace 可写"          "touch \"$BASE/.wt\" && rm \"$BASE/.wt\""
check "events.jsonl 可写"       "touch \"$BASE/.openclaw/logs/events.jsonl\""
check "events.jsonl JSON 合法"  "python3 - << 'PY'
import json, sys
bad = []
try:
    for i, l in enumerate(open('$BASE/.openclaw/logs/events.jsonl'), 1):
        l = l.strip()
        if not l: continue
        try: json.loads(l)
        except: bad.append(i)
    if bad: print('bad lines:', bad); sys.exit(1)
except FileNotFoundError:
    pass
PY"
check "Git 仓库正常"            "cd \"$BASE\" && git status"
check "磁盘 > 1GB"              "[ \$(df \"$BASE\" --output=avail 2>/dev/null | tail -1 || df \"$BASE\" | tail -1 | awk '{print \$4}') -gt 1048576 ]"
check "IDENTITY.md 存在"        "test -f \"$BASE/IDENTITY.md\""
check "AGENTS.md 存在"          "test -f \"$BASE/AGENTS.md\""
check "memory/core.md 存在"     "test -f \"$BASE/memory/core.md\""
check "scripts/evolve.py 存在"  "test -f \"$BASE/scripts/evolve.py\""

echo ""
echo "健康检查：OK=$PASS  ERR=$FAIL"
[ $FAIL -gt 0 ] && exit 1 || exit 0
