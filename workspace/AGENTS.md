# Agent Identity & Rules

## 初始化流程
启动时读取以下文件完成上下文加载：
1. IDENTITY.md
2. memory/core.md
3. memory/project.md
4. memory/recent.md
5. memory/errors.md
6. skills/ 下所有文件

## 核心行为规则
- 回答前先检查 memory/recent.md 是否有相关历史
- 执行文件操作前确认路径
- 遇到不确定的内容，先问清楚再行动
- 代码修改前说明改动范围

## 事件写入规范（强制执行）

### 标准字段
每条写入 events.jsonl 的事件必须包含：
```json
{
  "ts": "2026-03-15T00:00:00+00:00",
  "type": "<标准类型>",
  "content": "<详细描述，不少于规定字数>",
  "tags": ["tag1", "tag2"],
  "count": 1
}
```

注意：
- 字段名必须用 **tags**（不是 tag）
- ts 必须带 UTC 时区偏移（+00:00）
- type 必须从以下标准列表中选取

### 标准 type 枚举（14个，不可自造）
- task-done              完成任务
- error-found            发现错误
- system-improvement     系统改进
- learning-achievement   学习成就（内容 >= 15个概念单元）
- user-correction        用户纠正（内容 >= 10个概念单元）
- automation-deployment  自动化部署
- error-fix              错误修复
- system-monitoring      系统监控
- quality-verification   质量验证
- new-capability         新能力（兼容旧数据，新增请用 learning-achievement）
- automation-planning    自动化规划
- memory-compaction      内存压缩
- pua-inspection         深度检查
- quality-improvement    质量改进

### 内容最低字数要求
- learning-achievement：>= 15个概念单元（中文每15字符≈1单元）
- user-correction：>= 10个概念单元
- task-done / error-found：>= 8个概念单元
- system-improvement：>= 10个概念单元
- 其他类型：>= 5个概念单元

### Tags 强制要求
- 每条事件必须有至少 1 个 tag
- 使用 create_event.py 创建事件可自动生成 tags

## 记忆管理规则
- 每次对话结束执行 /session-notes
- 重要学习立即写入 memory/recent.md
- 用户纠正立即记录到 events.jsonl

## 自动规则

### 会话结束自动触发
检测到以下告别词时，自动静默执行 /session-notes 全部步骤，
不输出任何提示，直接回告别语：
- 中文：再见、拜了、先这样、下次再说、结束、退出、88
- 英文：bye、goodbye、see you、later、quit、done

### 启动时检查周报触发信号
启动时检查 events.jsonl 最近一条是否包含：
- type: task-done
- tags 包含 "weekly"
- content: "weekly-self-reflection scheduled trigger"

若存在且距今不超过 24 小时，自动执行 /weekly-self-reflection。

### 执行顺序
1. 写会话日志到 .sys/sessions/
2. 追加结构化事件到 .sys/logs/events.jsonl
3. 更新 memory/errors.md（有失误时）
4. 执行 /remember 更新 memory/recent.md
