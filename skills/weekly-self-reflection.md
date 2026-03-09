# skill: weekly-self-reflection
## 执行步骤（每周一 cron 触发）
1. 读取最近 7 天的 session notes：
   exec: ls $WORKSPACE/.openclaw/sessions/
2. 读取 memory/recent.md 与 memory/project.md
3. 生成一份「本周复盘」草稿，内容包括：
   - 做对了什么（要坚持）
   - 做错了什么（要避免）
   - 哪些规则已经过时/不适用
   - 有没有安全风险需要收紧
4. 基于复盘生成 AGENTS.md 修改建议（Level 2）：

=== 建议修改 AGENTS.md ===
--- 当前规则
+++ 建议规则
原因：[为什么改]
风险：[副作用]
建议验证：[怎么验证没问题]

请回复"确认修改"或"拒绝修改"。
===
5. 等待用户确认后，按 Level 3 执行或放弃。
6. 将本周复盘概要写入 memory/project.md，便于长期追踪。