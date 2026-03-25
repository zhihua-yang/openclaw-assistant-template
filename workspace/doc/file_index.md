<!-- 本文件：memory/ 目录文件索引，在需要查阅数据文件用途时由 AGENTS.md 索引调用 -->

# memory/ 文件索引

## 核心数据文件（主源，JSON 格式）

| 文件 | 类型 | 说明 | 谁在写 | 谁在读 |
|---|---|---|---|---|
| `evolution_chain.jsonl` | Append-only | 所有事件 + 进化节点完整日志 | create_event.py | evolve.py, audit_events.py |
| `capabilities.json` | 主表 | 能力对象库（4 阶段状态） | evolve.py | weekly_reflection.py, export_capabilities.py |
| `intelligence_index.json` | 快照 | IQ/EQ/FQ 三维指数当前分数 + 历史 | evolve.py | 模型上下文注入 |
| `audit_queue.jsonl` | 状态机 | 诊断建议队列（pending/adopted/dismissed/expired） | audit_events.py | resolve_audit.py |
| `profile.json` | 配置 | 个性化参数、LLM 预算开关、计分权重 | 手动编辑 | 所有脚本 |
| `goals.json` | 目标 | 三层目标（结果/能力/训练） | 手动编辑 | weekly_reflection.py, 模型注入 |

---

## 摘要文件（导出物）

| 文件 | 说明 | 谁在写 | 刷新周期 |
|---|---|---|---|
| `recent_digest.json` | 近 7 天精简摘要（**上下文注入白名单**） | daily_digest.py | 每天 00:15 |
| `weekly_summary.json` | 周统计快照（指数变化、事件分布） | weekly_reflection.py | 每周一 09:00 |
| `training_plan.json` | 规则生成的训练建议 | weekly_reflection.py | 每周一 09:00 |
| `calibration.json` | 元认知校准统计（预判准确度） | weekly_reflection.py | 每月滚动 |

---

## 展示文件（只读，Markdown 格式）

| 文件 | 说明 | 用途 |
|---|---|---|
| `recent.md` | v3.7 保留，当前周事件摘要 | 查看最近发生了什么 |
| `growth.md` | v3.7 保留，降为只读展示层 | 历史参考 |
| `errors.md` | 已知错误和解决方案 | 问题排查参考 |

---

## 模型访问权限

### ✅ 允许读取
```
recent_digest.json   — 每天同步，含最新摘要
recent.md            — 查询上下文
errors.md            — 问题排查
goals.json           — 理解目标差距
相关 capability ≤ 3 条（精确匹配）
相关 antipattern ≤ 3 条（精确匹配）
```

### ❌ 禁止读取
```
evolution_chain.jsonl   — 全量太大
capabilities.json       — 全表数据
intelligence_index.json — 直接读分数
audit_queue.jsonl       — 诊断队列
.sys/logs/              — 系统日志
```

---

## 常见查阅场景

```bash
# 查看当前指数分
cat memory/intelligence_index.json | jq '.current'

# 查看上周统计
cat memory/weekly_summary.json | jq '.last_week'

# 搜索错误历史
grep "关键词" memory/errors.md

# 查看 pending 审计建议
python3 scripts/resolve_audit.py --list

# 导出 strong_verified 能力
python3 scripts/export_capabilities.py
```

---

## profile.json 关键字段

```json
{
  "evidence_default": "self",
  "allow_weekly_report_llm_rewrite": true,
  "allow_training_plan_llm_rewrite": true,
  "allow_error_fix_llm_extraction": true,
  "weekly_llm_call_budget": 4,
  "sample_sufficient_min_task_done": 15,
  "daily_task_done_limit_per_type": 2
}
```

---

## 备份与恢复

```bash
# 备份
tar czf memory_backup_$(date +%Y%m%d).tar.gz memory/

# 恢复
tar xzf memory_backup_20260325.tar.gz
```

---

## 关键提示

- **evolution_chain.jsonl 是 append-only**，不要直接编辑，所有写入通过 create_event.py
- **JSON 是主源**，Markdown 文件（recent.md / growth.md）只是导出展示，不要手动写入
- **recent_digest.json** 是模型上下文注入的唯一白名单来源，每天自动刷新
