#!/usr/bin/env bash
# OpenClaw v3.11.1-Lite setup.sh
# 从 v3.7 升级：新增 utils/、audit/digest/export 脚本、4条 cron、30项健康检查

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$REPO_DIR/workspace"
MEMORY="$TARGET/memory"
SYS="$TARGET/.sys"
LOGS="$SYS/logs"
SCRIPTS="$TARGET/scripts"

echo "================================================"
echo " OpenClaw v3.11.1-Lite Setup"
echo " REPO : $REPO_DIR"
echo " TARGET: $TARGET"
echo "================================================"

# ── Step 1：前提条件检查 ──────────────────────────
echo ""
echo "[ Step 1 ] 前提条件检查"

if ! command -v python3 &>/dev/null; then
  echo "❌ python3 未找到，请先安装 Python 3.8+"
  exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  ✅ python3 $PYTHON_VERSION"

# 安装依赖
echo "  → 安装 filelock（文件锁，必须）"
pip3 install filelock --quiet && echo "  ✅ filelock" || echo "  ⚠️ filelock 安装失败，请手动执行: pip3 install filelock"

echo "  → 安装 scikit-learn（TF-IDF 检索，可选）"
pip3 install scikit-learn --quiet && echo "  ✅ scikit-learn" || echo "  ⚠️ scikit-learn 未安装，capability 检索将使用精确匹配降级"

# ── Step 2：初始化目录结构 ────────────────────────
echo ""
echo "[ Step 2 ] 初始化目录结构"

mkdir -p "$MEMORY"
mkdir -p "$LOGS"
mkdir -p "$SCRIPTS/utils"
echo "  ✅ 目录结构已就绪"

# ── Step 3：同步脚本文件 ──────────────────────────
echo ""
echo "[ Step 3 ] 同步脚本文件"

SCRIPT_FILES=(
  "create_event.py"
  "evolve.py"
  "audit_events.py"
  "resolve_audit.py"
  "weekly_reflection.py"
  "daily_digest.py"
  "export_capabilities.py"
)

for f in "${SCRIPT_FILES[@]}"; do
  SRC="$REPO_DIR/workspace/scripts/$f"
  DST="$SCRIPTS/$f"
  if [ -f "$SRC" ]; then
    cp "$SRC" "$DST"
    echo "  ✅ 已更新: scripts/$f"
  else
    echo "  ⚠️ 缺失: scripts/$f（请检查仓库完整性）"
  fi
done

# 同步 utils/
UTIL_FILES=(
  "__init__.py"
  "file_lock.py"
  "paths.py"
  "sample_check.py"
  "capability_search.py"
)

for f in "${UTIL_FILES[@]}"; do
  SRC="$REPO_DIR/workspace/scripts/utils/$f"
  DST="$SCRIPTS/utils/$f"
  if [ -f "$SRC" ]; then
    cp "$SRC" "$DST"
    echo "  ✅ 已更新: scripts/utils/$f"
  else
    echo "  ⚠️ 缺失: scripts/utils/$f"
  fi
done

