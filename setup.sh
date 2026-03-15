#!/bin/bash
# ============================================================
# OpenClaw 内网数字助手 — 一键部署脚本 v3.4.1
#
# 用法 A（系统终端）：
#   bash setup.sh                 # 安装到 ~/.openclaw/workspace
#   bash setup.sh /custom/path    # 安装到自定义路径
#   bash setup.sh --force         # 强制重装（覆盖已有数据）
#
# 用法 B（OpenClaw 对话）：
#   将本文件拖给 OpenClaw → AI 完成文件部署 + 自动注册 OpenClaw 原生 cron
#   不依赖系统 crontab，OpenClaw Gateway 内置调度器直接管理定时任务
# ============================================================

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$REPO_DIR/workspace"
WORKSPACE="${1:-$HOME/.openclaw/workspace}"
FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1 && WORKSPACE="$HOME/.openclaw/workspace"
[ "${2:-}" = "--force" ] && FORCE=1

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[setup]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
fail() { echo -e "${RED}[fail]${NC} $1"; exit 1; }

# ── 1. 基本检查 ──────────────────────────────────────────────────────────
[ -d "$TEMPLATE_DIR" ] || fail "找不到 workspace/ 目录，请确认仓库结构正确"
command -v python3 &>/dev/null || fail "python3 未安装，请先安装后重试"

log "模板目录：$TEMPLATE_DIR"
log "目标 workspace：$WORKSPACE"

# ── 2. 拷贝模板文件 ───────────────────────────────────────────────────────
if [ -f "$WORKSPACE/.sys/logs/events.jsonl" ] && \
   [ -s "$WORKSPACE/.sys/logs/events.jsonl" ] && \
   [ "$FORCE" = "0" ]; then
  warn "检测到已有数据，跳过模板覆盖（强制重装请加 --force）"
else
  log "复制 workspace/ 到目标目录..."
  mkdir -p "$WORKSPACE"
  cp -r "$TEMPLATE_DIR"/. "$WORKSPACE"/
fi

# ── 3. 初始化运行时目录 ───────────────────────────────────────────────────
log "初始化运行时目录 (.sys)..."
mkdir -p "$WORKSPACE/.sys/sessions"
mkdir -p "$WORKSPACE/.sys/logs"
mkdir -p "$WORKSPACE/.sys/baseline"
mkdir -p "$WORKSPACE/.sys/todo"
mkdir -p "$WORKSPACE/.sys/compact"
mkdir -p "$WORKSPACE/memory/archive"

touch "$WORKSPACE/.sys/logs/events.jsonl"
[ -f "$WORKSPACE/.sys/logs/last_evolution_line.txt" ] || \
  echo "0" > "$WORKSPACE/.sys/logs/last_evolution_line.txt"

# ── 4. 脚本执行权限 ───────────────────────────────────────────────────────
log "设置脚本执行权限..."
chmod +x "$WORKSPACE/scripts/"*.sh 2>/dev/null || true
chmod +x "$WORKSPACE/scripts/evolve.py" 2>/dev/null || true
chmod +x "$WORKSPACE/scripts/create_event.py" 2>/dev/null || true

# ── 5. 定时任务注册 ───────────────────────────────────────────────────────
# 优先级：
#   1. openclaw cron add（OpenClaw 原生，终端/对话均可）
#   2. 系统 crontab（终端专用，兜底方案）
#   3. 均不可用时，生成 install-cron.sh 供手动操作

log "注册定时任务..."

_register_openclaw_cron() {
  log "使用 OpenClaw 原生 cron 注册定时任务..."

  # 任务1：每天 00:00 运行 evolve.py（记忆进化）
  openclaw cron add \
    --name "memory-evolution" \
    --cron "0 0 * * *" \
    --tz "UTC" \
    --session isolated \
    --message "执行记忆进化：运行 exec: WORKSPACE=$WORKSPACE python3 $WORKSPACE/scripts/evolve.py，完成后静默结束" \
    --delivery none 2>/dev/null && \
    log "memory-evolution 已注册（每天 00:00 UTC）" || \
    warn "memory-evolution 注册失败"

  # 任务2：每周一 09:00 写入周报触发信号
  openclaw cron add \
    --name "weekly-self-reflection-trigger" \
    --cron "0 9 * * 1" \
    --tz "UTC" \
    --session main \
    --system-event "weekly-self-reflection scheduled trigger" \
    --wake now 2>/dev/null && \
    log "weekly-self-reflection-trigger 已注册（每周一 09:00 UTC）" || \
    warn "weekly-self-reflection-trigger 注册失败"

  # 验证
  if openclaw cron list 2>/dev/null | grep -q "memory-evolution"; then
    log "OpenClaw cron 验证成功，当前任务列表："
    openclaw cron list 2>/dev/null | grep -E "memory-evolution|weekly-self-reflection"
    return 0
  else
    warn "OpenClaw cron 验证失败，切换到系统 crontab 方案"
    return 1
  fi
}

