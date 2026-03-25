<!-- 本文件：计分规则、证据等级、字段枚举完整参考，在需要理解计分机制时由 AGENTS.md 索引调用 -->

# 计分规则完整参考

## 证据等级系数表

| 等级 | 系数 | 说明 |
|---|---|---|
| `external` | 1.0 | 有外部可验证证据（日志、截图、测试通过等），尽量提供 `--evidence-ref` |
| `logical` | 0.7 | 系统自动推断，**不允许手动填写** |
| `self` | 0.2 | 自我声明，只进 EQ_process，不直接改 IQ/FQ，缺省值 |

---

## 边际递减（阻力系数）

### 计算公式
```
resistance_factor = max(0.1, (100 - current_score) / 50)
```

### 系数表

| 当前分数 | 阻力系数 | 含义 |
|---|---|---|
| 20 | 1.6 | 快速增长期 |
| 50 | 1.0 | 正常增长 |
| 70 | 0.6 | 增长放缓 |
| 85 | 0.3 | 缓慢增长 |
| 90+ | 0.1（下限） | 极难突破 |

---

## 关键约束速查

| 约束 | 内容 |
|---|---|
| **单链增益上限** | 同 task_id 所有事件合计不超过 +0.6 或 -0.6 |
| **派生增益上限** | 派生事件增益 ≤ 主事件绝对值的 50% |
| **同日限制** | 同 task_type 同日最多 2 次常规 task-done 参与 FQ 计分 |
| **负向不打折** | user-correction / task-rework 不乘阻力系数 |
| **decay 周期** | capability-decay-penalty 只由 weekly_reflection.py 触发 |
| **diagnostic 隔离** | diagnostic 事件永不直接写指数分 |

---

## 三维指数说明

### IQ（智识指数）—— 解决新问题的能力

驱动事件：`error-fix` (+) / `learning-achievement` (+) / `capability-reuse far` (+) / `user-correction` (-)

```
ΔIQ = base_score × evidence_coeff × resistance_factor
示例：external error-fix，IQ=50 → 0.3 × 1.0 × 1.0 = +0.3
```

### EQ（执行指数）—— 与用户协作的质量

驱动事件：`user-positive-feedback` 固定 +0.5 / `user-correction` 固定 -0.3

- `self` 证据只进 EQ_process，不直接改 EQ
- `external` 证据权重 100%，`self` 证据权重 20%

### FQ（频率指数）—— 稳定执行的密度

驱动事件：`task-done`

```
ΔFQ = base_score × resistance_factor
（FQ 不乘 evidence_coeff）
```

---

## 计分示例

### 例 1：常规任务，external 证据，FQ=50
```
base = 0.2，evidence = 1.0，resistance = (100-50)/50 = 1.0
ΔFQ = 0.2 × 1.0 = +0.2
```

### 例 2：修复 bug，external 证据，IQ=70
```
base = 0.35，evidence = 1.0，resistance = (100-70)/50 = 0.6
ΔIQ = 0.35 × 0.6 = +0.21
```

### 例 3：用户反馈负向
```
ΔEQ = -0.3（固定扣分，不乘阻力系数）
```

---

## 派生事件计分链

```
error-found（诊断，不改分）
  ↓ 人工 adopt
error-fix（改分）
  ↓
learning-achievement（派生，改分 ≤ error-fix 的 50%）
```

---

## 样本充足度判断

| 指标 | 充足条件 |
|---|---|
| 能力升级为 standard_verified | ≥ 1 次成功复用 |
| 能力升级为 strong_verified | 总复用 ≥ 3，near ≥ 2，far ≥ 1 |
| FQ 指数用于周报 | 近 30 天 task-done ≥ 15 条 |
| EQ 指数用于周报 | 近 30 天 user-feedback ≥ 5 条 |

---

## 不允许的操作

- ❌ 手动填写 `--evidence logical`
- ❌ `learning-achievement` / `capability-reuse` 缺少 `--parent`
- ❌ 批量创建相同内容事件刷分（evolve.py 会检测并折扣）
- ❌ 手动创建 diagnostic 类型事件
