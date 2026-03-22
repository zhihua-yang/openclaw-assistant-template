## 快速开始

```bash
git clone https://github.com/zhihua-yang/openclaw-assistant-template.git
cd openclaw-assistant-template
bash setup.sh
```

setup.sh 自动完成：

- 检查并安装依赖（filelock、scikit-learn）
- 同步所有脚本文件到 workspace/scripts/
- 初始化 memory/ 数据文件（已有数据不覆盖）
- 运行 30 项健康检查
- 配置 4 条 Cron 定时任务

---

## 版本定位

| 版本 | 核心能力 |
| :-- | :-- |
| v3.6 | 基础事件记录、evolve.py、cron |
| v3.7 | 修复路径 bug、weekly_reflection.py、growth.md、中文支持 |
| **v3.11.1-Lite** | 三维指数、能力状态机、审计系统、元认知校准、文件锁安全、边际递减 |

### 核心设计理念

> **能规则化就不调用模型，能增量更新就不读全量，能摘要就不回放全文。**

每周模型调用预算：**2–5 次**（周报润色 + 训练建议润色 + 高价值错误提炼）。
其余所有计分、诊断、状态迁移全部由 Python 脚本规则化完成，零 API 调用。

---

## 系统架构

```
任务发生
  ↓
create_event.py（结构化录入，无模型调用）
  ↓
00:05  audit_events.py    — 诊断扫描，输出 audit_queue.jsonl（不改分）
00:15  daily_digest.py    — 更新 recent_digest.json（上下文注入源）
00:20  evolve.py          — 计分引擎，状态更新，evolution_chain 追加
  ↓
每周一 09:00  weekly_reflection.py
  — 周报 + decay penalty + 训练计划 + 可选模型润色
  ↓
resolve_audit.py（人工处理审计建议，按需触发）
```


---

## 三维成长指数

| 指数 | 含义 | 核心驱动事件 |
| :-- | :-- | :-- |
| **IQ** 智识指数 | 解决新问题的能力 | error-fix、learning-achievement、capability-reuse |
| **EQ** 执行指数 | 与用户协作的质量 | user-positive-feedback（+）、user-correction（-） |
| **FQ** 频率指数 | 稳定执行的密度 | task-done（受日限和递减约束） |

所有指数从 **50.0** 起步，增长受边际递减约束（分数越高，同等事件的增益越小）。

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


---

## 能力状态机

```
observed → declared → standard_verified → strong_verified
```

| 状态 | 升级条件 |
| :-- | :-- |
| `observed` | 初始状态 |
| `declared` | 有 learning-achievement 记录 |
| `standard_verified` | 至少 1 次成功 capability-reuse |
| `strong_verified` | 总复用 ≥ 3，near ≥ 2，**far ≥ 1**（跨场景迁移验证） |

只有 `strong_verified` 能力可通过 `export_capabilities.py` 导出。

---

## 文件结构

```
openclaw-assistant-template/
├── README.md                         # 本文件
├── setup.sh                          # 一键安装脚本（全新/升级通用）
├── AGENTS.md                         # AI Agent 行为规范（完整独立版）
├── IDENTITY.md                       # 身份锚点（保护文件，升级不覆盖）
└── workspace/
    ├── install-cron.sh               # 由 setup.sh 自动生成
    ├── scripts/
    │   ├── create_event.py           # 事件录入
    │   ├── evolve.py                 # 计分引擎
    │   ├── audit_events.py           # 每日审计扫描
    │   ├── resolve_audit.py          # 人工审计处理
    │   ├── weekly_reflection.py      # 周报 + 训练计划 + decay penalty
    │   ├── daily_digest.py           # 每日摘要更新
    │   ├── export_capabilities.py    # strong_verified 能力导出
    │   └── utils/
    │       ├── __init__.py
    │       ├── file_lock.py          # 文件锁（并发安全写入）
    │       ├── paths.py              # 路径常量
    │       ├── sample_check.py       # 样本充足度判断
    │       └── capability_search.py  # 三级降级检索（不调用外部 API）
    └── memory/
        ├── evolution_chain.jsonl     # 进化链主数据（保护，append-only）
        ├── capabilities.json         # 能力库（保护）
        ├── antipatterns.json         # 避坑库（保护）
        ├── intelligence_index.json   # 三维指数快照（保护）
        ├── audit_queue.jsonl         # 审计队列状态机（保护）
        ├── profile.json              # 配置参数（保护）
        ├── goals.json                # 三层目标（保护）
        ├── recent_digest.json        # 近7天摘要（每日更新）
        ├── weekly_summary.json       # 周统计快照（每周更新）
        ├── training_plan.json        # 训练建议（每周更新）
        ├── calibration.json          # 元认知校准（每月滚动）
        ├── recent.md                 # v3.7 保留，仍可查阅
        ├── errors.md                 # v3.7 保留，仍可查阅
        └── growth.md                 # v3.7 保留，降为只读展示层
```


