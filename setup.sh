#!/bin/bash
# ============================================================
# OpenClaw 内网数字助手 — 一键部署脚本 v3.4
# 用法：
#   bash setup.sh                 # 安装到 ~/.openclaw/workspace
#   bash setup.sh /custom/path    # 安装到自定义路径
#   bash setup.sh --force         # 强制重装（覆盖已有数据）
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

# 1. 基本检查
[ -d "$TEMPLATE_DIR" ] || fail "找不到 workspace/ 目录，请确认仓库结构正确"
command -v python3 &>/dev/null || fail "python3 未安装，请先安装后重试"

log "模板目录：$TEMPLATE_DIR"
log "目标 workspace：$WORKSPACE"

# 2. 拷贝模板文件（检测已有数据，避免覆盖）
if [ -f "$WORKSPACE/.sys/logs/events.jsonl" ] && [ -s "$WORKSPACE/.sys/logs/events.jsonl" ] && [ "$FORCE" = "0" ]; then
  warn "检测到已有数据，跳过模板覆盖（如需强制重装请加 --force 参数）"
else
  log "复制 workspace/ 到目标目录..."
  mkdir -p "$WORKSPACE"
  cp -r "$TEMPLATE_DIR"/. "$WORKSPACE"/
fi

# 3. 初始化运行时目录（.sys）和 memory/archive
log "初始化运行时目录 (.sys)..."
mkdir -p "$WORKSPACE/.sys/sessions"
mkdir -p "$WORKSPACE/.sys/logs"
mkdir -p "$WORKSPACE/.sys/baseline"
mkdir -p "$WORKSPACE/.sys/todo"
mkdir -p "$WORKSPACE/.sys/compact"
mkdir -p "$WORKSPACE/memory/archive"

touch "$WORKSPACE/.sys/logs/events.jsonl"
[ -f "$WORKSPACE/.sys/logs/last_evolution_line.txt" ] || echo "0" > "$WORKSPACE/.sys/logs/last_evolution_line.txt"

# 4. 脚本执行权限
log "设置脚本执行权限..."
chmod +x "$WORKSPACE/scripts/"*.sh 2>/dev/null || true
chmod +x "$WORKSPACE/scripts/evolve.py" 2>/dev/null || true
chmod +x "$WORKSPACE/scripts/create_event.py" 2>/dev/null || true   # v3.4 新增

# 5. 注册 crontab 定时任务
log "注册 crontab 定时任务..."

CRON_EVOLUTION="0 0 * * * WORKSPACE=$WORKSPACE python3 $WORKSPACE/scripts/evolve.py >> $WORKSPACE/.sys/logs/cron-memory-evolution.log 2>&1"
# v3.4 修复：字段名从 "tag" 改为 "tags"，与 events.jsonl 规范一致
CRON_REFLECTION="0 9 * * 1 echo '{\"ts\":\"$(date -Iseconds)\",\"type\":\"task-done\",\"tags\":[\"cron\",\"weekly\"],\"content\":\"weekly-self-reflection scheduled trigger\",\"count\":1}' >> $WORKSPACE/.sys/logs/events.jsonl"

(
  crontab -l 2>/dev/null | grep -v "cron-memory-evolution\|weekly-self-reflection"
  echo "$CRON_EVOLUTION"
  echo "$CRON_REFLECTION"
) | crontab -

# 验证
if crontab -l 2>/dev/null | grep -q "cron-memory-evolution"; then
  log "crontab 验证成功：memory-evolution 已注册（每天 00:00）"
else
  warn "memory-evolution 注册失败，请手动执行：crontab -e"
fi

if crontab -l 2>/dev/null | grep -q "weekly-self-reflection"; then
  log "crontab 验证成功：weekly-self-reflection 已注册（每周一 09:00）"
else
  warn "weekly-self-reflection 注册失败，请手动执行：crontab -e"
fi

# 6. 快速健康检查
log "运行健康检查脚本..."
WORKSPACE="$WORKSPACE" bash "$WORKSPACE/scripts/health-check.sh" || {
  warn "健康检查有 ERR，可在 OpenClaw 里执行 /health-check 查看详情"
}

echo ""
echo -e "${GREEN}✅ 部署完成！${NC}"
echo ""
echo "一、请在 OpenClaw → Settings → Workspace 中设置路径为："
echo "    $WORKSPACE"
echo ""
echo "二、在 OpenClaw 里新建一个对话，粘贴以下「激活提示词」："
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

完成后请验证定时任务状态：
exec: crontab -l | grep -E "memory-evolution|weekly-self-reflection"

将验证结果告诉我，然后做一个简短的自我介绍，确认全部初始化完成。
PROMPT_EOF
echo "------------------------------------------------------------"
echo ""
echo "你可以："
echo "  1. 复制以上提示词到 OpenClaw 对话；"
echo "  2. 或者直接把本 setup.sh 文件拖给 OpenClaw，让它按步骤执行。"
echo ""
echo "定时任务状态（当前）："
crontab -l 2>/dev/null | grep -E "memory-evolution|weekly-self-reflection" || echo "  （未检测到，请查看上方警告）"
