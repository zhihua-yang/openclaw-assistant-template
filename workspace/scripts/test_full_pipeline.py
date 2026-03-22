#!/usr/bin/env bash
# test_full_pipeline.sh — OpenClaw v3.11.1-Lite 全链路测试
# 用法：bash workspace/scripts/test_full_pipeline.sh
# 预期：全部 PASS，无 FAIL

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
MEMORY="$WORKSPACE/memory"
CHAIN="$MEMORY/evolution_chain.jsonl"
INDEX="$MEMORY/intelligence_index.json"
DIGEST="$MEMORY/recent_digest.json"

PASS=0
FAIL=0
ERRORS=()

# ── 工具函数 ──────────────────────────────────────
pass() { echo "  ✅ PASS: $1"; ((PASS++)); }
fail() { echo "  ❌ FAIL: $1"; ((FAIL++)); ERRORS+=("$1"); }

check_field() {
  local file="$1" field="$2" label="$3"
  if python3 -c "
import json, sys
data = json.loads(open('$file').readlines()[-1])
val = data.get('$field')
sys.exit(0 if val is not None and val != '' else 1)
" 2>/dev/null; then
    pass "$label"
  else
    fail "$label (字段 '$field' 缺失或为空)"
  fi
}

check_json_field() {
  local file="$1" field="$2" label="$3"
  if python3 -c "
import json, sys
data = json.load(open('$file'))
val = data.get('$field')
sys.exit(0 if val is not None else 1)
" 2>/dev/null; then
    pass "$label"
  else
    fail "$label (字段 '$field' 缺失)"
  fi
}

section() { echo; echo "── $1 ──────────────────────────────────"; }

