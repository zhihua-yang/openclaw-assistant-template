#!/bin/bash
BASE="${WORKSPACE:-$HOME/.openclaw/workspace}"
DATE=$(date +%Y-%m-%d)
DIR="$BASE/.openclaw/baseline"
LOG="$DIR/baseline-$DATE.log"
mkdir -p "$DIR"

{
  echo "=== 基线记录 $DATE ==="
  echo "IDENTITY.md 行数:      $(wc -l < "$BASE/IDENTITY.md"                  2>/dev/null || echo N/A)"
  echo "AGENTS.md 行数:        $(wc -l < "$BASE/AGENTS.md"                    2>/dev/null || echo N/A)"
  echo "memory/recent.md 行数: $(wc -l < "$BASE/memory/recent.md"             2>/dev/null || echo N/A)"
  echo "memory/project.md 行数:$(wc -l < "$BASE/memory/project.md"            2>/dev/null || echo N/A)"
  echo "skills 数量:           $(ls "$BASE/skills/" 2>/dev/null | wc -l)"
  echo "scripts 数量:          $(ls "$BASE/scripts/" 2>/dev/null | wc -l)"
  echo "事件总数:              $(wc -l < "$BASE/.openclaw/logs/events.jsonl"   2>/dev/null || echo 0)"
  echo "用户纠正次数:          $(grep -c '"user_correction"' "$BASE/.openclaw/logs/events.jsonl" 2>/dev/null || echo 0)"
  echo "新能力次数:            $(grep -c '"new_capability"'  "$BASE/.openclaw/logs/events.jsonl" 2>/dev/null || echo 0)"
  echo "git 提交数:            $(cd "$BASE" && git log --oneline 2>/dev/null | wc -l || echo 0)"
} > "$LOG"

PREV=$(ls "$DIR"/ | grep -v "^baseline-$DATE" | sort | tail -1)
if [ -n "$PREV" ]; then
  { echo ""; echo "=== 与上次对比 ($PREV) ==="; diff "$DIR/$PREV" "$LOG" || true; } >> "$LOG"
fi
cat "$LOG"