_register_system_cron() {
  log "使用系统 crontab 注册定时任务..."

  CRON_EVOLUTION="0 0 * * * WORKSPACE=$WORKSPACE python3 $WORKSPACE/scripts/evolve.py >> $WORKSPACE/.sys/logs/cron-memory-evolution.log 2>&1"
  CRON_REFLECTION="0 9 * * 1 python3 -c \"import json,sys; from datetime import datetime,timezone; sys.stdout.write(json.dumps({'ts':datetime.now(timezone.utc).isoformat(timespec='seconds'),'type':'task-done','tags':['cron','weekly'],'content':'weekly-self-reflection scheduled trigger','count':1},ensure_ascii=False)+chr(10))\" >> $WORKSPACE/.sys/logs/events.jsonl"

  (
    crontab -l 2>/dev/null | grep -v "cron-memory-evolution\|weekly-self-reflection"
    echo "$CRON_EVOLUTION"
    echo "$CRON_REFLECTION"
  ) | crontab -

  crontab -l 2>/dev/null | grep -q "cron-memory-evolution" && \
    log "memory-evolution 已注册（每天 00:00）" || warn "memory-evolution 注册失败"
  crontab -l 2>/dev/null | grep -q "weekly-self-reflection" && \
    log "weekly-self-reflection 已注册（每周一 09:00）" || warn "weekly-self-reflection 注册失败"
}

_write_install_cron() {
  INSTALL_SCRIPT="$WORKSPACE/scripts/install-cron.sh"
  cat > "$INSTALL_SCRIPT" << SCRIPT_EOF
#!/bin/bash
# install-cron.sh — 由 setup.sh 自动生成，在系统终端运行
# Workspace: $WORKSPACE

set -e
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "\${GREEN}[cron]\${NC} \$1"; }
warn() { echo -e "\${YELLOW}[warn]\${NC} \$1"; }

# 优先尝试 openclaw cron
if command -v openclaw &>/dev/null; then
  log "使用 OpenClaw 原生 cron..."
  openclaw cron add --name "memory-evolution" --cron "0 0 * * *" --tz "UTC" \
    --session isolated \
    --message "执行记忆进化：运行 exec: WORKSPACE=$WORKSPACE python3 $WORKSPACE/scripts/evolve.py，完成后静默结束" \
    --delivery none
  openclaw cron add --name "weekly-self-reflection-trigger" --cron "0 9 * * 1" --tz "UTC" \
    --session main \
    --system-event "weekly-self-reflection scheduled trigger" \
    --wake now
  log "完成！运行 openclaw cron list 确认"
elif command -v crontab &>/dev/null; then
  log "使用系统 crontab..."
  CRON_EVOLUTION="0 0 * * * WORKSPACE=$WORKSPACE python3 $WORKSPACE/scripts/evolve.py >> $WORKSPACE/.sys/logs/cron-memory-evolution.log 2>&1"
  CRON_REFLECTION="0 9 * * 1 python3 -c \"import json,sys; from datetime import datetime,timezone; sys.stdout.write(json.dumps({'ts':datetime.now(timezone.utc).isoformat(timespec='seconds'),'type':'task-done','tags':['cron','weekly'],'content':'weekly-self-reflection scheduled trigger','count':1},ensure_ascii=False)+chr(10))\" >> $WORKSPACE/.sys/logs/events.jsonl"
  ( crontab -l 2>/dev/null | grep -v "cron-memory-evolution\|weekly-self-reflection"
    echo "\$CRON_EVOLUTION"; echo "\$CRON_REFLECTION" ) | crontab -
  crontab -l | grep -E "memory-evolution|weekly-self-reflection"
  log "完成！"
else
  warn "未找到 openclaw 或 crontab 命令"
  warn "请手动定期执行：python3 $WORKSPACE/scripts/evolve.py"
fi
SCRIPT_EOF
  chmod +x "$INSTALL_SCRIPT"
  log "已生成备用安装脚本：$INSTALL_SCRIPT"
}

# 按优先级尝试注册
CRON_DONE=0
if command -v openclaw &>/dev/null; then
  _register_openclaw_cron && CRON_DONE=1
fi
if [ "$CRON_DONE" = "0" ] && command -v crontab &>/dev/null; then
  _register_system_cron && CRON_DONE=1
