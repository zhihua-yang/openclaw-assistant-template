# skill: session-notes
## 执行步骤
1. 获取今日日期，追加写入 .openclaw/sessions/YYYY-MM-DD.md：
   - 做了什么
   - 遇到的问题 & 解法
   - 有哪些 TODO 留到下次
2. 根据 AGENTS.md 的事件规则，向 .openclaw/logs/events.jsonl 写事件：
   - 每条一行 JSON，含 ts/type/uuid/session_id
   - 写入前检查去重