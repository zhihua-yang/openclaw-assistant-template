# Agent Identity & Rules

## 初始化流程
启动时读取以下文件完成上下文加载（按顺序）：
1. IDENTITY.md
2. AGENTS.md
3. memory/core.md
4. memory/project.md
5. memory/recent.md
6. memory/errors.md
7. skills/ 下所有文件

---

## 核心行为规则
- 回答前先检查 memory/recent.md 是否有相关历史
- 执行文件操作前确认路径
- 遇到不确定内容，先问清楚再行动
- 代码修改前说明改动范围

---

## /session-notes 实现规范

`/session-notes` 不是概念标签，必须通过以下脚本真正执行。

### 标准调用方式

```
exec: python3 ~/.openclaw/workspace/scripts/session_note_writer.py   --summary   "本次会话摘要（自然语言，简明扼要）"   --type      task-done   --content   "完成的具体内容，中文不少于120字符"   --tags      task-completion,progress   [--error    "发现的错误描述（可选）"]
```

### 脚本完成的4个步骤（缺一不可）
1. 写会话摘要 → `.sys/sessions/YYYY-MM-DD.md`（同时写 `.openclaw/sessions/`）
2. 追加结构化事件 → `.sys/logs/events.jsonl`
3. 若有错误 → 更新 `memory/errors.md`
4. 触发 `/remember` → 更新 `memory/recent.md`

---

## 事件写入规范（强制执行）

每条写入 `events.jsonl` 的事件必须符合：

```json
{
  "ts":      "2026-03-17T00:00:00+00:00",
  "type":    "<标准类型>",
  "content": "<详细描述>",
  "tags":    ["tag1", "tag2"],
  "count":   1
}
```

**强制要求：**
- 字段名必须用 `tags`（不是 `tag`）
- `ts` 必须带 UTC 时区偏移（`+00:00`）
- `type` 必须从标准列表中选取（共14个）
- `tags` 至少 1 个

**推荐使用 create_event.py 单独写入事件：**
```
exec: python3 ~/.openclaw/workspace/scripts/create_event.py   --type learning-achievement   --content "详细描述..."
```

### 标准 type 枚举（14个，不可自造）

| type | 说明 | 最低字数 |
|---|---|---|
| task-done | 完成任务 | 8单元 |
| error-found | 发现错误 | 8单元 |
| system-improvement | 系统改进 | 10单元 |
| learning-achievement | 学习成就 | 15单元 |
| user-correction | 用户纠正 | 10单元 |
| automation-deployment | 自动化部署 | 5单元 |
| error-fix | 错误修复 | 5单元 |
| system-monitoring | 系统监控 | 5单元 |
| quality-verification | 质量验证 | 5单元 |
| new-capability | 新能力（兼容旧数据） | 5单元 |
| automation-planning | 自动化规划 | 5单元 |
| memory-compaction | 内存压缩 | 5单元 |
| pua-inspection | 深度检查 | 5单元 |
| quality-improvement | 质量改进 | 5单元 |

> 字数单元：中文每15字符≈1单元；英文按单词数计算。

---

## 自动规则

### 规则1：会话结束告别词自动触发

检测到以下告别词时，**立即静默执行 /session-notes，不输出任何过程提示，直接回告别语**。

**检测方式（优先使用脚本）：**
```
exec: python3 ~/.openclaw/workspace/scripts/farewell_detector.py   --text      "<用户最后一句话>"   --auto-trigger   --summary   "<本次会话摘要>"   --type      task-done   --content   "<本次完成的内容>"   --tags      session,auto-close
```

**告别词列表（35+种）：**
- 中文：再见、拜了、拜拜、先这样、下次再说、结束、退出、88、886、晚安、
        好的再见、就这样吧、暂时这样、今天就到这、先到这里、告一段落、
        下线了、去忙了、忙去了、有空再聊、回头见、待会见、改天聊、先聊到这
- 英文：bye、goodbye、see you、see ya、later、quit、done、that's all、
        good night、gotta go、gtg、ttyl、talk later、take care、signing off

### 规则2：启动时检查周报触发信号

启动时检查 `events.jsonl` 最近一条是否包含：
- `type: task-done`
- `tags` 包含 `"weekly"`
- `content: "weekly-self-reflection scheduled trigger"`

若存在且距今不超过 24 小时，自动执行 `/weekly-self-reflection`。

### 规则3：路径双写兼容

所有文件操作同时兼容以下两个路径，以存在且非空的为准：
- `~/.openclaw/workspace/.sys/logs/events.jsonl`
- `~/.openclaw/workspace/.openclaw/logs/events.jsonl`

`session_note_writer.py` 和 `evolve.py` 均已内置自动探测逻辑，无需手动指定。

---

## 记忆管理规则
- 每次对话结束执行 `/session-notes`（通过 `session_note_writer.py` 真正写入）
- 重要学习立即通过 `create_event.py` 写入 `events.jsonl`
- 用户纠正立即记录（type: user-correction）
- `evolve.py` 每天 00:00 自动整理近7天事件到 `memory/recent.md`
