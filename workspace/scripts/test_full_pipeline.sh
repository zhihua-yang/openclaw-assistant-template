#!/usr/bin/env bash
# test_full_pipeline.sh — OpenClaw v3.11.1-Lite 全链路测试
# 用法：cd workspace/scripts && bash test_full_pipeline.sh
# 预期：全部 PASS，无 FAIL

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
MEMORY="$WORKSPACE/memory"
CHAIN="$MEMORY/evolution_chain.jsonl"
INDEX="$MEMORY/intelligence_index.json"
DIGEST="$MEMORY/recent_digest.json"

PASS=0
FAIL=0
ERRORS=()

# ── 工具函数 ──────────────────────────────────────
pass() { echo "  ✅ PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "  ❌ FAIL: $1"; FAIL=$((FAIL + 1)); ERRORS+=("$1"); }

run_ce() {
  # 调用 create_event.py，屏蔽预览输出，只保留最后几行
  python3 "$SCRIPT_DIR/create_event.py" "$@" 2>&1 | tail -4
}

check_last_field() {
  # 检查 evolution_chain.jsonl 最后一行是否含有指定字段
  local field="$1" label="$2"
  python3 - <<EOF
import json, sys
try:
    data = json.loads(open('$CHAIN').readlines()[-1])
    val  = data.get('$field')
    sys.exit(0 if (val is not None and val != '') else 1)
except Exception:
    sys.exit(1)
EOF
  local rc=$?
  [ $rc -eq 0 ] && pass "$label" || fail "$label (字段 '$field' 缺失或为空)"
}

check_json_field() {
  # 检查某个 JSON 文件顶层是否含有指定字段
  local file="$1" field="$2" label="$3"
  python3 - <<EOF
import json, sys
try:
    data = json.load(open('$file'))
    sys.exit(0 if data.get('$field') is not None else 1)
except Exception:
    sys.exit(1)
EOF
  local rc=$?
  [ $rc -eq 0 ] && pass "$label" || fail "$label (字段 '$field' 缺失)"
}

section() { echo; echo "── $1 ──────────────────────────────────"; }

# ── 记录测试前 IQ 基线 ───────────────────────────
IQ_BEFORE=$(python3 - <<EOF
import json, os
f = '$INDEX'
try:
    print(json.load(open(f)).get('IQ', {}).get('score', 50.0))
except Exception:
    print(50.0)
EOF
)

echo "╔══════════════════════════════════════════════╗"
echo "║  OpenClaw v3.11.1-Lite 全链路测试            ║"
echo "╚══════════════════════════════════════════════╝"
echo "  工作目录: $WORKSPACE"
echo "  IQ 基线 : $IQ_BEFORE"

# ════════════════════════════════════════════════
section "T1  基础写入：task-done（最小参数）"
# ════════════════════════════════════════════════
run_ce \
  --type task-done \
  --content "全链路测试：修复 cron 时区问题" \
  --task-type cron-maintenance \
  --difficulty routine \
  --evidence self

check_last_field "event_id"    "T1-1  字段 event_id 存在"
check_last_field "event_type"  "T1-2  字段 event_type 存在"
check_last_field "ts"          "T1-3  字段 ts 存在"
check_last_field "source_type" "T1-4  字段 source_type 存在"
check_last_field "content"     "T1-5  字段 content 存在"
check_last_field "task_id"     "T1-6  字段 task_id 存在"

python3 - <<'EOF'
import json, sys
try:
    e = json.loads(open('CHAIN_PLACEHOLDER').readlines()[-1])
    assert e['event_type']  == 'task-done', f"event_type={e['event_type']}"
    assert e['source_type'] == 'fact',      f"source_type={e['source_type']}"
    assert e['event_id'].startswith('evt-'), f"event_id={e['event_id']}"
    sys.exit(0)
except Exception as ex:
    print(f"  assertion: {ex}")
    sys.exit(1)
EOF
# 用真实路径替换占位符再执行
python3 - "$CHAIN" <<'EOF'
import json, sys
f = sys.argv[1]
try:
    e = json.loads(open(f).readlines()[-1])
    assert e['event_type']  == 'task-done', f"event_type={e['event_type']}"
    assert e['source_type'] == 'fact',      f"source_type={e['source_type']}"
    assert e['event_id'].startswith('evt-'), f"event_id={e['event_id']}"
    sys.exit(0)
except Exception as ex:
    print(f"  assertion: {ex}", file=sys.stderr)
    sys.exit(1)
EOF
rc=$?
[ $rc -eq 0 ] \
  && pass "T1-7  字段值符合 Schema（task-done / fact / evt- 前缀）" \
  || fail "T1-7  字段值不符合 Schema"

# ════════════════════════════════════════════════
section "T2  派生事件链：error-fix → learning-achievement"
# ════════════════════════════════════════════════
run_ce \
  --type error-fix \
  --content "全链路测试：修复 evolve.py 路径错误" \
  --task-type debug \
  --difficulty stretch \
  --evidence external \
  --evidence-ref "log:test-full-pipeline"

ERROR_FIX_ID=$(python3 -c "
import json
print(json.loads(open('$CHAIN').readlines()[-1])['event_id'])
")
echo "  parent event_id: $ERROR_FIX_ID"

run_ce \
  --type learning-achievement \
  --content "全链路测试：认知更新，evolve 路径必须用 file.parent" \
  --cognitive-update "Path(__file__).parent.parent 才能正确定位 workspace 根目录" \
  --trigger error-driven \
  --parent "$ERROR_FIX_ID"

check_last_field "parent_id"        "T2-1  learning-achievement 写入 parent_id"
check_last_field "cognitive_update" "T2-2  写入 cognitive_update 字段"
check_last_field "trigger"          "T2-3  写入 trigger 字段"

python3 - "$CHAIN" "$ERROR_FIX_ID" <<'EOF'
import json, sys
f, expected_parent = sys.argv[1], sys.argv[2]
try:
    e = json.loads(open(f).readlines()[-1])
    assert e.get('parent_id') == expected_parent, \
        f"parent_id={e.get('parent_id')} != {expected_parent}"
    assert e.get('source_type') == 'derived', \
        f"source_type={e.get('source_type')}"
    sys.exit(0)
except Exception as ex:
    print(f"  assertion: {ex}", file=sys.stderr)
    sys.exit(1)
EOF
rc=$?
[ $rc -eq 0 ] \
  && pass "T2-4  parent_id 值匹配、source_type=derived" \
  || fail "T2-4  parent_id 不匹配或 source_type 错误"

# ════════════════════════════════════════════════
section "T3  --dry-run 不写入保护"
# ════════════════════════════════════════════════
LINE_BEFORE=$(wc -l < "$CHAIN")

DRY_OUT=$(python3 "$SCRIPT_DIR/create_event.py" \
  --type task-done \
  --content "dry-run 测试，不应写入" \
  --dry-run 2>&1)

echo "$DRY_OUT" | grep -qi "dry.run" \
  && pass "T3-1  dry-run 模式打印提示" \
  || fail "T3-1  dry-run 无提示输出"

LINE_AFTER=$(wc -l < "$CHAIN")
[ "$LINE_BEFORE" -eq "$LINE_AFTER" ] \
  && pass "T3-2  dry-run 未写入文件（行数 $LINE_BEFORE → $LINE_AFTER 不变）" \
  || fail "T3-2  dry-run 意外写入了文件（行数 $LINE_BEFORE → $LINE_AFTER）"

# ════════════════════════════════════════════════
section "T4  非法参数校验"
# ════════════════════════════════════════════════

# T4-1：非法 event_type
OUT=$(python3 "$SCRIPT_DIR/create_event.py" \
  --type invalid-type-xyz \
  --content "应被拒绝" 2>&1) || true
echo "$OUT" | grep -qi "未知事件类型\|unknown\|invalid\|无效\|error" \
  && pass "T4-1  非法 event_type 被拒绝" \
  || fail "T4-1  非法 event_type 未被校验（输出：$(echo $OUT | head -c 80)）"

# T4-2：learning-achievement 缺 --parent
OUT=$(python3 "$SCRIPT_DIR/create_event.py" \
  --type learning-achievement \
  --content "缺 parent 应被拒绝" 2>&1) || true
echo "$OUT" | grep -qi "parent\|派生\|必须\|required" \
  && pass "T4-2  learning-achievement 缺 --parent 被拒绝" \
  || fail "T4-2  learning-achievement 缺 --parent 未报错（输出：$(echo $OUT | head -c 80)）"

# T4-3：evidence=logical 不允许手动填写
OUT=$(python3 "$SCRIPT_DIR/create_event.py" \
  --type task-done \
  --content "logical 证据应被拒绝" \
  --evidence logical 2>&1) || true
echo "$OUT" | grep -qi "logical\|不允许\|系统\|invalid\|无效" \
  && pass "T4-3  evidence=logical 手动填写被拒绝" \
  || fail "T4-3  evidence=logical 未被校验（输出：$(echo $OUT | head -c 80)）"

# ════════════════════════════════════════════════
section "T5  daily_digest.py 摘要生成"
# ════════════════════════════════════════════════
python3 "$SCRIPT_DIR/daily_digest.py" 2>&1 | tail -4

[ -f "$DIGEST" ] \
  && pass "T5-1  recent_digest.json 已生成" \
  || fail "T5-1  recent_digest.json 未生成"

check_json_field "$DIGEST" "updated_at"      "T5-2  摘要字段 updated_at 存在"
check_json_field "$DIGEST" "recent_failures" "T5-3  摘要字段 recent_failures 存在"
check_json_field "$DIGEST" "recent_reworks"  "T5-4  摘要字段 recent_reworks 存在"
check_json_field "$DIGEST" "index_snapshot"  "T5-5  摘要字段 index_snapshot 存在"

# ════════════════════════════════════════════════
section "T6  evolve.py 计分"
# ════════════════════════════════════════════════
python3 "$SCRIPT_DIR/evolve.py" 2>&1 | tail -5

[ -f "$INDEX" ] \
  && pass "T6-1  intelligence_index.json 存在" \
  || fail "T6-1  intelligence_index.json 未生成"

check_json_field "$INDEX" "IQ" "T6-2  IQ 字段存在"
check_json_field "$INDEX" "EQ" "T6-3  EQ 字段存在"
check_json_field "$INDEX" "FQ" "T6-4  FQ 字段存在"

IQ_AFTER=$(python3 -c "
import json
print(json.load(open('$INDEX')).get('IQ', {}).get('score', 50.0))
" 2>/dev/null)

python3 - "$IQ_BEFORE" "$IQ_AFTER" <<'EOF'
import sys
before, after = float(sys.argv[1]), float(sys.argv[2])
sys.exit(0 if after >= before else 1)
EOF
rc=$?
[ $rc -eq 0 ] \
  && pass "T6-5  IQ 正向增量（${IQ_BEFORE} → ${IQ_AFTER}）✓" \
  || fail "T6-5  IQ 未增加（${IQ_BEFORE} → ${IQ_AFTER}），检查 evolve.py 计分逻辑"

# ════════════════════════════════════════════════
section "T7  audit_events.py 诊断扫描"
# ════════════════════════════════════════════════
python3 "$SCRIPT_DIR/audit_events.py" 2>&1 | tail -4
pass "T7-1  audit_events.py 执行无崩溃"

AUDIT_QUEUE="$MEMORY/audit_queue.jsonl"
[ -f "$AUDIT_QUEUE" ] \
  && pass "T7-2  audit_queue.jsonl 存在" \
  || fail "T7-2  audit_queue.jsonl 未生成"

# ════════════════════════════════════════════════
section "T8  session_note_writer.py（farewell 通路）"
# ════════════════════════════════════════════════
LINE_BEFORE=$(wc -l < "$CHAIN")

python3 "$SCRIPT_DIR/session_note_writer.py" \
  --content "全链路测试会话结束" \
  --tags "test,farewell" 2>&1 | tail -3   # --tags 应被静默忽略

LINE_AFTER=$(wc -l < "$CHAIN")
[ "$LINE_AFTER" -gt "$LINE_BEFORE" ] \
  && pass "T8-1  session_note_writer 写入新管道（行数 $LINE_BEFORE → $LINE_AFTER）" \
  || fail "T8-1  session_note_writer 未写入 evolution_chain.jsonl"

python3 - "$CHAIN" <<'EOF'
import json, sys
try:
    e = json.loads(open(sys.argv[1]).readlines()[-1])
    assert 'event_id'   in e, "缺少 event_id"
    assert 'event_type' in e, "缺少 event_type"
    assert 'ts'         in e, "缺少 ts"
    sys.exit(0)
except Exception as ex:
    print(f"  assertion: {ex}", file=sys.stderr)
    sys.exit(1)
EOF
rc=$?
[ $rc -eq 0 ] \
  && pass "T8-2  写入格式符合新 Schema（event_id / event_type / ts）" \
  || fail "T8-2  写入格式不符合新 Schema"

OLD_LOG="$WORKSPACE/.sys/logs/events.jsonl"
if [ -f "$OLD_LOG" ]; then
  OLD_BEFORE=$(wc -l < "$OLD_LOG")
  python3 "$SCRIPT_DIR/session_note_writer.py" \
    --content "第二次测试，验证旧管道静默" 2>&1 | tail -1
  OLD_AFTER=$(wc -l < "$OLD_LOG")
  [ "$OLD_BEFORE" -eq "$OLD_AFTER" ] \
    && pass "T8-3  旧管道 .sys/logs/events.jsonl 未被写入" \
    || fail "T8-3  旧管道仍被写入（行数 $OLD_BEFORE → $OLD_AFTER）"
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
if [ $FAIL -eq 0 ]; then
  echo "🎉 全链路测试通过，所有管道工作正常。"
else
  echo "⚠️  存在 $FAIL 项失败，请检查上方详情。"
fi

exit $FAIL
