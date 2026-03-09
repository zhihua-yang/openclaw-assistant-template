# skill: memory-evolution
## 执行步骤（每日 cron 触发）
1. 运行外部脚本（内部处理阈值与聚类判断）：
   exec: WORKSPACE=$WORKSPACE SCRIPTS=$SCRIPTS python3 ${SCRIPTS}/evolve.py
2. 根据脚本输出：
   - 输出包含 "SKIP" → 事件不足，跳过
   - 输出包含 "INFO" → 仅更新记忆，不触发规则修改
   - 输出包含 "LEVEL2" → 进入规则建议流程（仅生成 diff，不修改）
3. 如有 LEVEL2 提示，在对话中与用户确认是否执行变更：
   - 用户明确说"确认修改" → 按 AGENTS.md 的 Level 3 步骤执行
   - 用户说"拒绝修改" → 保持现状，并记录到 session notes