# AGENTS.md — OpenClaw v3.11.1-Lite

> 本文件定义 AI Agent 在此工作区的行为规范。升级时末尾追加，不覆盖原有内容。

---

## 基础行为规范（v3.6 沿用）

### 工作区结构
- 所有持久数据存放在 `memory/` 目录
- 脚本文件存放在 `scripts/` 目录
- 日志文件存放在 `.sys/logs/` 目录
- `IDENTITY.md` 是身份锚点文件，任何情况下不修改、不删除

### 响应原则
- 优先读取 `memory/recent.md` 作为上下文起点
- **【强制】任务完成后，在发送最终回复之前，必须先调用 `create_event.py` 记录事件。录入是任务的组成部分，不是可选收尾。未录入 = 任务未完成。**
- 不主动修改 `memory/` 下的 JSON 文件（通过脚本操作）
- 遇到不确定的技术问题，优先查 `memory/errors.md`

### 事件记录时机
- 完成一个明确的技术任务后 → `task-done`
- 发现并修复 bug 后 → `error-fix`
- 被用户指出错误后 → `user-correction`
- 收到明确正向反馈后 → `user-positive-feedback`
- 完成系统性改进后 → `system-improvement`

---

## 自主进化系统（v3.11.1-Lite）

本实例运行 OpenClaw v3.11.1-Lite 自主进化方案，在 v3.7 基础上新增三维成长指数、能力追踪、审计系统和元认知校准。

### Cron 执行顺序（每日）

```

00:05  audit_events.py      — 诊断扫描，输出 audit_queue.jsonl（不改分）
00:15  daily_digest.py      — 更新 recent_digest.json（上下文注入源）
00:20  evolve.py            — 计分、状态更新、evolution_chain 追加
09:00  weekly_reflection.py — 周一执行：周报 + decay penalty + 训练计划

```

### 核心文件说明

| 文件 | 类型 | 说明 |
|---|---|---|
| `memory/evolution_chain.jsonl` | 主数据 | 所有事件 + 进化节点（append-only）|
| `memory/capabilities.json` | 主数据 | 能力对象库（四阶段状态）|
| `memory/intelligence_index.json` | 主数据 | IQ/EQ/FQ 三维指数快照 |
| `memory/audit_queue.jsonl` | 状态机 | 诊断队列（pending/adopted/dismissed/expired）|
| `memory/recent_digest.json` | 摘要 | 近7天摘要，上下文注入白名单 |
| `memory/weekly_summary.json` | 摘要 | 周统计快照，每周更新 |
| `memory/training_plan.json` | 建议 | 规则生成训练建议，每周更新 |
| `memory/calibration.json` | 校准 | 元认知校准统计，每月滚动 |
| `memory/profile.json` | 配置 | 个性化参数 + LLM 预算开关 |
| `memory/goals.json` | 目标 | 三层目标（结果/能力/训练）|
| `memory/recent.md` | 展示 | v3.7 保留，仍可查阅 |
| `memory/errors.md` | 展示 | v3.7 保留，仍可查阅 |
| `memory/growth.md` | 展示 | v3.7 保留，降为只读展示层 |

### 三维成长指数

| 指数 | 含义 | 核心驱动事件 |
|---|---|---|
| **IQ** 智识指数 | 解决新问题的能力 | error-fix、learning-achievement、capability-reuse |
| **EQ** 执行指数 | 与用户协作的质量 | user-positive-feedback（+）、user-correction（-）|
| **FQ** 频率指数 | 稳定执行的密度 | task-done（受日限和递减约束）|

### 能力状态机

```

observed → declared → standard_verified → strong_verified

```

- `standard_verified`：至少 1 次成功复用
- `strong_verified`：总复用 ≥ 3，near ≥ 2，far ≥ 1（跨场景迁移验证）
- 只有 `strong_verified` 能力可通过 `export_capabilities.py` 导出

---

## 事件录入命令

### 最小模式（evidence 缺省 self）

```bash
python3 scripts/create_event.py \
  --type task-done \
  --content "完成 xxx" \
  --task-type yyy
```


### 完整模式

```bash
python3 scripts/create_event.py \
  --type task-done \
  --content "完成 xxx" \
  --task-type yyy \
  --difficulty stretch \
  --confidence medium \
  --evidence external \
  --evidence-ref "log:xxx" \
  --cap cap_yyy
```


### 刻意练习

```bash
python3 scripts/create_event.py \
  --type intentional-challenge \
  --content "挑战：在新场景下独立完成 xxx" \
  --difficulty novel \
  --challenge-type transfer \
  --outcome success \
  --cap cap_yyy
```


### 错误驱动学习（必须有 --cognitive-update 和 --parent）

