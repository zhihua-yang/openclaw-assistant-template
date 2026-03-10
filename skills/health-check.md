# skill: health-check
## 触发条件
- /memory-evolution 和 /weekly-self-reflection 执行后自动触发
- /rollback 执行后自动触发
- 主人主动执行 /health-check

## 执行步骤
exec: bash ${WORKSPACE}/scripts/health-check.sh

## 输出格式
OK/ERR 逐项报告，发现问题时输出具体修复建议
