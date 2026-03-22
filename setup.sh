#!/usr/bin/env bash
# OpenClaw v3.11.1-Lite setup.sh
# 支持两种用法：
#   用法1（全新实例）: bash setup.sh
#                     → workspace 目录在仓库内，原地初始化
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

if [ -n "$TARGET_WORKSPACE" ]; then
  WORKSPACE="$TARGET_WORKSPACE"
  COPY_MODE=true
  MODE_LABEL="升级已有工作区"
else
  WORKSPACE="$REPO_DIR/workspace"
  COPY_MODE=false
  MODE_LABEL="全新实例原地初始化"
fi

MEMORY="$WORKSPACE/memory"
SYS="$WORKSPACE/.sys"
LOGS="$SYS/logs"
SCRIPTS="$WORKSPACE/scripts"
UTILS="$SCRIPTS/utils"

echo "================================================"
echo " OpenClaw v3.11.1-Lite Setup"
echo " 模式     : $MODE_LABEL"
echo " REPO     : $REPO_DIR"
echo " WORKSPACE: $WORKSPACE"
echo "================================================"

# ── Step 1：前提条件检查 & 依赖安装 ──────────────
echo ""
echo "[ Step 1 ] 前提条件检查 & 依赖安装"

if ! command -v python3 &>/dev/null; then
  echo "❌ python3 未找到，请先安装 Python 3.8+"
  exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  ✅ python3 $PYTHON_VERSION"

install_pkg() {
  local pkg="$1"
  local required="$2"
  local import_name="${3:-$pkg}"

  # 先检查是否已安装
  if python3 -c "import $import_name" 2>/dev/null; then
    echo "  ✅ $pkg（已安装）"
    return 0
  fi

  echo "  → 安装 $pkg ..."

  # 依次尝试四种安装方式
  if pip3 install "$pkg" --quiet 2>/dev/null; then
    echo "  ✅ $pkg（pip3 安装成功）"
    return 0
  elif pip install "$pkg" --quiet 2>/dev/null; then
    echo "  ✅ $pkg（pip 安装成功）"
    return 0
  elif python3 -m pip install "$pkg" --quiet 2>/dev/null; then
    echo "  ✅ $pkg（python3 -m pip 安装成功）"
    return 0
  elif python3 -m pip install "$pkg" --user --quiet 2>/dev/null; then
    echo "  ✅ $pkg（pip --user 安装成功）"
    return 0
  else
    if [ "$required" = "required" ]; then
      echo "  ❌ $pkg 安装失败（必须依赖）"
      echo "     请手动执行以下任一命令后重新运行 setup.sh："
      echo "       pip3 install $pkg"
      echo "       pip install $pkg"
      echo "       python3 -m pip install $pkg --user"
      return 1
    else
      echo "  ⚠️  $pkg 安装失败（可选依赖，功能降级）"
      echo "     capability 检索将使用精确匹配替代 TF-IDF"
      return 0
    fi
  fi
}

install_pkg "filelock"     "required" "filelock"   || exit 1
install_pkg "scikit-learn" "optional" "sklearn"

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
      echo "  ❌ 源文件缺失: $SRC_SCRIPTS/$f（请检查仓库完整性）"
    fi
  done

  UTIL_FILES=(
    "__init__.py"
    "file_lock.py"
    "paths.py"
    "sample_check.py"
    "capability_search.py"
  )

  for f in "${UTIL_FILES[@]}"; do
    if [ -f "$SRC_SCRIPTS/utils/$f" ]; then
      cp "$SRC_SCRIPTS/utils/$f" "$UTILS/$f"
      echo "  ✅ 已更新: scripts/utils/$f"
    else
      echo "  ❌ 源文件缺失: $SRC_SCRIPTS/utils/$f"
    fi
  done

  # AGENTS.md 覆盖更新
  if [ -f "$REPO_DIR/workspace/AGENTS.md" ]; then
    cp "$REPO_DIR/workspace/AGENTS.md" "$WORKSPACE/AGENTS.md"
    echo "  ✅ 已更新: AGENTS.md"
  fi

  # IDENTITY.md 保护，不覆盖
  if [ -f "$WORKSPACE/IDENTITY.md" ]; then
    echo "  → 保留: IDENTITY.md（保护文件，不覆盖）"
  elif [ -f "$REPO_DIR/workspace/IDENTITY.md" ]; then
    cp "$REPO_DIR/workspace/IDENTITY.md" "$WORKSPACE/IDENTITY.md"
    echo "  ✅ 新建: IDENTITY.md"
  fi

