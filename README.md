# 自主进化的OpenClaw 内网数字助手配置模板 v2.3

让 OpenClaw AI 助手「越用越好用」的自主进化配置框架。

## 解决的问题

| 问题 | 解法 |
|------|------|
| 对话越来越慢，token 消耗迅猛 | 三层记忆按需加载 |
| 压缩后助手「变傻」 | 对话结束主动固化记忆 |
| 死板，不会举一反三 | 事件驱动错误聚类，自动触发规则建议 |
| 越用越老旧 | 双频率进化回路 + git 版本追踪 |

## 快速开始

推荐使用 HTTPS（无需 SSH key，OpenClaw 环境直接可用）：

    git clone https://github.com/zhihua-yang/openclaw-assistant-template.git
    cd openclaw-assistant-template
    bash setup.sh

可选使用 SSH（需要提前配置 SSH key）：

    git clone git@github.com:zhihua-yang/openclaw-assistant-template.git
    cd openclaw-assistant-template
    bash setup.sh

> ⚠️ 必须先 cd openclaw-assistant-template 再运行 bash setup.sh，
> 否则脚本会提示找不到 workspace/ 目录。

## 自定义部署路径（可选）

    OPENCLAW_WORKSPACE=/your/custom/path bash setup.sh

## setup.sh 执行完成后

终端会输出一段激活提示词，复制粘贴到 OpenClaw 对话框，
助手会主动向你提问来完善身份设定和用户偏好，
收集完成后自动写入配置文件，无需手动编辑任何文件。

## 目录结构

    workspace/
    ├── IDENTITY.md          # 助手身份（由激活对话自动写入）
    ├── AGENTS.md            # 行为规则与进化门控
    ├── memory/
    │   ├── core.md          # 长期环境信息（由激活对话自动写入）
    │   ├── project.md       # 项目上下文
    │   └── recent.md        # 近期学习记录（系统自动维护）
    ├── skills/              # 可调用技能（8个）
    └── scripts/             # 进化脚本（与配置统一 git 追踪）
        ├── evolve.py
        ├── baseline.sh
        └── health-check.sh

## 重要说明

- IDENTITY.md：只能手动编辑，进化机制不可触及
- memory/recent.md：系统自动维护，setup.sh 不会覆盖已有内容
- scripts/：有 bug 修复时 setup.sh 会备份旧版本后更新

## cron 任务（激活后在 OpenClaw 里设置）

    每天 00:00   → /memory-evolution
    每周一 09:00 → /weekly-self-reflection

## 版本历史

| 版本 | 主要变更 |
|------|---------|
| v2.3 | setup.sh 自动检测交互环境，终端询问确认，OpenClaw 自动跳过 |
| v2.2 | 移除 read 交互，修复 OpenClaw 非交互式环境卡死问题 |
| v2.1 | scripts/ 移入 workspace/，统一 git 追踪 |
| v2.0 | IDENTITY.md 与 AGENTS.md 职责分离，三级进化门控 |