---

## 常用命令

### 事件录入

```bash
# 任务完成（最小模式）
python3 scripts/create_event.py \
  --type task-done \
  --content "完成 Panama 邮件修复，定位 SMTP 配置错误" \
  --task-type email-debug

# 任务完成（完整模式）
python3 scripts/create_event.py \
  --type task-done \
  --content "完成 Panama 邮件修复，定位 SMTP 配置错误" \
  --task-type email-debug \
  --difficulty stretch \
  --confidence medium \
  --evidence external \
  --evidence-ref "log:cron-memory-evolution-20260322" \
  --cap cap_email_smtp_debug

# 错误修复
python3 scripts/create_event.py \
  --type error-fix \
  --content "修复 cron 时区错误，根因是容器默认 UTC" \
  --task-type cron-maintenance \
  --evidence external \
  --cap cap_cron_timezone

# 刻意练习
python3 scripts/create_event.py \
  --type intentional-challenge \
  --content "在新项目中独立完成日志分析，无参考资料" \
  --difficulty novel \
  --challenge-type transfer \
  --outcome success \
  --cap cap_log_analysis

# 错误驱动学习（必须有 --cognitive-update 和 --parent）
python3 scripts/create_event.py \
  --type learning-achievement \
  --content "理解了 SMTP 认证失败的根因" \
  --trigger error-driven \
  --cognitive-update "Gmail SMTP 需要 App Password，不是账号密码，之前一直误解" \
  --parent evt-20260322-abc123

# 能力复用（far transfer）
python3 scripts/create_event.py \
  --type capability-reuse \
  --content "将日志分析能力迁移到新的监控系统排查" \
  --cap cap_log_analysis \
  --transfer far \
  --parent evt-20260322-def456

# 查看所有事件类型
python3 scripts/create_event.py --list-types

# 预览事件（不写入）
python3 scripts/create_event.py --type task-done --content "xxx" --dry-run
```


### 审计处理

```bash
# 查看所有待处理建议
python3 scripts/resolve_audit.py --list

# 采纳建议（采纳后用 create_event.py 录入对应派生事件）
python3 scripts/resolve_audit.py --adopt diag-20260322-abc123

# 忽略建议
python3 scripts/resolve_audit.py --dismiss diag-20260322-abc123

# 批量过期超 7 天未处理的建议
python3 scripts/resolve_audit.py --expire-old
```


### 系统操作

```bash
# 手动触发计分引擎
python3 scripts/evolve.py

# 手动触发审计扫描
python3 scripts/audit_events.py

# 更新每日摘要
python3 scripts/daily_digest.py

# 预览周报（不写入文件）
python3 scripts/weekly_reflection.py --dry-run

# 执行周报（写入文件）
python3 scripts/weekly_reflection.py

# 导出 strong_verified 能力
python3 scripts/export_capabilities.py
```


### 日志查看

```bash
cat workspace/.sys/logs/cron-audit.log
cat workspace/.sys/logs/cron-digest.log
cat workspace/.sys/logs/cron-memory-evolution.log
cat workspace/.sys/logs/weekly-reflection.log
```


---

## 计分规则

### 证据等级系数

| 等级 | 系数 | 说明 |
| :-- | :-- | :-- |
| `external` | 1.0 | 有外部可验证证据（日志、截图、测试结果等） |
| `logical` | 0.7 | 系统基于事实链自动推断，**不允许手动填写** |
| `self` | 0.2 | 自我声明，只进 EQ_process，不直接改 IQ/FQ |

