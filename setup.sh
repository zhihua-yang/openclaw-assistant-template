#!/bin/bash
# ============================================================
# OpenClaw 数字助手 v3.7 — 一键部署脚本
# 放置位置：openclaw-assistant-template/setup.sh（仓库根目录）
#
# 用法：
#   bash setup.sh              # 安装到 ~/.openclaw/workspace
#   bash setup.sh /custom/path # 安装到自定义路径
#   bash setup.sh --force      # 强制重装（覆盖记忆文件，谨慎）
# ============================================================
# v3.7 变更：
#   - 修复脚本同步路径：$REPO_DIR/workspace/scripts/ → $WORKSPACE/scripts/
#   - 删除系统 crontab 注册（避免与 OpenClaw 原生 cron 双重触发）
#   - 自动清理 v3.6 遗留的系统 crontab 条目
#   - 恢复 10 项健康检查
#   - 新增 memory/growth.md 初始化
# ============================================================

set -e

# $REPO_DIR = 仓库根目录（setup.sh 所在位置）
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="${1:-$HOME/.openclaw/workspace}"
FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1 && WORKSPACE="$HOME/.openclaw/workspace"
[ "${2:-}" = "--force" ] && FORCE=1

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BLUE='\033[0;34m'; NC='\033[0m'
log()   { echo -e "${GREEN}[setup]${NC} $1"; }
warn()  { echo -e "${YELLOW}[warn]${NC}  $1"; }
fail()  { echo -e "${RED}[fail]${NC}  $1"; exit 1; }
check() { echo -e "${BLUE}[check]${NC} $1"; }
ok()    { echo -e "${GREEN}  ✅${NC} $1"; }
ng()    { echo -e "${RED}  ❌${NC} $1"; HEALTH_FAIL=$((HEALTH_FAIL + 1)); }

HEALTH_FAIL=0

# ════════════════════════════════════════════════════════════
# 1. 前提条件检查
# ════════════════════════════════════════════════════════════
echo ""
log "检查前提条件..."
command -v python3 &>/dev/null || fail "python3 未安装，请先安装后重试"
log "python3 已就绪：$(python3 --version 2>&1)"

BASH_MAJOR="${BASH_VERSINFO[0]}"
if [ "$BASH_MAJOR" -lt 4 ]; then
    warn "Bash 版本为 $BASH_VERSION（建议 4.0+）"
    warn "macOS 用户请执行：brew install bash"
fi

# ════════════════════════════════════════════════════════════
# 2. 初始化运行时目录（.sys）
# ════════════════════════════════════════════════════════════
log "目标 workspace：$WORKSPACE"
log "初始化运行时目录 (.sys)..."

mkdir -p "$WORKSPACE/.sys/sessions"
mkdir -p "$WORKSPACE/.sys/logs"
mkdir -p "$WORKSPACE/.sys/baseline"
mkdir -p "$WORKSPACE/.sys/todo"
mkdir -p "$WORKSPACE/.sys/compact"
mkdir -p "$WORKSPACE/memory/archive"
mkdir -p "$WORKSPACE/scripts"

touch "$WORKSPACE/.sys/logs/events.jsonl"
[ -f "$WORKSPACE/.sys/logs/last_evolution_line.txt" ] || echo "0" > "$WORKSPACE/.sys/logs/last_evolution_line.txt"

# ════════════════════════════════════════════════════════════
# 3. 同步脚本文件（仓库 workspace/scripts/ → $WORKSPACE/scripts/）
#    直接覆盖，确保版本与仓库一致
# ════════════════════════════════════════════════════════════
log "同步脚本文件到 $WORKSPACE/scripts/..."

# 脚本源目录：仓库根目录/workspace/scripts/
SCRIPTS_SRC="$REPO_DIR/workspace/scripts"

SCRIPTS=(
    evolve.py
    create_event.py
    session_note_writer.py
    fix_recent_events_tags.py
    fix_nonstandard_types.py
)

for s in "${SCRIPTS[@]}"; do
    if [ -f "$SCRIPTS_SRC/$s" ]; then
        cp "$SCRIPTS_SRC/$s" "$WORKSPACE/scripts/$s"
        log "  已更新：scripts/$s"
    else
        warn "  仓库中未找到：workspace/scripts/$s（跳过）"
    fi
done

# ════════════════════════════════════════════════════════════
# 4. 初始化记忆文件（不覆盖已有数据）
# ════════════════════════════════════════════════════════════
log "初始化记忆文件..."

