<!-- 本文件：系统操作命令、健康检查、导出脚本参考，在需要运行系统脚本时由 AGENTS.md 索引调用 -->

# 系统操作命令参考

## 日常操作命令

### 手动触发计分引擎
```bash
python3 scripts/evolve.py
```
**何时用**：新增事件后想立即看到分数变化；cron 时间外手动执行。
**输出**：更新 `memory/intelligence_index.json`

### 手动触发审计扫描
```bash
python3 scripts/audit_events.py
```
**何时用**：cron 时间外立即检查是否有新诊断建议。
**输出**：新增条目写入 `memory/audit_queue.jsonl`

### 手动更新每日摘要
```bash
python3 scripts/daily_digest.py
```
**何时用**：手动刷新 recent_digest.json 用于上下文注入。
**输出**：更新 `memory/recent_digest.json`（近 7 天精简数据）

---

## 周报和训练计划

### 预览周报（不写入）
```bash
python3 scripts/weekly_reflection.py --dry-run
```

### 执行周报（写入文件）
```bash
python3 scripts/weekly_reflection.py
```
**注意**：建议只由每周一 09:00 cron 自动触发，不要频繁手动执行。
**输出**：`weekly_summary.json` + `training_plan.json` + capability decay 惩罚

---

## 数据导出

### 导出 strong_verified 能力
```bash
python3 scripts/export_capabilities.py
```
**输出**：`memory/exported_capabilities.md`

---

## 日志查看

```bash
# 审计扫描日志
tail -20 .sys/logs/cron-audit.log

# 摘要生成日志
tail -20 .sys/logs/cron-digest.log

# 计分引擎日志
tail -20 .sys/logs/cron-memory-evolution.log

# 周报执行日志
tail -20 .sys/logs/weekly-reflection.log
```

---

## 健康检查

### 快速验证核心脚本
```bash
python3 scripts/create_event.py --list-types
python3 scripts/evolve.py
python3 scripts/weekly_reflection.py --dry-run
python3 scripts/audit_events.py
python3 scripts/daily_digest.py
```

### 验证依赖
```bash
python3 -c "from filelock import FileLock; print('✅ filelock OK')"
```

### 验证核心配置
```bash
python3 -c "
import json
p = json.load(open('memory/profile.json'))
assert p.get('evidence_default') == 'self', '❌ evidence_default 不是 self'
assert 'sample_sufficient_min_task_done' in p, '❌ 缺少 sample_sufficient_min_task_done'
print('✅ profile.json 字段正确')
"
```

### 验证目录结构
```bash
test -d memory && test -d scripts && test -d .sys/logs \
  && echo "✅ 目录结构正确" || echo "❌ 缺少必要目录"
```

---

## Cron 配置

```bash
# 编辑 crontab
crontab -e

# 添加以下 4 行（替换 /path/to/openclaw 为实际路径）
5  0 * * *   cd /path/to/openclaw && python3 scripts/audit_events.py >> .sys/logs/cron-audit.log 2>&1
15 0 * * *   cd /path/to/openclaw && python3 scripts/daily_digest.py >> .sys/logs/cron-digest.log 2>&1
20 0 * * *   cd /path/to/openclaw && python3 scripts/evolve.py >> .sys/logs/cron-memory-evolution.log 2>&1
0  9 * * 1   cd /path/to/openclaw && python3 scripts/weekly_reflection.py >> .sys/logs/weekly-reflection.log 2>&1
```

---

## 故障排查

### 脚本报错
```bash
# 查看详细错误
python3 scripts/xxxxx.py

# 检查依赖
python3 -m pip list | grep filelock

# 检查权限
ls -la memory/ .sys/logs/
```

### 分数异常
```bash
# 查看最近 10 条事件
tail -10 memory/evolution_chain.jsonl

# 重新计分并查看日志
python3 scripts/evolve.py
cat .sys/logs/cron-memory-evolution.log
```

### 审计建议堆积
```bash
# 查看 pending 数量
grep '"status":"pending"' memory/audit_queue.jsonl | wc -l

# 清理超期
python3 scripts/resolve_audit.py --expire-old
```
