# /session-notes

每次会话结束时自动静默执行（由 AGENTS.md 自动规则触发）。

## ⚠️ 重要：这是真实执行，不是描述

`/session-notes` 必须通过 `session_note_writer.py` 脚本真正写入文件，
不能只是在对话中"描述"要做什么。

## 标准执行命令

```
exec: python3 ~/.openclaw/workspace/scripts/session_note_writer.py \
  --summary   "本次会话摘要（自然语言）" \
  --type      task-done \
  --content   "完成的具体内容，中文不少于120字符" \
  --tags      task-completion,progress \
  --error     "发现的错误（无则省略此行）"
```

## 脚本完成的4个步骤

1. **写会话日志** → `.sys/sessions/YYYY-MM-DD.md` + `.openclaw/sessions/YYYY-MM-DD.md`（双路径）
2. **追加结构化事件** → `.sys/logs/events.jsonl`（自动探测路径）
3. **更新 errors.md** → 有错误时自动新增或累计次数
4. **触发 /remember** → 在 `memory/recent.md` 写入时间戳标记

## 告别词自动触发方式

```
exec: python3 ~/.openclaw/workspace/scripts/farewell_detector.py \
  --text "<用户最后说的话>" \
  --auto-trigger \
  --summary "..." \
  --type task-done \
  --content "..."
```

## type 选择参考

| 本次会话主要内容 | 推荐 type |
|---|---|
| 完成了任务/功能 | task-done |
| 发现了 bug / 问题 | error-found |
| 修复了 bug | error-fix |
| 学习了新知识 | learning-achievement |
| 用户纠正了 AI | user-correction |
| 系统配置改进 | system-improvement |