if [ ! -f "$WORKSPACE/memory/recent.md" ]; then
    echo -e "# Recent Memory\n_由 evolve.py 自动维护_" > "$WORKSPACE/memory/recent.md"
    log "创建 memory/recent.md"
fi
if [ ! -f "$WORKSPACE/memory/errors.md" ]; then
    echo -e "# Error Log\n_记录高频错误与正确处理方式_" > "$WORKSPACE/memory/errors.md"
    log "创建 memory/errors.md"
fi
if [ ! -f "$WORKSPACE/memory/core.md" ]; then
    printf "# Core Memory\n\n## 用户信息\n- 姓名：（待填写）\n- 时区：（待填写）\n" > "$WORKSPACE/memory/core.md"
    log "创建 memory/core.md"
fi
if [ ! -f "$WORKSPACE/memory/growth.md" ]; then
    printf "# Growth Log\n\n_长期能力成长轨迹，由 evolve.py 自动追加_\n_格式：\`- [YYYY-MM-DD] [event-type] content\`_\n\n---\n\n" > "$WORKSPACE/memory/growth.md"
    log "创建 memory/growth.md"
fi

# ════════════════════════════════════════════════════════════
# 5. 设置脚本执行权限
# ════════════════════════════════════════════════════════════
log "设置脚本执行权限..."
chmod +x "$WORKSPACE/scripts/"*.sh 2>/dev/null || true
chmod +x "$WORKSPACE/scripts/"*.py 2>/dev/null || true

# ════════════════════════════════════════════════════════════
# 5. 清理 v3.6 遗留的系统 crontab 条目（如有）
#    v3.7 起统一使用 OpenClaw 原生 cron，不注册系统 crontab
# ════════════════════════════════════════════════════════════
EXISTING=$(crontab -l 2>/dev/null | grep -E "memory-evolution|weekly-self-reflection" || true)
if [ -n "$EXISTING" ]; then
    warn "检测到系统 crontab 中存在 openclaw 旧条目，自动清理..."
    crontab -l 2>/dev/null | grep -v "memory-evolution\|weekly-self-reflection" | crontab -
    log "系统 crontab 旧条目已清理 ✅"
fi

# ════════════════════════════════════════════════════════════
# 6. 生成 install-cron.sh（参考文件，不自动注册）
#    v3.7：OpenClaw 原生 cron 统一管理，此文件仅供查阅
# ════════════════════════════════════════════════════════════
log "生成 install-cron.sh 参考文件..."

INSTALL_CRON="$WORKSPACE/scripts/install-cron.sh"
cat > "$INSTALL_CRON" << 'EOF'
#!/bin/bash
# ============================================================
# install-cron.sh — OpenClaw cron 参考配置
# 由 setup.sh v3.7 自动生成
#
# v3.7 起建议在 OpenClaw 应用内使用原生 cron 管理定时任务。
# 如需手动注册系统 crontab，参考下方说明。
# ============================================================
EOF

# 追加含变量展开的部分（单独写，避免 heredoc 变量转义问题）
cat >> "$INSTALL_CRON" << EOF

WORKSPACE="$WORKSPACE"

echo "=== OpenClaw 推荐 cron 配置（供参考）==="
echo ""
echo "# 记忆进化（每天 00:00）"
echo "0 0 * * * python3 \$WORKSPACE/scripts/evolve.py >> \$WORKSPACE/.sys/logs/cron-memory-evolution.log 2>&1"
echo ""
echo "# 周反思（每周一 09:00，调用真实脚本）"
echo "0 9 * * 1 \$WORKSPACE/scripts/weekly_reflection.sh >> \$WORKSPACE/.sys/logs/weekly-reflection.log 2>&1"
echo ""
echo "手动注册方法：crontab -e，粘贴上方两行（去掉 echo 和引号）"
EOF

chmod +x "$INSTALL_CRON"
log "install-cron.sh 已生成：$INSTALL_CRON"

# ════════════════════════════════════════════════════════════
# 7. 健康检查（10 项核心检查）
# ════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}══════════════════════════════════════${NC}"
echo -e "${BLUE}  健康检查（v3.7）${NC}"
echo -e "${BLUE}══════════════════════════════════════${NC}"

# 1. 业务事件日志
check "1/10  .sys/logs/events.jsonl 存在"
if [ -f "$WORKSPACE/.sys/logs/events.jsonl" ]; then
    LINES=$(wc -l < "$WORKSPACE/.sys/logs/events.jsonl" 2>/dev/null || echo 0)
    ok "存在（${LINES} 条记录）"
