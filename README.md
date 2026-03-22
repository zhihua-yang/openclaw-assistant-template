# OpenClaw v3.11.1-Lite

> 低 token 成本、长期可持续的 AI 自主成长进化系统
> 适用于全新实例和从 v3.7 升级的实例，setup.sh 自动兼容两种场景

---

## 快速开始

### 全新实例

```bash
git clone https://github.com/zhihua-yang/openclaw-assistant-template.git
cd openclaw-assistant-template
bash setup.sh
```

> ℹ️ 全新实例不需要指定目标路径，`workspace/` 即为工作目录，setup.sh 原地初始化。

### 升级已有 OpenClaw 实例（v3.7 → v3.11.1-Lite）

```bash
# 在任意临时目录 clone（不要 clone 到旧工作区内部）
git clone https://github.com/zhihua-yang/openclaw-assistant-template.git /tmp/openclaw-upgrade
cd /tmp/openclaw-upgrade

# 指定旧工作区路径，脚本直接升级到位
bash setup.sh --target /root/.openclaw/workspace

# 升级完成后可删除临时目录
rm -rf /tmp/openclaw-upgrade
```

> ℹ️ `--target` 模式下，setup.sh 将新脚本**直接复制到旧工作区**，
> 所有 memory/ 数据文件保留不动，IDENTITY.md 保护不覆盖。

setup.sh 自动完成：

- 检查并安装依赖（filelock、scikit-learn）
- 同步所有脚本文件到目标工作区（升级模式）/ 验证文件完整性（全新模式）
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
├── README.md
├── setup.sh                              # 一键安装（支持 --target 升级已有工作区）
└── workspace/                            # 全新实例的工作目录
    ├── AGENTS.md                         # AI Agent 行为规范
    ├── IDENTITY.md                       # 身份锚点（保护文件）
    ├── install-cron.sh                   # 由 setup.sh 自动生成
    ├── memory/
    │   ├── archive/                      # 归档目录
    │   ├── evolution_chain.jsonl         # 进化链主数据（保护，append-only）
    │   ├── capabilities.json             # 能力库（保护）
    │   ├── antipatterns.json             # 避坑库（保护）
    │   ├── intelligence_index.json       # 三维指数快照（保护）
    │   ├── audit_queue.jsonl             # 审计队列状态机（保护）
    │   ├── profile.json                  # 配置参数（保护）
    │   ├── goals.json                    # 三层目标（保护）
    │   ├── recent_digest.json            # 近7天摘要（每日更新）
    │   ├── weekly_summary.json           # 周统计快照（每周更新）
    │   ├── training_plan.json            # 训练建议（每周更新）
    │   ├── calibration.json              # 元认知校准（每月滚动）
    │   ├── core.md                       # v3.7 保留
    │   ├── recent.md                     # v3.7 保留
    │   ├── errors.md                     # v3.7 保留
    │   ├── growth.md                     # v3.7 保留（降为展示层）
    │   └── project.md                    # v3.7 保留
    ├── scripts/
    │   ├── baseline.sh                   # v3.7 保留
    │   ├── health-check.sh               # v3.7 保留
    │   ├── farewell_detector.py          # v3.7 保留
    │   ├── fix_nonstandard_types.py      # v3.7 保留
    │   ├── fix_recent_events_tags.py     # v3.7 保留
    │   ├── session_note_writer.py        # v3.7 保留
    │   ├── create_event.py               # v3.11.1 重写
    │   ├── evolve.py                     # v3.11.1 重写
    │   ├── audit_events.py               # v3.11.1 新增
    │   ├── resolve_audit.py              # v3.11.1 新增
    │   ├── weekly_reflection.py          # v3.11.1 重写
    │   ├── daily_digest.py               # v3.11.1 新增
    │   ├── export_capabilities.py        # v3.11.1 新增
    │   └── utils/
    │       ├── __init__.py
    │       ├── file_lock.py              # 文件锁（并发安全写入）
    │       ├── paths.py                  # 路径常量
    │       ├── sample_check.py           # 样本充足度判断
    │       └── capability_search.py      # 三级降级检索（不调用外部 API）
    └── skills/                           # v3.7 保留
        ├── compact.md
        ├── health-check.md
        ├── memory-evolution.md
        ├── remember.md
        ├── rollback.md
        ├── session-notes.md
        ├── todo.md
        └── weekly-self-reflection.md
```


---

## 常用命令

> 所有脚本命令均在工作区根目录下执行：
> - 全新实例：`cd openclaw-assistant-template/workspace`
> - 升级实例：`cd /root/.openclaw/workspace`（即原有工作区）

### 事件录入

```bash
# 任务完成（最小模式，evidence 缺省 self）
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


### 事件字段参考

| 字段 | 可选值 | 缺省值 |
| :-- | :-- | :-- |
| `--difficulty` | `routine` / `stretch` / `novel` | `routine` |
| `--confidence` | `high` / `medium` / `low` | 可不填 |
| `--evidence` | `external` / `self` | `self` |
| `--transfer` | `near` / `far` | `near` |
| `--trigger` | `normal` / `error-driven` / `challenge-driven` | `normal` |
| `--challenge-type` | `consolidate` / `stretch` / `transfer` | 可不填 |
| `--outcome` | `success` / `partial` / `fail` | 可不填 |

> ⚠️ `--evidence logical` 只能由系统自动推断，**不允许手动填写**。

### 审计处理

```bash
# 查看所有 pending 建议
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
cat .sys/logs/cron-audit.log
cat .sys/logs/cron-digest.log
cat .sys/logs/cron-memory-evolution.log
cat .sys/logs/weekly-reflection.log
```