```bash
python3 scripts/create_event.py \
  --type learning-achievement \
  --content "理解了 xxx 的根因" \
  --trigger error-driven \
  --cognitive-update "原来 xxx 是因为 yyy，之前误解了" \
  --parent evt-xxxxxxxx-xxxxxx
```


### 能力复用（far transfer）

```bash
python3 scripts/create_event.py \
  --type capability-reuse \
  --content "将 cap_log_analysis 迁移到新场景" \
  --cap cap_log_analysis \
  --transfer far \
  --parent evt-xxxxxxxx-xxxxxx
```


### 错误相关

```bash
# 发现错误
python3 scripts/create_event.py \
  --type error-found \
  --content "发现 xxx 问题" \
  --task-type yyy \
  --cap cap_yyy

# 修复错误
python3 scripts/create_event.py \
  --type error-fix \
  --content "修复 xxx，根因是 yyy" \
  --task-type yyy \
  --evidence external \
  --evidence-ref "log:xxx" \
  --cap cap_yyy
```


### 事件类型完整清单

```bash
# 查看所有可用事件类型
python3 scripts/create_event.py --list-types

# 预览事件（不写入）
python3 scripts/create_event.py --type task-done --content "xxx" --dry-run
```

**事实事件（fact）：**
`task-done` / `error-fix` / `error-found` / `task-rework` /
`user-correction` / `user-positive-feedback` / `system-improvement` / `intentional-challenge`

**派生事件（derived）：**
`learning-achievement` / `capability-reuse` / `capability-status-change` /
`antipattern-extracted` / `reputation-recovered` / `capability-decay-penalty` / `milestone-unlocked`

**字段取值参考：**


| 字段 | 可选值 | 缺省值 |
| :-- | :-- | :-- |
| `--difficulty` | `routine` / `stretch` / `novel` | `routine` |
| `--confidence` | `high` / `medium` / `low` | 可不填 |
| `--evidence` | `external` / `logical` / `self` | `self` |
| `--transfer` | `near` / `far` | `near` |
| `--trigger` | `normal` / `error-driven` / `challenge-driven` | `normal` |
| `--challenge-type` | `consolidate` / `stretch` / `transfer` | 可不填 |
| `--outcome` | `success` / `partial` / `fail` | 可不填 |

> ⚠️ `--evidence logical` 只能由系统基于事实链自动推断，**不允许手动填写**。

---

## 审计处理命令

```bash
# 查看所有 pending 建议
python3 scripts/resolve_audit.py --list

# 采纳建议（采纳后请用 create_event.py 录入对应派生事件）
python3 scripts/resolve_audit.py --adopt diag-xxxxxxxx-xxxxxx

# 忽略建议
python3 scripts/resolve_audit.py --dismiss diag-xxxxxxxx-xxxxxx

# 批量过期超 7 天未处理的建议
python3 scripts/resolve_audit.py --expire-old
```


### 审计建议类型

| 诊断类型 | 触发条件 | 建议操作 |
| :-- | :-- | :-- |
| `stagnation-warning` | 连续 3 天无 learning-achievement | 补录 learning-achievement |
| `suspected-missing-learning` | task-done 含学习关键词但无派生 | 考虑补录 learning-achievement |
| `repeat-error-alert` | 7 天内同类错误重复 ≥ 2 | 复盘根因，录入 antipattern |
| `comfort-zone-warning` | routine > 70%（近30天） | 安排 stretch 任务 |
| `overconfidence-warning` | 高置信失败率 > 15% | 注意校准，降低预判置信度 |
| `underconfidence-warning` | 低置信成功率 > 25% | 更信任自己的能力 |
| `plateau-detected` | 连续 3 周净增长 < 0.3 | 增加 intentional-challenge |
| `breakthrough-detected` | 单周净增长 > 8周均值 2 倍 | 记录突破原因，强化该路径 |


---

## 系统操作命令

```bash
# 手动触发进化（计分引擎）
python3 scripts/evolve.py

# 手动触发审计扫描
python3 scripts/audit_events.py

# 更新每日摘要
python3 scripts/daily_digest.py

# 预览周报（不写入）
python3 scripts/weekly_reflection.py --dry-run

# 执行周报（写入文件）
python3 scripts/weekly_reflection.py

# 导出 strong_verified 能力
python3 scripts/export_capabilities.py
```


### 日志查看

```bash
cat .sys/logs/cron-audit.log
cat .sys/logs/cron-digest.log
cat .sys/logs/cron-memory-evolution.log
cat .sys/logs/weekly-reflection.log
```


---

## 计分规则速查

### 证据等级系数

| 等级 | 系数 | 说明 |
| :-- | :-- | :-- |
| `external` | 1.0 | 有外部可验证证据（日志、截图等） |
| `logical` | 0.7 | 系统自动推断，不可手动填写 |
| `self` | 0.2 | 自我声明，只进 EQ_process，不直接改 IQ/FQ |