else
  # 全新模式：仅验证文件完整性，不复制
  REQUIRED_SCRIPTS=(
    "create_event.py"
    "evolve.py"
    "audit_events.py"
    "resolve_audit.py"
    "weekly_reflection.py"
    "daily_digest.py"
    "export_capabilities.py"
  )

  REQUIRED_UTILS=(
    "__init__.py"
    "file_lock.py"
    "paths.py"
    "sample_check.py"
    "capability_search.py"
  )

  ALL_OK=true
  for f in "${REQUIRED_SCRIPTS[@]}"; do
    if [ -f "$SCRIPTS/$f" ]; then
      echo "  ✅ scripts/$f"
    else
      echo "  ❌ scripts/$f 缺失"
      ALL_OK=false
    fi
  done

  for f in "${REQUIRED_UTILS[@]}"; do
    if [ -f "$UTILS/$f" ]; then
      echo "  ✅ scripts/utils/$f"
    else
      echo "  ❌ scripts/utils/$f 缺失"
      ALL_OK=false
    fi
  done

  if [ "$ALL_OK" = false ]; then
    echo ""
    echo "  ⚠️  部分文件缺失，可能是 clone 不完整，请重新 clone："
    echo "     git clone https://github.com/zhihua-yang/openclaw-assistant-template.git"
  fi
fi