fi
if [ "$CRON_DONE" = "0" ]; then
  warn "当前环境无法自动注册定时任务（可能在 OpenClaw 对话中运行）"
fi

# 始终生成 install-cron.sh 备用
_write_install_cron

# ── 6. 健康检查 ───────────────────────────────────────────────────────────
log "运行健康检查..."
WORKSPACE="$WORKSPACE" bash "$WORKSPACE/scripts/health-check.sh" || {
  warn "健康检查有 ERR，可在 OpenClaw 里执行 /health-check 查看详情"
}

# ── 7. 完成提示 ───────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}✅ 文件部署完成！${NC}"
echo ""
echo "一、请在 OpenClaw → Settings → Workspace 中设置路径为："
echo "    $WORKSPACE"
echo ""

if [ "$CRON_DONE" = "1" ]; then
  echo "二、定时任务已自动注册完成 ✅"
else
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "⚠️  定时任务待注册（deploy 在 OpenClaw 对话中运行时属正常情况）"
  echo ""
  echo "在 OpenClaw 对话中，粘贴以下指令让 AI 完成注册："
  echo ""
  echo "  请执行以下两条 OpenClaw cron 命令注册定时任务："
  echo ""
  echo "  exec: openclaw cron add \\"
  echo "    --name \"memory-evolution\" \\"
  echo "    --cron \"0 0 * * *\" --tz \"UTC\" \\"
  echo "    --session isolated \\"
  echo "    --message \"执行记忆进化：exec: WORKSPACE=$WORKSPACE python3 $WORKSPACE/scripts/evolve.py\" \\"
  echo "    --delivery none"
  echo ""
  echo "  exec: openclaw cron add \\"
  echo "    --name \"weekly-self-reflection-trigger\" \\"
  echo "    --cron \"0 9 * * 1\" --tz \"UTC\" \\"
  echo "    --session main \\"
  echo "    --system-event \"weekly-self-reflection scheduled trigger\" \\"
  echo "    --wake now"
  echo ""
  echo "  或直接在终端运行：bash $WORKSPACE/scripts/install-cron.sh"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

echo ""
echo "三、在 OpenClaw 里新建一个对话，粘贴以下「激活提示词」："
echo "------------------------------------------------------------"
cat << 'PROMPT_EOF'
请读取以下文件完成初始化：
IDENTITY.md、AGENTS.md、memory/core.md、
memory/project.md、memory/recent.md、memory/errors.md
以及 skills/ 下所有文件。

读取完成后，请依次问我以下问题：

[关于我]
1. 给我起个名字 — 你想叫什么？
2. 我的性格风格 — 直接/温和/幽默/严谨，或自由描述
3. 有什么口头禅或特别习惯吗？（没有可跳过）

[关于你]
4. 你叫什么？你在哪个时区？
5. 你的工作场景和日常使用偏好是什么？
6. 你希望我重点协助哪些方面？

收集完以上信息后，请：
- 将助手设定写入 IDENTITY.md
- 将用户信息写入 memory/core.md
- 执行 /remember 和 /session-notes

完成初始化后，请检查 OpenClaw cron 定时任务是否已注册：
  exec: openclaw cron list

若输出中不包含 memory-evolution 和 weekly-self-reflection-trigger，
请自动执行以下注册（将 WORKSPACE 替换为实际路径）：

  exec: openclaw cron add \
    --name "memory-evolution" \
    --cron "0 0 * * *" --tz "UTC" \
    --session isolated \
    --message "执行记忆进化：exec: WORKSPACE=WORKSPACE_PATH python3 WORKSPACE_PATH/scripts/evolve.py，完成后静默结束" \
    --delivery none

  exec: openclaw cron add \
    --name "weekly-self-reflection-trigger" \
    --cron "0 9 * * 1" --tz "UTC" \
    --session main \
    --system-event "weekly-self-reflection scheduled trigger" \
    --wake now

注册完成后再次运行 openclaw cron list 确认，
然后做一个简短的自我介绍，确认全部初始化完成。
PROMPT_EOF
echo "------------------------------------------------------------"
echo ""
echo "定时任务当前状态："
if command -v openclaw &>/dev/null; then
  openclaw cron list 2>/dev/null | grep -E "memory-evolution|weekly-self-reflection" || \
    echo "  （未注册，请参考上方说明）"
elif command -v crontab &>/dev/null; then
  crontab -l 2>/dev/null | grep -E "memory-evolution|weekly-self-reflection" || \
    echo "  （未注册，请运行 bash $WORKSPACE/scripts/install-cron.sh）"
else
  echo "  （无调度工具，请在 OpenClaw 对话中执行激活提示词里的 cron 注册步骤）"
fi
