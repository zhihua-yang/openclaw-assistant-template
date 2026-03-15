# 内网数字助手 (OpenClaw Workspace)

> 一套运行在本地 / 内网 OpenClaw 环境中的个人 AI 助手配置方案。  
> 无需联网，数据完全本地存储，支持长期记忆、自动进化和定时自省。

---

## 快速开始

```bash
git clone <your-repo-url>
cd <repo>
bash setup.sh
```

然后在 OpenClaw → Settings → Workspace 中将路径设为 `~/.openclaw/workspace`，  
新建对话并粘贴 `setup.sh` 运行结束后打印的「激活提示词」即可完成初始化。

---

## 目录结构

```
workspace/
├── IDENTITY.md               # 助手人格设定
├── AGENTS.md                 # 核心行为规则 & 事件写入规范
├── memory/
│   ├── core.md               # 用户基本信息
│   ├── project.md            # 当前项目上下文
│   ├── recent.md             # 近期活动摘要（evolve.py 自动维护）
│   ├── errors.md             # 错误记录（状态：monitoring / pending / promoted）
│   └── archive/              # 历史压缩归档
├── skills/
│   ├── session-notes.md      # /session-notes 技能
│   ├── remember.md           # /remember 技能
│   ├── weekly-self-reflection.md
│   ├── compact.md
│   ├── todo.md
│   └── health-check.md
├── scripts/
│   ├── evolve.py             # 记忆进化主程序（cron 每天 00:00）
│   ├── create_event.py       # 标准化事件写入工具
│   ├── health-check.sh       # 健康检查
│   ├── baseline.sh           # 基线快照 & Diff 对比
│   └── fix_nonstandard_types.py   # 历史数据修复：type 标准化
│   └── fix_recent_events_tags.py  # 历史数据修复：tag -> tags 字段名
└── .sys/                     # 运行时目录（gitignore）
    ├── logs/events.jsonl     # 结构化事件日志
    ├── sessions/             # 每日会话摘要
    ├── baseline/             # 基线快照
    ├── todo/
    └── compact/
```

---

## 核心脚本说明

### `scripts/evolve.py`
每天 00:00 由 cron 自动运行，读取近 7 天 `events.jsonl`，提取洞察并更新 `memory/recent.md` 和 `memory/errors.md`。

```bash
# 手动运行
python3 workspace/scripts/evolve.py

# 搜索历史事件
python3 workspace/scripts/evolve.py search "关键词"
```

### `scripts/create_event.py`
标准化事件写入工具，自动验证 type 合法性、content 字数、tags 非空，强制 UTC 时区。  
在 `session-notes` 中推荐优先使用此工具写入事件。

```bash
# 写入一条事件
python3 workspace/scripts/create_event.py \
  --type learning-achievement \
  --content "今天学习了..."

# 查看所有合法 type
python3 workspace/scripts/create_event.py --list-types

# 验证某个 type 是否合法
python3 workspace/scripts/create_event.py --check-type task-done
```

### `scripts/fix_nonstandard_types.py`
历史数据修复工具，将 `events.jsonl` 中非标准 type 批量替换为最近的标准类型。

### `scripts/fix_recent_events_tags.py`
历史数据修复工具，将旧数据中 `"tag"` 字段名批量重命名为 `"tags"`。

---

## 事件规范（events.jsonl）

每条事件必须符合以下格式，否则 `evolve.py` 和 `health-check.sh` 会报错：

```json
{
  "ts":      "2026-03-15T00:00:00+00:00",
  "type":    "<标准类型>",
  "content": "<详细描述>",
  "tags":    ["tag1", "tag2"],
  "count":   1
}
```

**强制要求：**
- `tags` 字段名（不是 `tag`）
- `ts` 必须带 UTC 时区偏移（`+00:00`）
- `type` 必须从以下 14 个标准类型中选取

**14 个标准 type：**

| type | 说明 | 内容最低字数 |
|---|---|---|
| `task-done` | 完成任务 | 8 单元 |
| `error-found` | 发现错误 | 8 单元 |
| `system-improvement` | 系统改进 | 10 单元 |
| `learning-achievement` | 学习成就 | 15 单元 |
| `user-correction` | 用户纠正 | 10 单元 |
| `automation-deployment` | 自动化部署 | 5 单元 |
| `error-fix` | 错误修复 | 5 单元 |
| `system-monitoring` | 系统监控 | 5 单元 |
| `quality-verification` | 质量验证 | 5 单元 |
| `new-capability` | 新能力（兼容旧数据） | 5 单元 |
| `automation-planning` | 自动化规划 | 5 单元 |
| `memory-compaction` | 内存压缩 | 5 单元 |
| `pua-inspection` | 深度检查 | 5 单元 |
| `quality-improvement` | 质量改进 | 5 单元 |

> 中文内容字数单元：每 15 个字符 ≈ 1 单元；英文按单词数计算。

---

## 定时任务

`setup.sh` 会自动注册以下两条 crontab：

| 任务 | 时间 | 说明 |
|---|---|---|
| `evolve.py` | 每天 00:00 | 记忆进化，更新 recent.md / errors.md |
| weekly trigger | 每周一 09:00 | 写入触发信号，启动时自动执行 /weekly-self-reflection |

手动查看：
```bash
crontab -l | grep -E "memory-evolution|weekly-self-reflection"
```

---

## 健康检查

```bash
bash workspace/scripts/health-check.sh
```

检查项包括：workspace 可写、events.jsonl JSON 合法、磁盘空间、关键文件存在、Python 脚本语法、**近 20 条事件的 tags 覆盖率**。

---

## 历史数据修复

如果你是从旧版本升级，建议先运行修复脚本：

```bash
# 修复 tag -> tags 字段名
python3 workspace/scripts/fix_recent_events_tags.py

# 修复非标准 type
python3 workspace/scripts/fix_nonstandard_types.py
```

---

## 版本历史

| 版本 | 主要改动 |
|---|---|
| v3.1 | 初始完整方案 |
| v3.2 | 修复激活提示词视角问题（关于我/关于你） |
| v3.3 | 修复 evolve.py 时区 bug（naive/aware datetime 混用） |
| v3.4 | 修复 evolve.py 3个字段一致性 bug（tags字段名兼容、capabilities类型、corrections字段读取）；新增 promoted 错误过滤；新增 create_event.py 标准事件写入工具；session-notes.md / AGENTS.md 补充强制写入规范；setup.sh 修复 crontab tag->tags 并补充 create_event.py chmod |

---

## 文件对应关系

部分脚本名称与方案文档中的描述名称对应如下：

| 方案文档名称 | 实际文件名 |
|---|---|
| `tags_fixer.py` | `fix_recent_events_tags.py` |
| `type_normalizer.py` | `fix_nonstandard_types.py` |

---

## License

MIT