else
    ng "不存在：$WORKSPACE/.sys/logs/events.jsonl"
fi

# 2. 双路径隔离
check "2/10  .sys/logs/ 与 .openclaw/logs/ 路径隔离正常"
GATEWAY_LOG="$HOME/.openclaw/logs/events.jsonl"
if [ -f "$GATEWAY_LOG" ]; then
    if ! diff -q "$GATEWAY_LOG" "$WORKSPACE/.sys/logs/events.jsonl" &>/dev/null; then
        ok "两个文件内容不同（路径隔离正常）"
    else
        warn "两个文件内容相同，请确认是否存在写入混用"
    fi
else
    ok "Gateway 日志独立（路径隔离有效）"
fi

# 3. growth.md
check "3/10  memory/growth.md 存在"
[ -f "$WORKSPACE/memory/growth.md" ] && ok "存在" || ng "不存在"

# 4. recent.md
check "4/10  memory/recent.md 存在"
[ -f "$WORKSPACE/memory/recent.md" ] && ok "存在" || ng "不存在"

# 5. errors.md
check "5/10  memory/errors.md 存在"
[ -f "$WORKSPACE/memory/errors.md" ] && ok "存在" || ng "不存在"

# 6. AGENTS.md / IDENTITY.md
check "6/10  AGENTS.md 和 IDENTITY.md 存在"
MISSING_MD=""
[ ! -f "$WORKSPACE/AGENTS.md" ]   && MISSING_MD="$MISSING_MD AGENTS.md"
[ ! -f "$WORKSPACE/IDENTITY.md" ] && MISSING_MD="$MISSING_MD IDENTITY.md"
[ -z "$MISSING_MD" ] && ok "均存在" || ng "缺少：$MISSING_MD"

# 7. 5 个核心脚本
check "7/10  核心脚本存在且可执行"
MISSING_S=""
for s in evolve.py create_event.py session_note_writer.py fix_recent_events_tags.py fix_nonstandard_types.py; do
    [ ! -f "$WORKSPACE/scripts/$s" ] && MISSING_S="$MISSING_S $s"
done
[ -z "$MISSING_S" ] && ok "5 个脚本均存在" || ng "缺少：$MISSING_S"

# 8. create_event.py --list-types（v3.7.1 无需 --type 参数）
check "8/10  create_event.py 可正常运行（--list-types）"
if python3 "$WORKSPACE/scripts/create_event.py" --list-types &>/dev/null; then
    ok "运行正常"
else
    ng "运行失败，请检查脚本语法"
fi

# 9. evolve.py
check "9/10  evolve.py 可正常运行"
EVOLVE_OUT=$(python3 "$WORKSPACE/scripts/evolve.py" 2>&1 || true)
if echo "$EVOLVE_OUT" | grep -q "using logs"; then
    ok "运行正常（$(echo "$EVOLVE_OUT" | head -1)）"
else
    ng "运行异常：$EVOLVE_OUT"
fi

# 10. 系统 crontab 无冲突
check "10/10 系统 crontab 无冲突条目"
SYS_CRON=$(crontab -l 2>/dev/null | grep -E "memory-evolution|weekly-self-reflection" || true)
if [ -z "$SYS_CRON" ]; then
    ok "无冲突条目"
    warn "请在 OpenClaw 应用内确认原生 cron 已启用 memory-evolution 任务"
else
    ng "仍有系统 crontab 条目：$SYS_CRON"
fi

# ════════════════════════════════════════════════════════════
# 结果汇总
# ════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}══════════════════════════════════════${NC}"
if [ "$HEALTH_FAIL" -eq 0 ]; then
    echo -e "${GREEN}✅ 全部 10 项检查通过！部署完成（v3.7）${NC}"
else
    echo -e "${YELLOW}⚠️  ${HEALTH_FAIL} 项检查未通过，请根据上方提示修复${NC}"
fi
echo -e "${BLUE}══════════════════════════════════════${NC}"
echo ""
echo "下一步："
echo "  1. 在 OpenClaw → Settings → Workspace 中设置路径为："
echo "     $WORKSPACE"
echo "  2. 确认 OpenClaw 原生 cron 已启用 memory-evolution 任务"
echo "  3. 在 OpenClaw 新建对话，粘贴 AGENTS.md 中的激活提示词"
echo ""