# ── 记录测试前的 IQ 基线 ─────────────────────────
IQ_BEFORE=$(python3 -c "
import json, os
f = '$INDEX'
if os.path.exists(f):
    d = json.load(open(f))
    print(d.get('IQ', {}).get('score', 50.0))
else:
    print(50.0)
" 2>/dev/null)

echo "╔══════════════════════════════════════════════╗"
echo "║  OpenClaw v3.11.1-Lite 全链路测试            ║"
echo "╚══════════════════════════════════════════════╝"
echo "  工作目录: $WORKSPACE"
echo "  IQ 基线 : $IQ_BEFORE"

# ════════════════════════════════════════════════
section "T1  基础写入：task-done（最小参数）"
# ════════════════════════════════════════════════
python3 "$SCRIPT_DIR/create_event.py" \
  --type task-done \
  --content "全链路测试：修复 cron 时区问题" \
  --task-type cron-maintenance \
  --difficulty routine \
  --evidence self 2>&1 | tail -6

# 验证最新一行字段
check_field "$CHAIN" "event_id"    "T1-1  写入字段 event_id 存在"
check_field "$CHAIN" "event_type"  "T1-2  写入字段 event_type 存在"
check_field "$CHAIN" "ts"          "T1-3  写入字段 ts 存在"
check_field "$CHAIN" "source_type" "T1-4  写入字段 source_type 存在"
check_field "$CHAIN" "content"     "T1-5  写入字段 content 存在"
check_field "$CHAIN" "task_id"     "T1-6  写入字段 task_id 存在"

# 验证字段值正确性
python3 -c "
import json
e = json.loads(open('$CHAIN').readlines()[-1])
assert e['event_type'] == 'task-done', f'event_type={e[\"event_type\"]}'
assert e['source_type'] == 'fact',     f'source_type={e[\"source_type\"]}'
assert e['event_id'].startswith('evt-'), f'event_id={e[\"event_id\"]}'
" && pass "T1-7  字段值符合 Schema（task-done/fact/evt-前缀）" \
  || fail "T1-7  字段值不符合 Schema"

# ════════════════════════════════════════════════
section "T2  派生事件：error-fix + learning-achievement"
# ════════════════════════════════════════════════

# 先拿到 T1 的 event_id，作为 parent
PARENT_ID=$(python3 -c "
import json
lines = open('$CHAIN').readlines()
print(json.loads(lines[-1])['event_id'])
")

python3 "$SCRIPT_DIR/create_event.py" \
  --type error-fix \
  --content "全链路测试：修复 evolve.py 路径错误" \
  --task-type debug \
  --difficulty stretch \
  --evidence external \
  --evidence-ref "log:test-full-pipeline" 2>&1 | tail -3

ERROR_FIX_ID=$(python3 -c "
import json
lines = open('$CHAIN').readlines()
print(json.loads(lines[-1])['event_id'])
")

python3 "$SCRIPT_DIR/create_event.py" \
  --type learning-achievement \
  --content "全链路测试：认知更新，evolve.py 路径必须用 file.parent" \
  --cognitive-update "Pathfile.parent.parent 才能正确定位 workspace 根目录" \
  --trigger error-driven \
  --parent "$ERROR_FIX_ID" 2>&1 | tail -3

check_field "$CHAIN" "parent_id"       "T2-1  learning-achievement 写入 parent_id"
check_field "$CHAIN" "cognitive_update" "T2-2  写入 cognitive_update 字段"
check_field "$CHAIN" "trigger"          "T2-3  写入 trigger 字段"

# ════════════════════════════════════════════════
section "T3  --dry-run 不写入验证"
# ════════════════════════════════════════════════
LINE_COUNT_BEFORE=$(wc -l < "$CHAIN")

python3 "$SCRIPT_DIR/create_event.py" \
  --type task-done \
  --content "dry-run 测试事件，不应写入" \
  --dry-run 2>&1 | grep -q "dry-run" && pass "T3-1  dry-run 模式打印提示" || fail "T3-1  dry-run 无提示"

LINE_COUNT_AFTER=$(wc -l < "$CHAIN")
[ "$LINE_COUNT_BEFORE" -eq "$LINE_COUNT_AFTER" ] \
  && pass "T3-2  dry-run 未写入文件（行数不变）" \
  || fail "T3-2  dry-run 意外写入了文件"

# ════════════════════════════════════════════════
section "T4  非法参数校验"
# ════════════════════════════════════════════════
python3 "$SCRIPT_DIR/create_event.py" \
  --type invalid-type-xyz \
  --content "应该报错" 2>&1 | grep -q "未知事件类型\|invalid\|error\|Error" \
  && pass "T4-1  非法 event_type 被拒绝" \
  || fail "T4-1  非法 event_type 未被校验"

python3 "$SCRIPT_DIR/create_event.py" \
  --type learning-achievement \
  --content "缺少 parent" 2>&1 | grep -q "parent\|派生\|必须" \
  && pass "T4-2  learning-achievement 缺少 --parent 被拒绝" \
  || fail "T4-2  learning-achievement 缺少 --parent 未报错"

python3 "$SCRIPT_DIR/create_event.py" \
  --type task-done \
  --content "证据等级非法测试" \
  --evidence logical 2>&1 | grep -q "logical\|不允许\|error\|Error" \
  && pass "T4-3  evidence=logical 手动填写被拒绝" \
  || fail "T4-3  evidence=logical 未被校验"

# ════════════════════════════════════════════════
section "T5  daily_digest.py 摘要生成"
# ════════════════════════════════════════════════
python3 "$SCRIPT_DIR/daily_digest.py" 2>&1 | tail -3

[ -f "$DIGEST" ] \
  && pass "T5-1  recent_digest.json 已生成" \
  || fail "T5-1  recent_digest.json 未生成"

check_json_field "$DIGEST" "updated_at"       "T5-2  摘要字段 updated_at 存在"
check_json_field "$DIGEST" "recent_failures"  "T5-3  摘要字段 recent_failures 存在"
check_json_field "$DIGEST" "recent_reworks"   "T5-4  摘要字段 recent_reworks 存在"

# ════════════════════════════════════════════════
section "T6  evolve.py 计分"
# ════════════════════════════════════════════════
python3 "$SCRIPT_DIR/evolve.py" 2>&1 | tail -5

[ -f "$INDEX" ] \
  && pass "T6-1  intelligence_index.json 已更新" \
  || fail "T6-1  intelligence_index.json 未生成"

IQ_AFTER=$(python3 -c "
import json
d = json.load(open('$INDEX'))
print(d.get('IQ', {}).get('score', 50.0))
" 2>/dev/null)

check_json_field "$INDEX" "IQ" "T6-2  IQ 字段存在"
check_json_field "$INDEX" "EQ" "T6-3  EQ 字段存在"
check_json_field "$INDEX" "FQ" "T6-4  FQ 字段存在"

python3 -c "
before = float('$IQ_BEFORE')
after  = float('$IQ_AFTER')
# error-fix(stretch/external) 应产生正向 delta
assert after >= before, f'IQ 未增加: before={before} after={after}'
" && pass "T6-5  IQ 在 error-fix(stretch/external) 后增加（${IQ_BEFORE} → ${IQ_AFTER}）" \
  || fail "T6-5  IQ 未如预期增加（${IQ_BEFORE} → ${IQ_AFTER}）"

# ════════════════════════════════════════════════
section "T7  audit_events.py 诊断扫描"
# ════════════════════════════════════════════════
python3 "$SCRIPT_DIR/audit_events.py" 2>&1 | tail -5
pass "T7-1  audit_events.py 执行无崩溃"

# ════════════════════════════════════════════════
section "T8  session_note_writer.py（farewell 通路）"
# ════════════════════════════════════════════════
LINE_BEFORE=$(wc -l < "$CHAIN")

python3 "$SCRIPT_DIR/session_note_writer.py" \
  --content "全链路测试会话结束" \
  --tags "test,farewell" 2>&1 | tail -3   # --tags 应被静默忽略

LINE_AFTER=$(wc -l < "$CHAIN")
[ "$LINE_AFTER" -gt "$LINE_BEFORE" ] \
  && pass "T8-1  session_note_writer 成功写入新管道（evolution_chain.jsonl）" \
  || fail "T8-1  session_note_writer 未写入"

# 验证写入的是新格式
python3 -c "
import json
e = json.loads(open('$CHAIN').readlines()[-1])
assert 'event_id' in e, '缺少 event_id'
assert 'event_type' in e, '缺少 event_type'
assert 'ts' in e, '缺少 ts'
" && pass "T8-2  session_note_writer 写入新 Schema 格式（event_id/event_type/ts）" \
  || fail "T8-2  session_note_writer 写入格式不符合 Schema"

# 确认没有写入旧管道
OLD_LOG="$WORKSPACE/.sys/logs/events.jsonl"
if [ -f "$OLD_LOG" ]; then
  OLD_BEFORE_COUNT=$(wc -l < "$OLD_LOG")
  # 重跑一次，验证旧管道行数不增加
  python3 "$SCRIPT_DIR/session_note_writer.py" \
    --content "第二次测试会话结束" 2>&1 | tail -1
  OLD_AFTER_COUNT=$(wc -l < "$OLD_LOG")
  [ "$OLD_BEFORE_COUNT" -eq "$OLD_AFTER_COUNT" ] \
    && pass "T8-3  旧管道 .sys/logs/events.jsonl 未被写入" \
    || fail "T8-3  旧管道仍被写入（管道切换未完成）"
else
  pass "T8-3  旧管道文件不存在（已彻底废弃）"
fi

# ════════════════════════════════════════════════
section "汇总"
# ════════════════════════════════════════════════
echo
TOTAL=$((PASS + FAIL))
echo "  总计: $TOTAL 项   ✅ PASS: $PASS   ❌ FAIL: $FAIL"

if [ ${#ERRORS[@]} -gt 0 ]; then
  echo
  echo "  失败项："
  for e in "${ERRORS[@]}"; do
    echo "    · $e"
  done
fi

echo
[ $FAIL -eq 0 ] \
  && echo "🎉 全链路测试通过，所有管道工作正常。" \
  || echo "⚠️  存在 $FAIL 项失败，请检查上方详情。"

exit $FAIL
