> 本文件定义 AI Agent 在此工作区的行为规范。升级时末尾追加，不覆盖原有内容。

---

# Plan-and-Execute

**何时**：文件操作/代码编写/多步任务/任何 tool call 前必须先写计划。纯问答、解释类请求可直接回答。

**执行前**：
- 将完整的执行计划写入 `Plan-and-Execute.md`
- 格式：`- [ ] Step 1: 描述` ... `- [ ] Step N: 描述`
- 输出计划摘要后立即执行，无需等待用户确认

**执行中**：
- 每完成一步，立即在 `Plan-and-Execute.md` 中标记 `[x]`
- 输出：`✅ Step N 完成：[简要说明做了什么]`
- 然后继续下一步

**遇到问题时**：
- 输出：`⚠️ Step N 受阻：[问题描述]，建议方案：[选项]`
- 停止执行，等待用户指示

---

# 工作区结构

- 所有持久数据存放在 `memory/` 目录
- 脚本文件存放在 `scripts/` 目录
- 日志文件存放在 `.sys/logs/` 目录
- `IDENTITY.md` 是身份锚点文件，任何情况下不修改、不删除

---

# 响应原则

- **优先读取** `memory/recent.md` 作为上下文起点
- **【强制】任务完成后，发送最终回复前，必须先调用 `create_event.py` 记录事件。未录入 = 任务未完成。**
- 不主动修改 `memory/` 下的 JSON 文件（通过脚本操作）
- 遇到不确定的技术问题，优先查 `memory/errors.md`

---

# 事件记录时机

- **task-done**：完成一个明确的技术任务后
- **error-fix**：发现并修复 bug 后
- **user-correction**：被用户指出错误后
- **user-positive-feedback**：收到明确正向反馈后
- **system-improvement**：完成系统性改进后

---

# 三维成长指数（v3.11.1-Lite）

| 指数 | 含义 | 核心驱动事件 |
|---|---|---|
| **IQ** 智识指数 | 解决新问题的能力 | error-fix、learning-achievement、capability-reuse |
| **EQ** 执行指数 | 与用户协作的质量 | user-positive-feedback（+）、user-correction（-） |
| **FQ** 频率指数 | 稳定执行的密度 | task-done（受日限和递减约束） |

---

# 能力状态机
observed → declared → standard_verified → strong_verified

- `standard_verified`：至少 1 次成功复用
- `strong_verified`：总复用 ≥ 3，near ≥ 2，far ≥ 1（跨场景迁移验证）
- 只有 `strong_verified` 能力可通过 `export_capabilities.py` 导出

---

# Cron 执行顺序（每日）


00:05  audit_events.py      — 诊断扫描
00:15  daily_digest.py      — 更新上下文注入源
00:20  evolve.py            — 计分、状态更新
09:00  weekly_reflection.py — 周一执行：周报 + 训练计划（仅周一）


---

# 上下文注入白名单

**✅ 允许注入：**
- 当前任务结构化描述
- 相关 capability 最多 3 条
- 相关 antipattern 最多 3 条
- `recent_digest.json` 全量
- 当前目标差距摘要 1 条
- 当月校准概要 1 行

**❌ 禁止注入：**
- 全量 `evolution_chain.jsonl`
- 全量 `growth.md` / `capabilities.md` / `audit.md`
- 近 30 天事件全文
- 全量 `weekly_summary.json` 历史

---

# LLM 调用预算

| 场景 | 频率 | 开关字段 |
|---|---|---|
| 周报润色 | 1 次/周 | `allow_weekly_report_llm_rewrite` |
| 训练建议润色 | 1 次/周 | `allow_training_plan_llm_rewrite` |
| 高价值错误认知提炼 | 0–3 次/周 | `allow_error_fix_llm_extraction` |
| 其他 | 0 | 不允许 |

推荐预算：每周 2–5 次。可在 `memory/profile.json` 中调整。

---

# 保护文件（升级不覆盖）

IDENTITY.md
memory/capabilities.json
memory/antipatterns.json
memory/intelligence_index.json
memory/evolution_chain.jsonl
memory/audit_queue.jsonl
memory/profile.json
memory/goals.json

---

# 核心设计原则

1. **diagnostic 永不直接改分** — 诊断只记录，由人工 adopt 后创建派生事件才可改分
2. **evidence_level 缺省 self** — `logical` 只能由系统推断，不允许手动填写
3. **正向增长受边际递减约束** — 分数越高，同等事件的增益越小
4. **负向扣分不打折** — user-correction / task-rework 不乘阻力系数
5. **strong_verified 需跨场景迁移** — near ≥ 2 且 far ≥ 1
6. **模型参与面极小** — 每周最多 2–5 次模型调用，其余全部规则化
7. **capability-decay-penalty 只由 weekly 触发** — 防止每日重复累计扣分
8. **JSON 是主源，Markdown 是导出物** — 脚本只读写 JSON，Markdown 只用于展示

---

# 参考文档（按需 read，不要提前读）

规则：只有在任务执行中**明确需要某类命令或参数**时才 read，不要在对话开始时预读。

| 触发条件 | 文件路径 |
|---|---|
| 录入事件（create_event.py 参数不确定） | `docs/create_event_cheatsheet.md` |
| 处理审计建议（resolve_audit.py） | `docs/audit_commands.md` |
| 查计分规则 / 证据等级 / 字段枚举 | `docs/scoring_rules.md` |
| 查 memory/ 文件用途和说明 | `docs/file_index.md` |
| 运行系统脚本 / 健康检查 / 导出能力 | `docs/ops_commands.md` |
