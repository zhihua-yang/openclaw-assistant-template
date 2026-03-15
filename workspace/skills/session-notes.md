# /session-notes

每次会话结束时自动静默执行（由 AGENTS.md 自动规则触发）。

## 执行步骤

1. 将本次会话摘要写入：
   ~/.openclaw/workspace/.sys/sessions/YYYY-MM-DD.md

2. 将结构化事件追加到 events.jsonl：
   ~/.openclaw/workspace/.sys/logs/events.jsonl

   强制规范（必须遵守）：
   - 字段名用 tags（不是 tag）
   - ts 必须带 UTC 时区（+00:00）
   - type 必须从以下 14 个标准类型中选，不可自造
   - content 字数须达到对应类型的最低要求
   - tags 至少 1 个

   推荐写法（使用 create_event.py，自动保证所有质量标准）：
   exec: python3 ~/.openclaw/workspace/scripts/create_event.py \
     --type learning-achievement \
     --content "详细描述学习内容、过程、收获和应用场景..."

   14个标准 type：
   task-done / error-found / system-improvement / learning-achievement /
   user-correction / automation-deployment / error-fix / system-monitoring /
   quality-verification / new-capability / automation-planning /
   memory-compaction / pua-inspection / quality-improvement

   内容最低字数（中文每15字符约1单元）：
   - learning-achievement: >= 15 单元
   - user-correction / system-improvement: >= 10 单元
   - task-done / error-found: >= 8 单元
   - 其他类型: >= 5 单元

3. 若本次会话有明显失误：
   - 检查 memory/errors.md 是否有同类条目
   - 有 -> 更新出现次数 +1，若 >= 2 次改状态为 pending
   - 无 -> 新增条目，状态为 monitoring
   - 不重复新增同类错误，只累计次数

4. 执行 /remember，更新 memory/recent.md 和 memory/project.md
