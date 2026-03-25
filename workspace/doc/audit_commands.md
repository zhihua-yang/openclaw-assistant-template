<!-- 本文件：resolve_audit.py 和审计处理流程，在处理诊断建议时由 AGENTS.md 索引调用 -->

# 审计处理命令参考

## 基本命令

### 查看所有 pending 审计建议
```bash
python3 scripts/resolve_audit.py --list
```

### 采纳建议
```bash
python3 scripts/resolve_audit.py --adopt diag-20260325-00001
```
⚠️ 采纳后还需手动调用 `create_event.py` 录入对应派生事件，才会影响分数。

### 忽略建议
```bash
python3 scripts/resolve_audit.py --dismiss diag-20260325-00002
```

### 批量清理超 7 天未处理的建议
```bash
python3 scripts/resolve_audit.py --expire-old
```

---

## 审计建议类型速查

| 诊断类型 | 触发条件 | 建议操作 | 对应修复命令 |
|---|---|---|---|
| `stagnation-warning` | 连续 3 天无 learning-achievement | 补录 learning-achievement | `create_event.py --type learning-achievement` |
| `suspected-missing-learning` | task-done 含学习关键词但无派生 | 考虑补录 learning-achievement | 同上 |
| `repeat-error-alert` | 7 天内同类错误重复 ≥ 2 次 | 复盘根因，录入 antipattern | `create_event.py --type antipattern-extracted` |
| `comfort-zone-warning` | 近 30 天 routine 任务 > 70% | 安排 stretch 任务 | 下次任务加 `--difficulty stretch` |
| `overconfidence-warning` | 高置信失败率 > 15% | 注意校准，降低预判置信度 | 调整 profile.json |
| `underconfidence-warning` | 低置信成功率 > 25% | 更信任自己的能力 | 调整 profile.json |
| `plateau-detected` | 连续 3 周净增长 < 0.3 | 增加 intentional-challenge | `create_event.py --type intentional-challenge` |
| `breakthrough-detected` | 单周净增长 > 8 周均值 2 倍 | 记录突破原因，强化该路径 | 手动记录在 memory/notes.md |

---

## 审计处理工作流

```
1. python3 scripts/resolve_audit.py --list
   ↓
2. 逐条审视，按需采纳（--adopt）或忽略（--dismiss）
   ↓
3. 若采纳，按建议创建对应派生事件（create_event.py）
   ↓
4. python3 scripts/resolve_audit.py --expire-old
   （周一或月初执行，清理超期建议）
```

### 采纳 → 派生事件对应关系

| 建议类型 | 采纳后需执行 |
|---|---|
| stagnation-warning | `create_event.py --type learning-achievement --trigger error-driven` |
| repeat-error-alert | `create_event.py --type antipattern-extracted` |
| comfort-zone-warning | 下次任务加 `--difficulty stretch`，完成后录 task-done |
| plateau-detected | `create_event.py --type intentional-challenge` |

---

## 关键提示

- **采纳 ≠ 完成**：采纳只是标记"同意诊断"，还需创建相应 create_event.py 才能改分
- **不是所有建议都要采纳**：不适用的直接 `--dismiss`
- **7 天过期规则**：超过 7 天未处理自动过期，可用 `--expire-old` 清理
- **不允许手动创建 diagnostic 事件**：diagnostic 类型仅由 audit_events.py 系统生成
