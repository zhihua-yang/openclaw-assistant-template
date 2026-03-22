#!/usr/bin/env bash
# OpenClaw v3.11.1-Lite setup.sh
# 支持两种用法：
#   用法1（全新实例）: bash setup.sh
#                     → workspace 目录在仓库内
#   用法2（升级旧实例）: bash setup.sh --target /root/.openclaw/workspace
#                     → 直接升级指定工作区，脚本文件复制过去

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── 解析参数 ──────────────────────────────────────
TARGET_WORKSPACE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET_WORKSPACE="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

# 判断工作区：有 --target 则用指定路径，否则用仓库内的 workspace/
if [ -n "$TARGET_WORKSPACE" ]; then
  WORKSPACE="$TARGET_WORKSPACE"
  COPY_MODE=true
  echo "  模式：升级已有工作区 → $WORKSPACE"
else
  WORKSPACE="$REPO_DIR/workspace"
  COPY_MODE=false
  echo "  模式：原地初始化（全新实例）→ $WORKSPACE"
fi

MEMORY="$WORKSPACE/memory"
SYS="$WORKSPACE/.sys"
LOGS="$SYS/logs"
SCRIPTS="$WORKSPACE/scripts"
UTILS="$SCRIPTS/utils"

echo "================================================"
echo " OpenClaw v3.11.1-Lite Setup"
echo " REPO     : $REPO_DIR"
echo " WORKSPACE: $WORKSPACE"
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

pip3 install filelock --quiet    && echo "  ✅ filelock"    || echo "  ⚠️ filelock 安装失败，请手动: pip3 install filelock"
pip3 install scikit-learn --quiet && echo "  ✅ scikit-learn" || echo "  ⚠️ scikit-learn 未安装，检索降级为精确匹配"

# ── Step 2：初始化目录结构 ────────────────────────
echo ""
echo "[ Step 2 ] 初始化目录结构"

mkdir -p "$MEMORY/archive"
mkdir -p "$LOGS"
mkdir -p "$UTILS"
echo "  ✅ 目录结构已就绪"

# ── Step 3：同步脚本文件 ──────────────────────────
echo ""
echo "[ Step 3 ] 同步脚本文件"

if [ "$COPY_MODE" = true ]; then
  # 升级模式：从仓库复制到目标工作区
  SRC_SCRIPTS="$REPO_DIR/workspace/scripts"

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
    if [ -f "$SRC_SCRIPTS/$f" ]; then
      cp "$SRC_SCRIPTS/$f" "$SCRIPTS/$f"
      echo "  ✅ 已更新: scripts/$f"
    else
      echo "  ❌ 源文件缺失: $SRC_SCRIPTS/$f"
    fi
  done

  UTIL_FILES=("__init__.py" "file_lock.py" "paths.py" "sample_check.py" "capability_search.py")
  for f in "${UTIL_FILES[@]}"; do
    if [ -f "$SRC_SCRIPTS/utils/$f" ]; then
      cp "$SRC_SCRIPTS/utils/$f" "$UTILS/$f"
      echo "  ✅ 已更新: scripts/utils/$f"
    else
      echo "  ❌ 源文件缺失: $SRC_SCRIPTS/utils/$f"
    fi
  done

  # 同步 AGENTS.md（覆盖）
  if [ -f "$REPO_DIR/workspace/AGENTS.md" ]; then
    cp "$REPO_DIR/workspace/AGENTS.md" "$WORKSPACE/AGENTS.md"
    echo "  ✅ 已更新: AGENTS.md"
  fi

  # IDENTITY.md 保护，不覆盖
  if [ -f "$WORKSPACE/IDENTITY.md" ]; then
    echo "  → 保留: IDENTITY.md（保护文件，不覆盖）"
  else
    [ -f "$REPO_DIR/workspace/IDENTITY.md" ] && cp "$REPO_DIR/workspace/IDENTITY.md" "$WORKSPACE/IDENTITY.md"
    echo "  ✅ 新建: IDENTITY.md"
  fi