> ⚠️ `evidence_level` 录入时缺省为 `self`，`logical` 只能由系统产生。

### 主要事件基础 delta

| 事件类型 | IQ | EQ | FQ |
| :-- | --: | --: | --: |
| `task-done` 首次新类型 | +0.2 | 0 | +0.2 |
| `task-done` 常规 | 0 | 0 | +0.1 |
| `error-fix` | +0.3 | 0 | 0 |
| `user-positive-feedback` | 0 | +0.2 | +0.1 |
| `user-correction` | -0.1 | -0.3 | -0.1 |
| `task-rework` | 0 | -0.1 | -0.3 |
| `intentional-challenge` 成功 | +0.2 | 0 | 0 |
| `learning-achievement` error-driven | +0.15 | 0 | 0 |
| `learning-achievement` normal | +0.1 | 0 | 0 |
| `capability-reuse` far | +0.12 | 0 | +0.05 |
| `capability-reuse` near | +0.1 | 0 | +0.1 |
| `capability-decay-penalty` | -0.1 | 0 | -0.1 |

### 关键约束

- 单链增益上限：`+0.6`（同一 task_id 所有事件合计）
- 单链减益上限：`-0.6`
- 派生事件增益 ≤ 主事件绝对值的 50%
- 同 task_type 同日最多 2 次常规 task-done 参与 FQ 计分
- 负向扣分**不乘阻力系数**（不打折）
- `diagnostic` 事件永不直接写指数分
- `capability-decay-penalty` 只由 `weekly_reflection.py` 触发

---

## 诊断系统

每日 00:05 自动扫描，输出诊断建议到 `audit_queue.jsonl`，**不直接改分**：


| 诊断类型 | 触发条件 | 建议操作 |
| :-- | :-- | :-- |
| `stagnation-warning` | 连续 3 天无 learning-achievement | 补录 learning-achievement |
| `suspected-missing-learning` | task-done 含学习关键词但无派生 | 考虑补录 learning-achievement |
| `repeat-error-alert` | 7 天内同类错误重复 ≥ 2 次 | 复盘根因，录入 antipattern |
| `comfort-zone-warning` | routine 占比 > 70%（近30天） | 安排 stretch/novel 任务 |
| `overconfidence-warning` | 高置信失败率 > 15% | 降低预判置信度 |
| `underconfidence-warning` | 低置信成功率 > 25% | 更信任自己的能力 |
| `plateau-detected` | 连续 3 周净增长 < 0.3 | 增加 intentional-challenge |
| `breakthrough-detected` | 单周净增长 > 8周均值 2 倍 | 记录突破原因，强化该路径 |


---

## Cron 配置（4 条任务）

由 `setup.sh` 自动配置，也可手动安装：

```bash
bash workspace/install-cron.sh
```

```
# 每日审计 00:05
5 0 * * * cd /path/workspace && python3 scripts/audit_events.py >> .sys/logs/cron-audit.log 2>&1

# 每日摘要 00:15
15 0 * * * cd /path/workspace && python3 scripts/daily_digest.py >> .sys/logs/cron-digest.log 2>&1

# 记忆进化 00:20
20 0 * * * cd /path/workspace && python3 scripts/evolve.py >> .sys/logs/cron-memory-evolution.log 2>&1

# 周反思 周一 09:00
0 9 * * 1 cd /path/workspace && python3 scripts/weekly_reflection.py >> .sys/logs/weekly-reflection.log 2>&1
```


---

## LLM 调用预算

| 模式 | 每周调用次数 | 适合场景 |
| :-- | :-- | :-- |
| Level 0 极省 | 0 | 冷启动 / 成本最敏感 |
| **Level 1 常规（推荐）** | **2** | **日常运行（周报 + 训练建议各 1 次润色）** |
| Level 2 增强 | 2–5 | 重要阶段（增加错误认知提炼） |

在 `memory/profile.json` 中控制：

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

## 从 v3.7 升级

```bash
# 重新执行 setup.sh 即可，自动兼容升级场景
bash setup.sh
```

setup.sh 在升级时会自动：