---

## 计分规则

### 证据等级系数

| 等级 | 系数 | 说明 |
| :-- | :-- | :-- |
| `external` | 1.0 | 有外部可验证证据（日志、截图、测试结果等） |
| `logical` | 0.7 | 系统基于事实链自动推断，**不允许手动填写** |
| `self` | 0.2 | 自我声明，只进 EQ_process，不直接改 IQ/FQ |

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

每日 00:05 自动扫描，输出到 `memory/audit_queue.jsonl`，**不直接改分**：


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
bash install-cron.sh
```

```
# 每日审计 00:05
5 0 * * * cd /path/to/workspace && python3 scripts/audit_events.py >> .sys/logs/cron-audit.log 2>&1

# 每日摘要 00:15
15 0 * * * cd /path/to/workspace && python3 scripts/daily_digest.py >> .sys/logs/cron-digest.log 2>&1

# 记忆进化 00:20
20 0 * * * cd /path/to/workspace && python3 scripts/evolve.py >> .sys/logs/cron-memory-evolution.log 2>&1

# 周反思 周一 09:00
0 9 * * 1 cd /path/to/workspace && python3 scripts/weekly_reflection.py >> .sys/logs/weekly-reflection.log 2>&1
```


---

## LLM 调用预算

| 模式 | 每周调用次数 | 适合场景 |
| :-- | :-- | :-- |
| Level 0 极省 | 0 | 冷启动 / 成本最敏感 |
| **Level 1 常规（推荐）** | **2** | **周报 + 训练建议各 1 次润色** |
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
# 在临时目录 clone（勿 clone 到旧工作区内）
git clone https://github.com/zhihua-yang/openclaw-assistant-template.git /tmp/openclaw-upgrade
cd /tmp/openclaw-upgrade

# 直接升级到旧工作区
bash setup.sh --target /root/.openclaw/workspace

# 完成后删除临时目录
rm -rf /tmp/openclaw-upgrade
```

**自动处理：**

- ✅ 新脚本直接复制到旧工作区 scripts/（不再产生子目录）
- ✅ utils/ 工具库完整同步
- ✅ AGENTS.md 更新为完整版
- ✅ IDENTITY.md 保护不覆盖
- ✅ 所有 memory/ 数据文件保留不动，只补充缺失的 JSON
- ✅ v3.7 原有脚本（baseline.sh / health-check.sh / farewell_detector.py 等）保留
- ✅ skills/ 目录全部内容保留
- ✅ 清理旧版 crontab，配置 4 条新任务
- ✅ 30 项健康检查验证

**历史数据：**

- `.sys/logs/events.jsonl` 保留不动，可继续查阅
- `memory/evolution_chain.jsonl` 全新起点，不自动迁移旧数据

---

## 依赖

```bash
pip3 install filelock scikit-learn
```

| 依赖 | 是否必须 | 用途 |
| :-- | :-- | :-- |
| `python3 >= 3.8` | ✅ 必须 | 运行所有脚本 |
| `filelock` | ✅ 必须 | JSON 并发写入安全 |
| `scikit-learn` | ⚡ 推荐 | capability TF-IDF 检索（无则降级为精确匹配） |


---

## 保护文件（任何升级不覆盖）

```
workspace/IDENTITY.md
workspace/memory/capabilities.json
workspace/memory/antipatterns.json
workspace/memory/intelligence_index.json
workspace/memory/evolution_chain.jsonl
workspace/memory/audit_queue.jsonl
workspace/memory/profile.json
workspace/memory/goals.json
```


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
9. **升级不产生子目录** — `--target` 模式直接覆盖到旧工作区，保持目录结构干净

---

## FAQ

**Q：升级时 clone 目录放哪里？**
A：放任意临时目录，推荐 `/tmp/openclaw-upgrade`。**不要** clone 到旧工作区内部，否则会产生嵌套子目录。

**Q：--target 参数指向哪里？**
A：指向 OpenClaw 的实际工作区根目录，通常是 `/root/.openclaw/workspace`。可通过 `pwd` 在 OpenClaw 内确认。

**Q：全新实例和升级实例用法有区别吗？**
A：有。全新实例直接 `bash setup.sh`，原地初始化；升级实例用 `bash setup.sh --target <旧工作区路径>`，脚本复制过去。

**Q：capability 检索会调用外部 API 吗？**
A：不会。三级降级：精确匹配 → 本地 TF-IDF（scikit-learn）→ 空列表，全程离线。

**Q：v3.7 的 skills/ 目录和原有脚本还能用吗？**
A：可以。setup.sh 只覆盖 v3.11.1 重写的 7 个脚本和新增的 utils/，其余文件一律保留。

**Q：capability-decay-penalty 什么时候触发？**
A：仅由 `weekly_reflection.py` 在每周一触发。触发条件：能力 ≥ 60 天未复用，或停滞/遗忘诊断超 7 天未打破。

**Q：sample_sufficient 是按天数还是数量判断？**
A：按 task-done 事件数量，默认阈值 15 条，可在 `profile.json` 的 `sample_sufficient_min_task_done` 修改。

**Q：weekly_reflection.py 一定会调用模型吗？**
A：由 `profile.json` 控制。默认开启周报润色（1次）+ 训练建议润色（1次）= 每周 2 次。设置 `allow_weekly_report_llm_rewrite: false` 可降至零模型。

**Q：v3.7 的历史事件还在吗？**
A：在。`.sys/logs/events.jsonl` 保留不动。新系统从 `memory/evolution_chain.jsonl` 全新起点开始，两者互不影响。

---
