# OpenClaw 记忆进化系统

## 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.5 | 2026-03-17 | 统一日志路径为 `.sys/logs/events.jsonl`，删除自动路径探测逻辑 |
| v3.4 | 2026-03-15 | 增加过滤已promoted错误功能 |
| v3.3 | 2026-03-15 | PUA第4轮修复：字段名 tag/tags 统一，new-capability 映射修复 |
| v3.2 | 2026-03-15 | PUA第3轮修复：非标准类型事件修复 |
| v3.1 | 2026-03-15 | PUA第2轮修复：Tags覆盖率问题修复 |

---

## 文件结构

```
.openclaw/workspace/
├── .sys/
│   ├── logs/
│   │   └── events.jsonl          # 事件日志主文件（唯一路径）
│   ├── sessions/                 # 会话摘要
│   ├── baseline/                 # 快照
│   ├── todo/
│   └── compact/
├── memory/
│   ├── recent.md                 # 进化摘要（evolve.py 输出）
│   ├── errors.md                 # 错误日志（人工维护）
│   └── archive/                  # 归档
└── scripts/
    ├── evolve.py                 # 核心进化脚本 v3.5
    ├── create_event.py           # 标准化事件创建工具
    ├── fix_recent_events_tags.py # Tags修复工具
    └── fix_nonstandard_types.py  # 类型标准化修复工具
```

---

## 日志路径说明（v3.5 重要变更）

**统一使用 `.sys/logs/events.jsonl`，所有脚本路径已对齐。**

- `.openclaw/logs/events.jsonl` 是 OpenClaw Gateway 自身使用的路径，与我们的脚本完全隔离，避免 tag 污染和并发冲突。
- v3.4 及以前版本存在自动路径探测逻辑（`_detect_runtime_dir`），行为依赖安装环境，已在 v3.5 中删除。
- `.sys/logs/events.jsonl` 由 `setup.sh` 初始化，全新安装即可使用。

---

## 脚本说明

### evolve.py
核心进化脚本，读取近7天事件，提炼写入 `recent.md` 和 `errors.md`。

```bash
# 执行进化
python3 evolve.py

# 搜索记忆
python3 evolve.py search <keyword> [top_n]
```

### create_event.py
标准化事件创建工具，确保所有事件格式合规。

```bash
python3 create_event.py --type task-done --content "完成任务描述..."
python3 create_event.py --type learning-achievement --content "详细学习描述..." --tags learning,tool
python3 create_event.py --list-types   # 查看所有标准类型
```

### fix_recent_events_tags.py
修复 Tags 缺失的历史事件（从第24个事件开始）。

```bash
python3 fix_recent_events_tags.py
```

### fix_nonstandard_types.py
将非标准类型事件映射转换为标准类型。

```bash
python3 fix_nonstandard_types.py
```

---

## 标准事件类型

| 类型 | 用途 | 最小内容长度 |
|------|------|-------------|
| `task-done` | 完成任务 | 8词 |
| `error-found` | 发现错误 | 8词 |
| `system-improvement` | 系统改进 | 10词 |
| `learning-achievement` | 学习成就 | 15词 |
| `user-correction` | 用户纠正 | 10词 |
| `automation-deployment` | 自动化部署 | 5词 |
| `error-fix` | 错误修复 | 5词 |
| `system-monitoring` | 系统监控 | 5词 |
| `quality-verification` | 质量验证 | 5词 |
| `new-capability` | 新能力获得 | 5词 |
| `automation-planning` | 自动化规划 | 5词 |
| `memory-compaction` | 内存压缩 | 5词 |
| `pua-inspection` | PUA检查 | 5词 |
| `quality-improvement` | 质量改进 | 5词 |

---

## 注意事项

- 升级前建议先执行一次 `python3 evolve.py`，确保近期事件已提炼到 `recent.md`
- `events.jsonl` 丢失不影响已提炼的 `recent.md` 和 `errors.md`
- `errors.md` 是最重要的文件，包含人工整理的错误处理经验，请定期备份