- ✅ 新增 `utils/` 工具库（文件锁、检索、样本判断）
- ✅ 替换 `create_event.py` / `evolve.py` / `weekly_reflection.py`（完全重写）
- ✅ 新增 `audit_events.py` / `resolve_audit.py` / `daily_digest.py` / `export_capabilities.py`
- ✅ 初始化新增 JSON 文件（已有数据不覆盖）
- ✅ 清理旧版 crontab，新增 4 条任务
- ✅ 30 项健康检查验证

**历史数据策略：**

- v3.7 的 `.sys/logs/events.jsonl` 保留不动，可继续查阅
- v3.11.1-Lite 从 `memory/evolution_chain.jsonl` 全新起点开始记录
- 不自动迁移历史数据（避免字段缺失导致计分不准）

---

## 依赖

| 依赖 | 是否必须 | 用途 |
| :-- | :-- | :-- |
| `python3 >= 3.8` | ✅ 必须 | 运行所有脚本 |
| `filelock` | ✅ 必须 | JSON 并发写入安全 |
| `scikit-learn` | ⚡ 推荐 | capability TF-IDF 检索（无则降级为精确匹配） |

```bash
pip3 install filelock scikit-learn
```


---

## 健康检查（30 项）

`setup.sh` 执行时自动运行，也可单独查看：

```bash
bash setup.sh 2>&1 | grep -A 60 "Step 7"
```

覆盖范围：

- 脚本文件存在（10 项）
- JSON 数据文件存在（7 项）
- profile.json 字段完整（1 项）
- Python 语法正确（5 项）
- 脚本可运行（5 项）
- filelock 依赖可用（1 项）
- IDENTITY.md 保护文件存在（1 项）

---

## 核心设计原则

1. **diagnostic 永不直接改分** — 诊断只记录，人工 adopt 后创建派生事件才可改分
2. **evidence_level 缺省 self** — `logical` 只能由系统推断，不允许手动填写
3. **正向增长受边际递减约束** — 分数越高，同等事件增益越小
4. **负向扣分不打折** — user-correction / task-rework 不乘阻力系数
5. **strong_verified 需跨场景迁移** — near ≥ 2 且 far ≥ 1，不能只靠相似场景重复
6. **capability 检索不调用外部 API** — 精确匹配 → 本地 TF-IDF → 空列表，三级降级
7. **JSON 是主源，Markdown 是导出物** — 脚本只读写 JSON，Markdown 只用于展示
8. **样本充足度按数量判断** — task-done ≥ 15 条触发完整周报，不按天数

---

## 保护文件（任何升级不覆盖）

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

## FAQ

**Q：全新实例和从 v3.7 升级，setup.sh 有区别吗？**
A：没有区别，同一个 setup.sh。全新实例所有文件都不存在，全部新建；升级实例已有文件跳过，只补缺失文件。

**Q：capability 检索会调用 OpenAI API 吗？**
A：绝对不会。三级降级链：精确匹配 capability_ids → 本地 TF-IDF（scikit-learn）→ 空列表。

**Q：evidence_level 手动填 logical 有什么风险？**
A：`logical` 证据系数为 0.7，`self` 为 0.2。手动填写会造成自我声明被当作系统推断处理，证据等级虚高，破坏计分可信度。

**Q：capability-decay-penalty 什么时候触发？**
A：仅由 `weekly_reflection.py` 在每周一触发，不由 `evolve.py` 每日生成。触发条件：能力 ≥ 60 天未复用，或停滞/遗忘诊断超 7 天未打破。

**Q：sample_sufficient 是按天数还是数量判断？**
A：按 task-done 事件数量，默认阈值 15 条，可在 `profile.json` 的 `sample_sufficient_min_task_done` 修改。

**Q：weekly_reflection.py 一定会调用模型吗？**
A：由 `profile.json` 控制。默认开启周报润色（1次）+ 训练建议润色（1次）= 每周 2 次。设置 `allow_weekly_report_llm_rewrite: false` 可降至零模型。

**Q：v3.7 的历史事件还在吗？**
A：在。`.sys/logs/events.jsonl` 保留不动。新系统从 `memory/evolution_chain.jsonl` 全新起点开始，两者互不影响。

---
