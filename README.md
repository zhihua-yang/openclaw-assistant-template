# 内网数字助手 (OpenClaw Workspace)

> 一套运行在本地 / 内网 OpenClaw 环境中的个人 AI 助手配置方案。  
> 无需联网，数据完全本地存储，支持长期记忆、自动进化和定时自省。

**作者：** [zhihua-yang](https://github.com/zhihua-yang)

---

## 快速开始

```bash
git clone https://github.com/zhihua-yang/openclaw-assistant-template.git
cd openclaw-assistant-template
bash setup.sh
```

然后在 OpenClaw → Settings → Workspace 中将路径设为 `~/.openclaw/workspace`，  
新建对话并粘贴 `setup.sh` 运行结束后打印的「激活提示词」即可完成初始化。

> **也可以将 `setup.sh` 直接拖给 OpenClaw**，AI 会引导完成文件部署和 cron 注册，  
> 无需手动打开终端。

---

## 目录结构

```
workspace/
├── IDENTITY.md                    # 助手人格设定
├── AGENTS.md                      # 核心行为规则 & 事件写入规范
├── memory/
│   ├── core.md                    # 用户基本信息
│   ├── project.md                 # 当前项目上下文
│   ├── recent.md                  # 近期活动摘要（evolve.py 自动维护）
│   ├── errors.md                  # 错误记录（monitoring / pending / promoted）
│   └── archive/                   # 历史压缩归档
├── skills/
│   ├── session-notes.md           # /session-notes 技能（指向实现脚本）
│   ├── remember.md
│   ├── weekly-self-reflection.md
│   ├── compact.md
│   ├── todo.md
│   └── health-check.md
├── scripts/
│   ├── session_note_writer.py     # /session-notes 真正实现（v1.0 新增）
│   ├── farewell_detector.py       # 告别词检测 + 自动触发（v1.0 新增）
│   ├── evolve.py                  # 记忆进化主程序（cron 每天 00:00）
│   ├── create_event.py            # 标准化事件写入工具
│   ├── health-check.sh            # 健康检查
│   ├── baseline.sh                # 基线快照 & Diff 对比
│   ├── install-cron.sh            # 定时任务手动安装脚本（setup.sh 自动生成）
│   ├── fix_nonstandard_types.py   # 历史数据修复：type 标准化
│   └── fix_recent_events_tags.py  # 历史数据修复：tag -> tags 字段名
└── .sys/                          # 运行时目录（gitignore）
    ├── logs/events.jsonl          # 结构化事件日志（主路径）
    ├── sessions/                  # 每日会话摘要
    ├── baseline/
    ├── todo/
    └── compact/
```

> `.openclaw/sessions/` 和 `.openclaw/logs/` 作为双路径兼容备份，setup.sh 同时创建。

---

## 核心脚本说明

### `scripts/session_note_writer.py` ⭐ 新增
`/session-notes` 的真正实现脚本。AI 在会话结束时通过 `exec:` 调用，完成 4 个步骤：
1. 写会话摘要 → `.sys/sessions/YYYY-MM-DD.md`（双路径写入）
2. 追加结构化事件 → `events.jsonl`（强制规范校验）
3. 更新 `memory/errors.md`（有错误时自动新增或累计次数）
4. 触发 `/remember` → 更新 `memory/recent.md`

```bash
python3 workspace/scripts/session_note_writer.py   --summary   "本次会话完成了..."   --type      task-done   --content   "具体内容描述..."   --tags      task-completion,progress   --error     "发现的错误（可选）"

# 预览不写文件
python3 workspace/scripts/session_note_writer.py ... --dry-run
```

### `scripts/farewell_detector.py` ⭐ 新增
检测 35+ 种中英文告别词，检测到后自动调用 `session_note_writer.py`。

```bash
# 仅检测
python3 workspace/scripts/farewell_detector.py --text "好的，再见"

# 检测到告别词时自动触发 session-notes
python3 workspace/scripts/farewell_detector.py   --text "bye" --auto-trigger   --summary "会话结束" --type task-done --content "..."

# 查看所有告别词
python3 workspace/scripts/farewell_detector.py --list-keywords
```

### `scripts/evolve.py`
每天 00:00 由 cron 自动运行，读取近 7 天 `events.jsonl`，提取洞察并更新 `memory/recent.md` 和 `memory/errors.md`。

```bash
python3 workspace/scripts/evolve.py
python3 workspace/scripts/evolve.py search "关键词"
```

### `scripts/create_event.py`
标准化事件写入工具，自动验证 type 合法性、content 字数、tags 非空。

```bash
python3 workspace/scripts/create_event.py   --type learning-achievement --content "今天学习了..."

python3 workspace/scripts/create_event.py --list-types
```

### `scripts/fix_nonstandard_types.py` / `fix_recent_events_tags.py`
历史数据修复工具。文档中对应名称：`type_normalizer.py` / `tags_fixer.py`。

```bash
python3 workspace/scripts/fix_recent_events_tags.py   # tag -> tags
python3 workspace/scripts/fix_nonstandard_types.py    # 非标准 type 修复
```

---

## 事件规范（events.jsonl）

```json
{
  "ts":      "2026-03-17T00:00:00+00:00",
  "type":    "<标准类型>",
  "content": "<详细描述>",
  "tags":    ["tag1", "tag2"],
  "count":   1
}
```

**强制要求：** `tags` 字段名（非 `tag`）、`ts` 带 UTC 时区、`type` 从标准列表选取。

**14 个标准 type：**

| type | 说明 | 最低字数 |
|---|---|---|
| `task-done` | 完成任务 | 8单元 |
| `error-found` | 发现错误 | 8单元 |
| `system-improvement` | 系统改进 | 10单元 |
| `learning-achievement` | 学习成就 | 15单元 |
| `user-correction` | 用户纠正 | 10单元 |
| `automation-deployment` | 自动化部署 | 5单元 |
| `error-fix` | 错误修复 | 5单元 |
| `system-monitoring` | 系统监控 | 5单元 |
| `quality-verification` | 质量验证 | 5单元 |
| `new-capability` | 新能力（兼容旧数据） | 5单元 |
| `automation-planning` | 自动化规划 | 5单元 |
| `memory-compaction` | 内存压缩 | 5单元 |
| `pua-inspection` | 深度检查 | 5单元 |
| `quality-improvement` | 质量改进 | 5单元 |

> 字数单元：中文每 15 字符 ≈ 1 单元；英文按单词数计算。

---

## 定时任务

`setup.sh` 按以下优先级自动注册（终端和 OpenClaw 对话均可）：

1. **OpenClaw 原生 cron**（`openclaw cron add`）— 推荐，不依赖系统 crontab
2. **系统 crontab** — 兜底方案
3. **自动生成 `install-cron.sh`** — 两者均不可用时，提供手动安装脚本

| 任务 | 时间 | 说明 |
|---|---|---|
| `memory-evolution` | 每天 00:00 UTC | evolve.py 自动整理近7天事件 |
| `weekly-self-reflection-trigger` | 每周一 09:00 UTC | 写入触发信号，启动时自动执行周报 |

```bash
# 查看已注册任务
openclaw cron list

# 手动安装（沙箱/对话环境部署后）
bash ~/.openclaw/workspace/scripts/install-cron.sh
```

---

## 健康检查

```bash
bash workspace/scripts/health-check.sh
```

检查项包括（共17项）：
- 环境：workspace 可写、events.jsonl JSON 合法、磁盘 > 1GB
- 文件：IDENTITY.md、AGENTS.md、memory/core.md、memory/errors.md
- 脚本：evolve.py、create_event.py、session_note_writer.py、farewell_detector.py 的存在和语法
- 功能：farewell_detector 实际检测 `bye` 和 `再见`
- 路径：`.sys/sessions/` 和 `.openclaw/sessions/` 双目录
- 事件质量：近20条 tags 覆盖率、近24小时事件活跃度

---

## 历史数据修复

从旧版升级时建议先运行：

```bash
python3 workspace/scripts/fix_recent_events_tags.py   # 修复 tag -> tags
python3 workspace/scripts/fix_nonstandard_types.py    # 修复非标准 type
```

---

## 版本历史

| 版本 | 主要改动 |
|---|---|
| v3.1 | 初始完整方案 |
| v3.2 | 修复激活提示词视角问题（关于我/关于你） |
| v3.3 | 修复 evolve.py 时区 bug |
| v3.4 | 修复 evolve.py 3个字段一致性 bug；新增 create_event.py；session-notes.md 补充规范 |
| v3.5 | setup.sh 定时任务改为条件执行，新增4种注册方案说明 |
| v3.6 | setup.sh 新增 install-cron.sh 自动生成；激活提示词引导 AI 补注册 |
| v3.7 | setup.sh 接入 OpenClaw 原生 cron，终端和对话双场景均可注册 |
| v3.8 | setup.sh 修复路径嵌套问题（Docker/对话环境 TEMPLATE_DIR 自检修正） |
| v3.9 | 新增 session_note_writer.py（/session-notes 真正实现）和 farewell_detector.py（35+告别词检测）；AGENTS.md 伪命令改为真实 exec: 调用；health-check.sh 新增活跃度检测和新脚本验证 |

---

## 文件对应关系

| 方案文档名称 | 实际文件名 |
|---|---|
| `tags_fixer.py` | `fix_recent_events_tags.py` |
| `type_normalizer.py` | `fix_nonstandard_types.py` |

---

## License

MIT