# 统一设置执行权限
chmod +x "$SCRIPTS"/*.py 2>/dev/null || true
chmod +x "$SCRIPTS"/*.sh 2>/dev/null || true
echo "  ✅ 执行权限已设置"

# ── Step 4：初始化记忆文件（不覆盖已有数据） ──────
echo ""
echo "[ Step 4 ] 初始化记忆文件（不覆盖已有数据）"

# v3.7 保留的 Markdown 展示文件
for f in "recent.md" "errors.md" "growth.md" "core.md" "project.md"; do
  if [ -f "$MEMORY/$f" ]; then
    echo "  → 保留: memory/$f"
  else
    touch "$MEMORY/$f"
    echo "  ✅ 新建: memory/$f"
  fi
done

# 初始化 JSON（不覆盖）
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

if [ ! -f "$MEMORY/evolution_chain.jsonl" ]; then
  touch "$MEMORY/evolution_chain.jsonl"
  echo "  ✅ 新建: memory/evolution_chain.jsonl"
  [ -f "$SYS/logs/events.jsonl" ] && echo "  ℹ️  v3.7 历史事件保留在 .sys/logs/events.jsonl，不自动迁移"
else
  echo "  → 保留: memory/evolution_chain.jsonl"
fi

if [ ! -f "$MEMORY/audit_queue.jsonl" ]; then
  touch "$MEMORY/audit_queue.jsonl"
  echo "  ✅ 新建: memory/audit_queue.jsonl"
else
  echo "  → 保留: memory/audit_queue.jsonl"
fi

# ── Step 5：清理旧 crontab ────────────────────────
echo ""
echo "[ Step 5 ] 清理旧版 crontab 条目"

(crontab -l 2>/dev/null | grep -v "evolve.py\|weekly_reflection.py\|audit_events.py\|daily_digest.py\|openclaw" || true) \
  | crontab - 2>/dev/null || true
echo "  ✅ 旧 crontab 条目已清理"

# ── Step 6：生成 install-cron.sh ──────────────────
echo ""
echo "[ Step 6 ] 生成 install-cron.sh"

cat > "$WORKSPACE/install-cron.sh" << CRONEOF
#!/usr/bin/env bash
# OpenClaw v3.11.1-Lite Cron 安装脚本
# 运行方式: bash install-cron.sh（在 workspace 目录下）

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
echo "  ✅ install-cron.sh 已生成 → $WORKSPACE/install-cron.sh"

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

# 脚本文件存在性
[ -f "$SCRIPTS/create_event.py" ]        && check "create_event.py 存在" "ok"        || check "create_event.py 存在" "fail"
[ -f "$SCRIPTS/evolve.py" ]              && check "evolve.py 存在" "ok"               || check "evolve.py 存在" "fail"
[ -f "$SCRIPTS/audit_events.py" ]        && check "audit_events.py 存在" "ok"         || check "audit_events.py 存在" "fail"
[ -f "$SCRIPTS/resolve_audit.py" ]       && check "resolve_audit.py 存在" "ok"        || check "resolve_audit.py 存在" "fail"
[ -f "$SCRIPTS/weekly_reflection.py" ]   && check "weekly_reflection.py 存在" "ok"    || check "weekly_reflection.py 存在" "fail"
[ -f "$SCRIPTS/daily_digest.py" ]        && check "daily_digest.py 存在" "ok"         || check "daily_digest.py 存在" "fail"
[ -f "$SCRIPTS/export_capabilities.py" ] && check "export_capabilities.py 存在" "ok"  || check "export_capabilities.py 存在" "fail"

# utils 文件存在性
[ -f "$UTILS/__init__.py" ]              && check "utils/__init__.py 存在" "ok"        || check "utils/__init__.py 存在" "fail"
[ -f "$UTILS/file_lock.py" ]             && check "utils/file_lock.py 存在" "ok"       || check "utils/file_lock.py 存在" "fail"
[ -f "$UTILS/sample_check.py" ]          && check "utils/sample_check.py 存在" "ok"    || check "utils/sample_check.py 存在" "fail"
[ -f "$UTILS/capability_search.py" ]     && check "utils/capability_search.py 存在" "ok" || check "utils/capability_search.py 存在" "fail"

# memory 文件存在性
[ -f "$MEMORY/intelligence_index.json" ] && check "intelligence_index.json 存在" "ok" || check "intelligence_index.json 存在" "fail"
[ -f "$MEMORY/capabilities.json" ]       && check "capabilities.json 存在" "ok"       || check "capabilities.json 存在" "fail"
[ -f "$MEMORY/antipatterns.json" ]       && check "antipatterns.json 存在" "ok"       || check "antipatterns.json 存在" "fail"
[ -f "$MEMORY/profile.json" ]            && check "profile.json 存在" "ok"            || check "profile.json 存在" "fail"
[ -f "$MEMORY/goals.json" ]              && check "goals.json 存在" "ok"              || check "goals.json 存在" "fail"
[ -f "$MEMORY/evolution_chain.jsonl" ]   && check "evolution_chain.jsonl 存在" "ok"   || check "evolution_chain.jsonl 存在" "fail"
[ -f "$MEMORY/audit_queue.jsonl" ]       && check "audit_queue.jsonl 存在" "ok"       || check "audit_queue.jsonl 存在" "fail"

# profile.json 字段完整性
python3 -c "
import json
p = json.load(open('$MEMORY/profile.json'))
assert p.get('evidence_default') == 'self'
assert 'sample_sufficient_min_task_done' in p
assert 'context_inject_whitelist' in p
assert 'allow_weekly_report_llm_rewrite' in p
print('ok')
" 2>/dev/null | grep -q ok \
  && check "profile.json 字段完整" "ok" \
  || check "profile.json 字段完整" "fail"

# 语法检查
cd "$WORKSPACE"
python3 -m py_compile scripts/create_event.py      2>/dev/null && check "create_event.py 语法正确" "ok"      || check "create_event.py 语法正确" "fail"
python3 -m py_compile scripts/evolve.py            2>/dev/null && check "evolve.py 语法正确" "ok"            || check "evolve.py 语法正确" "fail"
python3 -m py_compile scripts/audit_events.py      2>/dev/null && check "audit_events.py 语法正确" "ok"      || check "audit_events.py 语法正确" "fail"
python3 -m py_compile scripts/weekly_reflection.py 2>/dev/null && check "weekly_reflection.py 语法正确" "ok" || check "weekly_reflection.py 语法正确" "fail"
python3 -m py_compile scripts/daily_digest.py      2>/dev/null && check "daily_digest.py 语法正确" "ok"      || check "daily_digest.py 语法正确" "fail"
python3 -m py_compile scripts/utils/capability_search.py 2>/dev/null && check "capability_search.py 语法正确" "ok" || check "capability_search.py 语法正确" "fail"

# 运行测试
python3 scripts/create_event.py --list-types        &>/dev/null && check "create_event.py --list-types 可运行" "ok" || check "create_event.py --list-types 可运行" "fail"
python3 scripts/evolve.py                           &>/dev/null && check "evolve.py 可运行" "ok"               || check "evolve.py 可运行" "fail"
python3 scripts/weekly_reflection.py --dry-run      &>/dev/null && check "weekly_reflection.py --dry-run 可运行" "ok" || check "weekly_reflection.py --dry-run 可运行" "fail"
python3 scripts/audit_events.py                     &>/dev/null && check "audit_events.py 可运行" "ok"         || check "audit_events.py 可运行" "fail"
python3 scripts/daily_digest.py                     &>/dev/null && check "daily_digest.py 可运行" "ok"         || check "daily_digest.py 可运行" "fail"

# filelock 实测（acquire/release）
python3 -c "
from filelock import FileLock
import tempfile, os
f = FileLock(os.path.join(tempfile.gettempdir(), 'openclaw_test.lock'))
f.acquire()
f.release()
print('ok')
" 2>/dev/null | grep -q ok \
  && check "filelock acquire/release 实测" "ok" \
  || check "filelock acquire/release 实测" "fail"

# 保护文件
[ -f "$WORKSPACE/IDENTITY.md" ] && check "IDENTITY.md 存在（保护文件）" "ok" || check "IDENTITY.md 存在（保护文件）" "fail"

echo ""
echo "  健康检查完成：✅ $PASS 通过 / ❌ $FAIL 失败"

# ── Step 8：Cron 配置提示 ─────────────────────────
echo ""
echo "[ Step 8 ] Cron 配置"

if [ -t 1 ]; then
  # 交互式终端
  echo ""
  echo "  方式一（推荐）: bash $WORKSPACE/install-cron.sh"
  echo ""
  echo "  方式二：粘贴以下内容到 OpenClaw 对话框："
  echo "  ┌──────────────────────────────────────────────┐"
  echo "  │ 请配置以下 4 个原生 cron 任务：               │"
  echo "  │ 1. 审计    5 0 * * *   audit_events.py       │"
  echo "  │ 2. 摘要   15 0 * * *   daily_digest.py       │"
  echo "  │ 3. 进化   20 0 * * *   evolve.py             │"
  echo "  │ 4. 周反思  0 9 * * 1   weekly_reflection.py  │"
  echo "  └──────────────────────────────────────────────┘"
else
  # 非交互式（AI 容器环境）
  echo "OPENCLAW_CRON_CONFIG_START"
  echo "请立即配置以下 4 个 OpenClaw 原生 cron 任务："
  echo ""
  echo "任务1 — 每日审计"
  echo " schedule: 5 0 * * *"
  echo " payload: python3 $WORKSPACE/scripts/audit_events.py"
  echo " logFile: $LOGS/cron-audit.log"
  echo " enabled: true"
  echo ""
  echo "任务2 — 每日摘要"
  echo " schedule: 15 0 * * *"
  echo " payload: python3 $WORKSPACE/scripts/daily_digest.py"
  echo " logFile: $LOGS/cron-digest.log"
  echo " enabled: true"
  echo ""
  echo "任务3 — 记忆进化"
  echo " schedule: 20 0 * * *"
  echo " payload: python3 $WORKSPACE/scripts/evolve.py"
  echo " logFile: $LOGS/cron-memory-evolution.log"
  echo " enabled: true"
  echo ""
  echo "任务4 — 周反思"
  echo " schedule: 0 9 * * 1"
  echo " payload: python3 $WORKSPACE/scripts/weekly_reflection.py"
  echo " logFile: $LOGS/weekly-reflection.log"
  echo " enabled: true"
  echo "OPENCLAW_CRON_CONFIG_END"
fi

# ── 完成 ──────────────────────────────────────────
echo ""
echo "================================================"
echo " OpenClaw v3.11.1-Lite Setup 完成"
if [ $FAIL -eq 0 ]; then
  echo " 状态：✅ 全部通过（$PASS/$((PASS+FAIL))）"
else
  echo " 状态：⚠️  $FAIL 项未通过，请检查上方输出"
  echo " 提示：修复后可重新运行 bash setup.sh 验证"
fi
echo "================================================"