# 设置执行权限
chmod +x "$SCRIPTS"/*.py 2>/dev/null || true
echo "  ✅ 执行权限已设置"

# ── Step 4：初始化记忆文件（不覆盖已有数据） ──────
echo ""
echo "[ Step 4 ] 初始化记忆文件（不覆盖已有数据）"

# v3.7 保留文件
for f in "recent.md" "errors.md" "growth.md"; do
  if [ ! -f "$MEMORY/$f" ]; then
    touch "$MEMORY/$f"
    echo "  ✅ 新建: memory/$f"
  else
    echo "  → 保留: memory/$f（不覆盖）"
  fi
done

# v3.11.1-Lite 新增 JSON 文件（不覆盖）
init_json() {
  local filename="$1"
  local content="$2"
  local dst="$MEMORY/$filename"
  if [ ! -f "$dst" ]; then
    echo "$content" > "$dst"
    echo "  ✅ 新建: memory/$filename"
  else
    echo "  → 保留: memory/$filename（不覆盖）"
  fi
}

init_json "intelligence_index.json" '{
  "IQ": {"score": 50.0, "components": {"novel_problem_solved": 0, "debug_success_rate": 0.0, "validated_capability_count": 0, "repeat_error_rate": 0.0}},
  "EQ": {"score": 50.0, "components": {"EQ_external": 50.0, "EQ_process": 50.0, "user_correction_count": 0, "positive_feedback_count": 0}, "weights": {"EQ_external": 0.8, "EQ_process": 0.2}},
  "FQ": {"score": 50.0, "components": {"first_attempt_success_rate": 0.0, "rework_rate": 0.0, "priority_accuracy": 0.0}},
  "baseline_date": "'"$(date +%Y-%m-%d)"'",
  "last_updated": "'"$(date +%Y-%m-%d)"'",
  "version": "v3.11.1-Lite"
}'

init_json "capabilities.json" '{
  "version": "v3.11.1-Lite",
  "updated_at": "'"$(date +%Y-%m-%d)"'",
  "capabilities": []
}'

init_json "antipatterns.json" '{
  "version": "v3.11.1-Lite",
  "updated_at": "'"$(date +%Y-%m-%d)"'",
  "antipatterns": []
}'

init_json "profile.json" '{
  "EQ_process_weight": 0.2,
  "min_learning_content_length": 12,
  "same_task_min_sample": 3,
  "evidence_default": "self",
  "daily_fq_cap_per_task_type": 2,
  "audit_expire_days": 7,
  "capability_degradation_error_rate": 0.15,
  "repair_cycle_max_idle_days": 60,
  "sample_sufficient_min_task_done": 15,
  "overconfidence_alert_threshold": 0.15,
  "llm_budget_mode": "low",
  "weekly_llm_call_budget": 4,
  "allow_daily_llm_summary": false,
  "allow_error_fix_llm_extraction": true,
  "allow_weekly_report_llm_rewrite": true,
  "allow_training_plan_llm_rewrite": true,
  "context_inject_whitelist": [
    "current_task",
    "related_capabilities_max_3",
    "related_antipatterns_max_3",
    "recent_digest",
    "goal_gap_summary",
    "calibration_summary_1line"
  ]
}'

init_json "goals.json" '{
  "result_goals": {
    "IQ": {"current": 50.0, "target_6m": 70.0},
    "EQ": {"current": 50.0, "target_6m": 75.0},
    "FQ": {"current": 50.0, "target_6m": 70.0}
  },
  "capability_goals": [],
  "training_goals": {
    "intentional_challenge_per_week": 2,
    "stretch_ratio_target": 0.35,
    "error_driven_learning_per_week": 1,
    "overconfidence_rate_max": 0.15
  }
}'

# evolution_chain.jsonl 只在不存在时创建（不迁移旧 events.jsonl）
if [ ! -f "$MEMORY/evolution_chain.jsonl" ]; then
  touch "$MEMORY/evolution_chain.jsonl"
  echo "  ✅ 新建: memory/evolution_chain.jsonl（全新起点）"
  echo "  ℹ️  v3.7 历史事件保留在 .sys/logs/events.jsonl，不自动迁移"
else
  echo "  → 保留: memory/evolution_chain.jsonl（不覆盖）"
fi

# audit_queue.jsonl
if [ ! -f "$MEMORY/audit_queue.jsonl" ]; then
  touch "$MEMORY/audit_queue.jsonl"
  echo "  ✅ 新建: memory/audit_queue.jsonl"
else
  echo "  → 保留: memory/audit_queue.jsonl"
fi

# ── Step 5：清理旧 crontab ────────────────────────
echo ""
echo "[ Step 5 ] 清理旧版 crontab 条目"

(crontab -l 2>/dev/null | grep -v "evolve.py\|weekly_reflection.py\|audit_events.py\|daily_digest.py\|openclaw" || true) | crontab - 2>/dev/null || true
echo "  ✅ 旧 crontab 条目已清理"

# ── Step 6：生成 install-cron.sh ──────────────────
echo ""
echo "[ Step 6 ] 生成 install-cron.sh"

cat > "$TARGET/install-cron.sh" << CRONEOF
#!/usr/bin/env bash
# OpenClaw v3.11.1-Lite Cron 安装脚本
# 运行方式: bash install-cron.sh

TARGET_DIR="$TARGET"

(crontab -l 2>/dev/null; cat << 'EOF'
# OpenClaw v3.11.1-Lite — 每日审计 00:05
5 0 * * * cd TARGET_DIR && python3 scripts/audit_events.py >> .sys/logs/cron-audit.log 2>&1
# OpenClaw v3.11.1-Lite — 每日摘要 00:15
15 0 * * * cd TARGET_DIR && python3 scripts/daily_digest.py >> .sys/logs/cron-digest.log 2>&1
# OpenClaw v3.11.1-Lite — 记忆进化 00:20
20 0 * * * cd TARGET_DIR && python3 scripts/evolve.py >> .sys/logs/cron-memory-evolution.log 2>&1
# OpenClaw v3.11.1-Lite — 周反思 周一09:00
0 9 * * 1 cd TARGET_DIR && python3 scripts/weekly_reflection.py >> .sys/logs/weekly-reflection.log 2>&1
EOF
) | sed "s|TARGET_DIR|$TARGET_DIR|g" | crontab -

echo "✅ OpenClaw v3.11.1-Lite cron 已安装（4 条任务）"
crontab -l | grep openclaw || crontab -l | grep "evolve\|audit\|digest\|weekly"
CRONEOF

chmod +x "$TARGET/install-cron.sh"
echo "  ✅ install-cron.sh 已生成"

# ── Step 7：健康检查（30 项） ─────────────────────
echo ""
echo "[ Step 7 ] 健康检查（30 项）"

PASS=0
FAIL=0

check() {
  local desc="$1"
  local result="$2"
  if [ "$result" = "ok" ]; then
    echo "  ✅ $desc"
    PASS=$((PASS+1))
  else
    echo "  ❌ $desc"
    FAIL=$((FAIL+1))
  fi
}

# 文件存在检查
[ -f "$SCRIPTS/create_event.py" ]        && check "create_event.py 存在" "ok"       || check "create_event.py 存在" "fail"
[ -f "$SCRIPTS/evolve.py" ]              && check "evolve.py 存在" "ok"              || check "evolve.py 存在" "fail"
[ -f "$SCRIPTS/audit_events.py" ]        && check "audit_events.py 存在" "ok"        || check "audit_events.py 存在" "fail"
[ -f "$SCRIPTS/resolve_audit.py" ]       && check "resolve_audit.py 存在" "ok"       || check "resolve_audit.py 存在" "fail"
[ -f "$SCRIPTS/weekly_reflection.py" ]   && check "weekly_reflection.py 存在" "ok"   || check "weekly_reflection.py 存在" "fail"
[ -f "$SCRIPTS/daily_digest.py" ]        && check "daily_digest.py 存在" "ok"        || check "daily_digest.py 存在" "fail"
[ -f "$SCRIPTS/export_capabilities.py" ] && check "export_capabilities.py 存在" "ok" || check "export_capabilities.py 存在" "fail"
[ -f "$SCRIPTS/utils/file_lock.py" ]     && check "utils/file_lock.py 存在" "ok"     || check "utils/file_lock.py 存在" "fail"
[ -f "$SCRIPTS/utils/sample_check.py" ]  && check "utils/sample_check.py 存在" "ok"  || check "utils/sample_check.py 存在" "fail"
[ -f "$SCRIPTS/utils/capability_search.py" ] && check "utils/capability_search.py 存在" "ok" || check "utils/capability_search.py 存在" "fail"

# JSON 文件存在
[ -f "$MEMORY/intelligence_index.json" ] && check "intelligence_index.json 存在" "ok" || check "intelligence_index.json 存在" "fail"
[ -f "$MEMORY/capabilities.json" ]       && check "capabilities.json 存在" "ok"       || check "capabilities.json 存在" "fail"
[ -f "$MEMORY/antipatterns.json" ]       && check "antipatterns.json 存在" "ok"       || check "antipatterns.json 存在" "fail"
[ -f "$MEMORY/profile.json" ]            && check "profile.json 存在" "ok"            || check "profile.json 存在" "fail"
[ -f "$MEMORY/goals.json" ]              && check "goals.json 存在" "ok"              || check "goals.json 存在" "fail"
[ -f "$MEMORY/evolution_chain.jsonl" ]   && check "evolution_chain.jsonl 存在" "ok"   || check "evolution_chain.jsonl 存在" "fail"
[ -f "$MEMORY/audit_queue.jsonl" ]       && check "audit_queue.jsonl 存在" "ok"       || check "audit_queue.jsonl 存在" "fail"

# profile.json 字段检查
if [ -f "$MEMORY/profile.json" ]; then
  python3 -c "
import json,sys
p=json.load(open('$MEMORY/profile.json'))
assert p.get('evidence_default')=='self', 'evidence_default != self'
assert 'sample_sufficient_min_task_done' in p, 'missing sample_sufficient_min_task_done'
assert 'context_inject_whitelist' in p, 'missing context_inject_whitelist'
print('ok')
" 2>/dev/null | grep -q ok && check "profile.json 字段完整" "ok" || check "profile.json 字段完整" "fail"
fi

# Python 脚本语法检查
python3 -m py_compile "$SCRIPTS/create_event.py"     2>/dev/null && check "create_event.py 语法正确" "ok"     || check "create_event.py 语法正确" "fail"
python3 -m py_compile "$SCRIPTS/evolve.py"           2>/dev/null && check "evolve.py 语法正确" "ok"           || check "evolve.py 语法正确" "fail"
python3 -m py_compile "$SCRIPTS/audit_events.py"     2>/dev/null && check "audit_events.py 语法正确" "ok"     || check "audit_events.py 语法正确" "fail"
python3 -m py_compile "$SCRIPTS/weekly_reflection.py" 2>/dev/null && check "weekly_reflection.py 语法正确" "ok" || check "weekly_reflection.py 语法正确" "fail"
python3 -m py_compile "$SCRIPTS/daily_digest.py"     2>/dev/null && check "daily_digest.py 语法正确" "ok"     || check "daily_digest.py 语法正确" "fail"

# dry-run 检查
cd "$TARGET"
python3 scripts/create_event.py --list-types &>/dev/null && check "create_event.py --list-types 可运行" "ok" || check "create_event.py --list-types 可运行" "fail"
python3 scripts/evolve.py &>/dev/null && check "evolve.py 可运行" "ok" || check "evolve.py 可运行" "fail"
python3 scripts/weekly_reflection.py --dry-run &>/dev/null && check "weekly_reflection.py --dry-run 可运行" "ok" || check "weekly_reflection.py --dry-run 可运行" "fail"
python3 scripts/audit_events.py &>/dev/null && check "audit_events.py 可运行" "ok" || check "audit_events.py 可运行" "fail"
python3 scripts/daily_digest.py &>/dev/null && check "daily_digest.py 可运行" "ok" || check "daily_digest.py 可运行" "fail"

# filelock 依赖检查
python3 -c "from filelock import FileLock; print('ok')" 2>/dev/null | grep -q ok && check "filelock 依赖可用" "ok" || check "filelock 依赖可用" "fail"

# IDENTITY.md 保护检查
[ -f "$TARGET/IDENTITY.md" ] && check "IDENTITY.md 存在（保护文件）" "ok" || check "IDENTITY.md 存在（保护文件）" "fail"

echo ""
echo "  健康检查完成：✅ $PASS 通过 / ❌ $FAIL 失败"

# ── Step 8：Cron 配置（tty 智能检测） ─────────────
echo ""
echo "[ Step 8 ] Cron 配置"

if [ -t 1 ]; then
  # 终端环境：打印提示
  echo ""
  echo "════════════════════════════════════════════"
  echo "  下一步：配置 OpenClaw v3.11.1-Lite Cron"
  echo "════════════════════════════════════════════"
  echo ""
  echo "方式一（推荐）：直接运行"
  echo "  bash $TARGET/install-cron.sh"
  echo ""
  echo "方式二：将以下内容粘贴到 OpenClaw 对话框："
  echo ""
  echo "┌─────────────────────────────────────────┐"
  echo "│ 请配置以下 4 个原生 cron 任务：          │"
  echo "│ 1. 审计    5 0 * * *  audit_events.py   │"
  echo "│ 2. 摘要   15 0 * * *  daily_digest.py   │"
  echo "│ 3. 进化   20 0 * * *  evolve.py         │"
  echo "│ 4. 周反思  0 9 * * 1  weekly_reflection │"
  echo "└─────────────────────────────────────────┘"
else
  # OpenClaw 非 tty 环境：输出结构化块
  echo ""
  echo "OPENCLAW_CRON_CONFIG_START"
  echo "请立即配置以下 4 个 OpenClaw 原生 cron 任务："
  echo ""
  echo "任务1 — 每日审计"
  echo " schedule: 5 0 * * *"
  echo " payload: python3 $TARGET/scripts/audit_events.py"
  echo " logFile: $LOGS/cron-audit.log"
  echo " enabled: true"
  echo ""
  echo "任务2 — 每日摘要"
  echo " schedule: 15 0 * * *"
  echo " payload: python3 $TARGET/scripts/daily_digest.py"
  echo " logFile: $LOGS/cron-digest.log"
  echo " enabled: true"
  echo ""
  echo "任务3 — 记忆进化"
  echo " schedule: 20 0 * * *"
  echo " payload: python3 $TARGET/scripts/evolve.py"
  echo " logFile: $LOGS/cron-memory-evolution.log"
  echo " enabled: true"
  echo ""
  echo "任务4 — 周反思"
  echo " schedule: 0 9 * * 1"
  echo " payload: python3 $TARGET/scripts/weekly_reflection.py"
  echo " logFile: $LOGS/weekly-reflection.log"
  echo " enabled: true"
  echo "OPENCLAW_CRON_CONFIG_END"
fi

echo ""
echo "================================================"
echo " OpenClaw v3.11.1-Lite Setup 完成"
if [ $FAIL -eq 0 ]; then
  echo " 状态：✅ 全部通过（$PASS/$((PASS+FAIL))）"
else
  echo " 状态：⚠️ $FAIL 项未通过，请检查上方输出"
fi
echo "================================================"