### 边际递减（阻力系数）

```
resistance_factor = max(0.1, (100 - current_score) / 50)
```

| 当前分数 | 阻力系数 |
| :-- | :-- |
| 50 | 1.0 |
| 70 | 0.6 |
| 90 | 0.2 |
| 95+ | 0.1（下限） |

### 关键约束

- 单链增益上限：`+0.6`（同一 task_id 所有事件合计）
- 单链减益上限：`-0.6`
- 派生事件增益 ≤ 主事件绝对值的 50%
- 同 task_type 同日最多 2 次常规 task-done 参与 FQ 计分
- **负向扣分不乘阻力系数**（不打折）
- `capability-decay-penalty` 只由 `weekly_reflection.py` 触发，不由 `evolve.py` 每日生成
- `diagnostic` 事件永不直接写指数分

---

## 核心设计原则

1. **diagnostic 永不直接改分** — 诊断只记录，由人工 adopt 后创建派生事件才可改分
2. **evidence_level 缺省 self** — `logical` 只能由系统推断，不允许手动填写
3. **正向增长受边际递减约束** — 分数越高，同等事件的增益越小
4. **负向扣分不打折** — user-correction / task-rework 不乘阻力系数
5. **strong_verified 需跨场景迁移** — near ≥ 2 且 far ≥ 1，不能只靠相似场景重复
6. **模型参与面极小** — 每周最多 2–5 次模型调用，其余全部规则化
7. **capability-decay-penalty 只由 weekly 触发** — 防止每日重复累计扣分
8. **样本充足度按数量判断** — task-done ≥ 15 条，不按天数
9. **JSON 是主源，Markdown 是导出物** — 脚本只读写 JSON，Markdown 只用于展示

---

## 上下文注入白名单

任务态调用模型时，**只允许**注入以下内容：

```
✅ 当前任务结构化描述
✅ 相关 capability 最多 3 条（精确匹配或本地 TF-IDF，不调用外部 API）
✅ 相关 antipattern 最多 3 条
✅ recent_digest.json 全量
✅ 当前目标差距摘要 1 条
✅ 当月校准概要 1 行（来自 calibration.json）
```

**禁止**注入：

```
❌ 全量 evolution_chain.jsonl
❌ 全量 growth.md / capabilities.md / audit.md
❌ 近 30 天事件全文
❌ 全量 weekly_summary.json 历史
```


---

## LLM 调用预算

| 场景 | 频率 | 开关字段 |
| :-- | :-- | :-- |
| 周报润色 | 1 次/周 | `allow_weekly_report_llm_rewrite` |
| 训练建议润色 | 1 次/周 | `allow_training_plan_llm_rewrite` |
| 高价值错误认知提炼 | 0–3 次/周 | `allow_error_fix_llm_extraction` |
| 日常事件写入 | 0 | 不允许 |
| 计分判断 | 0 | 不允许 |
| 审计规则扫描 | 0 | 不允许 |

**推荐预算：每周 2–5 次。** 可在 `memory/profile.json` 中调整：

```json
{
  "allow_weekly_report_llm_rewrite": true,
  "allow_training_plan_llm_rewrite": true,
  "allow_error_fix_llm_extraction": true,
  "allow_daily_llm_summary": false,
  "weekly_llm_call_budget": 4
}
```


---

## 保护文件（升级不覆盖）

以下文件在任何版本升级中**不得覆盖**：

```
IDENTITY.md
memory/capabilities.json
memory/antipatterns.json
memory/intelligence_index.json
memory/evolution_chain.jsonl
memory/audit_queue.jsonl
memory/profile.json
memory/goals.json
```


---

## 健康检查（快速验证）

```bash
# 验证核心脚本可运行
python3 scripts/create_event.py --list-types
python3 scripts/evolve.py
python3 scripts/weekly_reflection.py --dry-run
python3 scripts/audit_events.py
python3 scripts/daily_digest.py

# 验证文件锁依赖
python3 -c "from filelock import FileLock; print('✅ filelock OK')"

# 验证 profile.json 关键字段
python3 -c "
import json
p = json.load(open('memory/profile.json'))
assert p.get('evidence_default') == 'self', '❌ evidence_default 不是 self'
assert 'sample_sufficient_min_task_done' in p, '❌ 缺少 sample_sufficient_min_task_done'
print('✅ profile.json 字段正确')
"
```


---

## 版本历史

| 版本 | 日期 | 主要变更 |
| :-- | :-- | :-- |
| v3.6 | — | 基础事件记录、evolve.py、cron |
| v3.7 | — | 修复 setup.sh 路径、新增 weekly_reflection.py、growth.md、中文支持修复 |
| v3.11.1-Lite | 2026-03-22 | 三维指数、能力状态机、审计系统、元认知校准、文件锁安全、边际递减、30项健康检查 |


---