else
  # 全新模式：验证文件完整性
  REQUIRED=(
    "create_event.py" "evolve.py" "audit_events.py" "resolve_audit.py"
    "weekly_reflection.py" "daily_digest.py" "export_capabilities.py"
  )
  for f in "${REQUIRED[@]}"; do
    [ -f "$SCRIPTS/$f" ] && echo "  ✅ scripts/$f" || echo "  ❌ scripts/$f 缺失（请重新 clone）"
  done
  for f in "__init__.py" "file_lock.py" "paths.py" "sample_check.py" "capability_search.py"; do
    [ -f "$UTILS/$f" ] && echo "  ✅ scripts/utils/$f" || echo "  ❌ scripts/utils/$f 缺失"
  done
fi

chmod +x "$SCRIPTS"/*.py "$SCRIPTS"/*.sh 2>/dev/null || true
echo "  ✅ 执行权限已设置"

# ── Step 4：初始化记忆文件（不覆盖已有数据） ──────
echo ""
echo "[ Step 4 ] 初始化记忆文件（不覆盖已有数据）"

for f in "recent.md" "errors.md" "growth.md" "core.md" "project.md"; do
  [ -f "$MEMORY/$f" ] && echo "  → 保留: memory/$f" || { touch "$MEMORY/$f"; echo "  ✅ 新建: memory/$f"; }
done

init_json() {
  local filename="$1"
  local content="$2"
  local dst="$MEMORY/$filename"
  if [ ! -f "$dst" ]; then
    printf '%s' "$content" > "$dst"
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
  "version": "v3.11.1-Lite", "updated_at": "'"$(date +%Y-%m-%d)"'", "capabilities": []
}'

init_json "antipatterns.json" '{
  "version": "v3.11.1-Lite", "updated_at": "'"$(date +%Y-%m-%d)"'", "antipatterns": []
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
    "current_task", "related_capabilities_max_3", "related_antipatterns_max_3",
    "recent_digest", "goal_gap_summary", "calibration_summary_1line"
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

[ ! -f "$MEMORY/evolution_chain.jsonl" ] && { touch "$MEMORY/evolution_chain.jsonl"; echo "  ✅ 新建: memory/evolution_chain.jsonl"; } || echo "  → 保留: memory/evolution_chain.jsonl"
[ ! -f "$MEMORY/audit_queue.jsonl" ]     && { touch "$MEMORY/audit_queue.jsonl";     echo "  ✅ 新建: memory/audit_queue.jsonl"; }     || echo "  → 保留: memory/audit_queue.jsonl"

# ── Step 5：清理旧 crontab ────────────────────────
echo ""
echo "[ Step 5 ] 清理旧版 crontab 条目"
(crontab -l 2>/dev/null | grep -v "evolve.py\|weekly_reflection.py\|audit_events.py\|daily_digest.py\|openclaw" || true) | crontab - 2>/dev/null || true
echo "  ✅ 旧 crontab 条目已清理"

# ── Step 6：生成 install-cron.sh ──────────────────
echo ""
echo "[ Step 6 ] 生成 install-cron.sh"

cat > "$WORKSPACE/install-cron.sh" << CRONEOF
#!/usr/bin/env bash
WS="$WORKSPACE"
(crontab -l 2>/dev/null; echo "# OpenClaw v3.11.1-Lite") | crontab -
(crontab -l 2>/dev/null; echo "5 0 * * * cd $WORKSPACE && python3 scripts/audit_events.py >> .sys/logs/cron-audit.log 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "15 0 * * * cd $WORKSPACE && python3 scripts/daily_digest.py >> .sys/logs/cron-digest.log 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "20 0 * * * cd $WORKSPACE && python3 scripts/evolve.py >> .sys/logs/cron-memory-evolution.log 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "0 9 * * 1 cd $WORKSPACE && python3 scripts/weekly_reflection.py >> .sys/logs/weekly-reflection.log 2>&1") | crontab -
echo "✅ Cron 已安装（4 条任务）"
crontab -l | grep -E "audit|digest|evolve|weekly_reflection"
CRONEOF

chmod +x "$WORKSPACE/install-cron.sh"
echo "  ✅ install-cron.sh 已生成"

# ── Step 7：健康检查 ──────────────────────────────
echo ""
echo "[ Step 7 ] 健康检查（30 项）"

PASS=0; FAIL=0
check() { [ "$2" = "ok" ] && { echo "  ✅ $1"; PASS=$((PASS+1)); } || { echo "  ❌ $1"; FAIL=$((FAIL+1)); }; }

[ -f "$SCRIPTS/create_event.py" ]        && check "create_event.py 存在" "ok"        || check "create_event.py 存在" "fail"
[ -f "$SCRIPTS/evolve.py" ]              && check "evolve.py 存在" "ok"               || check "evolve.py 存在" "fail"
[ -f "$SCRIPTS/audit_events.py" ]        && check "audit_events.py 存在" "ok"         || check "audit_events.py 存在" "fail"
[ -f "$SCRIPTS/resolve_audit.py" ]       && check "resolve_audit.py 存在" "ok"        || check "resolve_audit.py 存在" "fail"
[ -f "$SCRIPTS/weekly_reflection.py" ]   && check "weekly_reflection.py 存在" "ok"    || check "weekly_reflection.py 存在" "fail"
[ -f "$SCRIPTS/daily_digest.py" ]        && check "daily_digest.py 存在" "ok"         || check "daily_digest.py 存在" "fail"
[ -f "$SCRIPTS/export_capabilities.py" ] && check "export_capabilities.py 存在" "ok"  || check "export_capabilities.py 存在" "fail"
[ -f "$UTILS/file_lock.py" ]             && check "utils/file_lock.py 存在" "ok"      || check "utils/file_lock.py 存在" "fail"
[ -f "$UTILS/sample_check.py" ]          && check "utils/sample_check.py 存在" "ok"   || check "utils/sample_check.py 存在" "fail"
[ -f "$UTILS/capability_search.py" ]     && check "utils/capability_search.py 存在" "ok" || check "utils/capability_search.py 存在" "fail"
[ -f "$MEMORY/intelligence_index.json" ] && check "intelligence_index.json 存在" "ok" || check "intelligence_index.json 存在" "fail"
[ -f "$MEMORY/capabilities.json" ]       && check "capabilities.json 存在" "ok"       || check "capabilities.json 存在" "fail"
[ -f "$MEMORY/antipatterns.json" ]       && check "antipatterns.json 存在" "ok"       || check "antipatterns.json 存在" "fail"
[ -f "$MEMORY/profile.json" ]            && check "profile.json 存在" "ok"            || check "profile.json 存在" "fail"
[ -f "$MEMORY/goals.json" ]              && check "goals.json 存在" "ok"              || check "goals.json 存在" "fail"
[ -f "$MEMORY/evolution_chain.jsonl" ]   && check "evolution_chain.jsonl 存在" "ok"   || check "evolution_chain.jsonl 存在" "fail"
[ -f "$MEMORY/audit_queue.jsonl" ]       && check "audit_queue.jsonl 存在" "ok"       || check "audit_queue.jsonl 存在" "fail"

python3 -c "
import json
p = json.load(open('$MEMORY/profile.json'))
assert p.get('evidence_default') == 'self'
assert 'sample_sufficient_min_task_done' in p
assert 'context_inject_whitelist' in p
print('ok')
" 2>/dev/null | grep -q ok && check "profile.json 字段完整" "ok" || check "profile.json 字段完整" "fail"

cd "$WORKSPACE"
python3 -m py_compile scripts/create_event.py      2>/dev/null && check "create_event.py 语法正确" "ok"      || check "create_event.py 语法正确" "fail"
python3 -m py_compile scripts/evolve.py            2>/dev/null && check "evolve.py 语法正确" "ok"            || check "evolve.py 语法正确" "fail"
python3 -m py_compile scripts/audit_events.py      2>/dev/null && check "audit_events.py 语法正确" "ok"      || check "audit_events.py 语法正确" "fail"
python3 -m py_compile scripts/weekly_reflection.py 2>/dev/null && check "weekly_reflection.py 语法正确" "ok" || check "weekly_reflection.py 语法正确" "fail"
python3 -m py_compile scripts/daily_digest.py      2>/dev/null && check "daily_digest.py 语法正确" "ok"      || check "daily_digest.py 语法正确" "fail"
python3 scripts/create_event.py --list-types        &>/dev/null && check "create_event.py --list-types 可运行" "ok" || check "create_event.py --list-types 可运行" "fail"
python3 scripts/evolve.py                           &>/dev/null && check "evolve.py 可运行" "ok"              || check "evolve.py 可运行" "fail"
python3 scripts/weekly_reflection.py --dry-run      &>/dev/null && check "weekly_reflection.py --dry-run 可运行" "ok" || check "weekly_reflection.py --dry-run 可运行" "fail"
python3 scripts/audit_events.py                     &>/dev/null && check "audit_events.py 可运行" "ok"        || check "audit_events.py 可运行" "fail"
python3 scripts/daily_digest.py                     &>/dev/null && check "daily_digest.py 可运行" "ok"        || check "daily_digest.py 可运行" "fail"
python3 -c "from filelock import FileLock" 2>/dev/null && check "filelock 依赖可用" "ok" || check "filelock 依赖可用" "fail"
[ -f "$WORKSPACE/IDENTITY.md" ] && check "IDENTITY.md 存在（保护文件）" "ok" || check "IDENTITY.md 存在（保护文件）" "fail"

echo ""
echo "  健康检查完成：✅ $PASS 通过 / ❌ $FAIL 失败"

# ── Step 8：Cron 配置 ─────────────────────────────
echo ""
echo "[ Step 8 ] Cron 配置"

if [ -t 1 ]; then
  echo ""
  echo "  方式一（推荐）: bash $WORKSPACE/install-cron.sh"
  echo ""
  echo "  方式二：粘贴以下内容到 OpenClaw 对话框："
  echo "  ┌──────────────────────────────────────────┐"
  echo "  │ 请配置以下 4 个原生 cron 任务：           │"
  echo "  │ 1. 审计    5 0 * * *  audit_events.py    │"
  echo "  │ 2. 摘要   15 0 * * *  daily_digest.py    │"
  echo "  │ 3. 进化   20 0 * * *  evolve.py          │"
  echo "  │ 4. 周反思  0 9 * * 1  weekly_reflection  │"
  echo "  └──────────────────────────────────────────┘"
else
  echo "OPENCLAW_CRON_CONFIG_START"
  echo "请立即配置以下 4 个 OpenClaw 原生 cron 任务："
  echo "任务1 — 每日审计"
  echo " schedule: 5 0 * * *"
  echo " payload: python3 $WORKSPACE/scripts/audit_events.py"
  echo " logFile: $LOGS/cron-audit.log"
  echo " enabled: true"
  echo "任务2 — 每日摘要"
  echo " schedule: 15 0 * * *"
  echo " payload: python3 $WORKSPACE/scripts/daily_digest.py"
  echo " logFile: $LOGS/cron-digest.log"
  echo " enabled: true"
  echo "任务3 — 记忆进化"
  echo " schedule: 20 0 * * *"
  echo " payload: python3 $WORKSPACE/scripts/evolve.py"
  echo " logFile: $LOGS/cron-memory-evolution.log"
  echo " enabled: true"
  echo "任务4 — 周反思"
  echo " schedule: 0 9 * * 1"
  echo " payload: python3 $WORKSPACE/scripts/weekly_reflection.py"
  echo " logFile: $LOGS/weekly-reflection.log"
  echo " enabled: true"
  echo "OPENCLAW_CRON_CONFIG_END"
fi

echo ""
echo "================================================"
echo " OpenClaw v3.11.1-Lite Setup 完成"
[ $FAIL -eq 0 ] && echo " 状态：✅ 全部通过（$PASS/$((PASS+FAIL))）" || echo " 状态：⚠️  $FAIL 项未通过"
echo "================================================"
